#!/usr/bin/env python3
"""
Parse logs for missing file paths and attempt automatic fixes:
- Normalize relative paths.
- Rewrite working directory to match repo-root-relative file locations.
- Create missing output directories for image outputs.
"""
from __future__ import annotations

import csv
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


LOG_LIMIT = 200_000
DATA_EXTS = {".csv", ".tsv", ".txt", ".h5", ".hdf5", ".npz", ".npy", ".bam", ".fastq", ".fasta", ".mtx", ".bed", ".gz"}
IMAGE_EXTS = {".png", ".pdf", ".svg", ".eps", ".tif", ".tiff", ".jpg", ".jpeg"}


MISSING_PATTERNS = [
    re.compile(r"FileNotFoundError: \\[Errno 2\\] No such file or directory: ['\"]([^'\"]+)['\"]"),
    re.compile(r"No such file or directory: ['\"]([^'\"]+)['\"]"),
    re.compile(r"cannot open file ['\"]([^'\"]+)['\"]", re.IGNORECASE),
]


@dataclass
class MissingHit:
    path: str
    kind: str


def read_text(path: Path) -> str:
    try:
        return path.read_text(errors="ignore")[:LOG_LIMIT]
    except Exception:
        return ""


def normalize_path(raw: str) -> str:
    cleaned = raw.strip().strip("\"'").replace("\\", "/")
    cleaned = re.sub(r"//+", "/", cleaned)
    if cleaned.startswith("./"):
        cleaned = cleaned[2:]
    return cleaned


def is_windows_abs(path: str) -> bool:
    return bool(re.match(r"^[A-Za-z]:/", path))


def extract_missing_path(text: str) -> MissingHit | None:
    for pat in MISSING_PATTERNS:
        m = pat.search(text)
        if m:
            raw = m.group(1)
            norm = normalize_path(raw)
            ext = Path(norm).suffix.lower()
            if ext in IMAGE_EXTS or "figure" in norm.lower() or "fig" in norm.lower():
                return MissingHit(norm, "image_output")
            if ext in DATA_EXTS or any(tok in norm.lower() for tok in ("data", "dataset", "input")):
                return MissingHit(norm, "data")
            return MissingHit(norm, "file")
    return None


def read_csv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        return
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        w.writeheader()
        w.writerows(rows)


def build_repo_dir_map() -> dict[str, str]:
    repo_path = Path("data/metadata/cns_tables/repositories.csv")
    if not repo_path.exists():
        return {}
    with repo_path.open(newline="") as f:
        return {row.get("repo_url", ""): row.get("repo_dir", "") for row in csv.DictReader(f)}


def extract_cd_prefix(cmd: str) -> tuple[str | None, str]:
    m = re.match(r"^\\s*cd\\s+([^;&]+?)\\s*&&\\s*(.+)$", cmd)
    if not m:
        return None, cmd
    cd_path = m.group(1).strip().strip("\"'")
    rest = m.group(2).strip()
    return cd_path, rest


def rebuild_command(
    cmd: str,
    language: str,
    script_path: str,
    repo_dir: Path,
    new_cwd: Path,
) -> str:
    if not script_path:
        return cmd
    script_abs = repo_dir / script_path
    try:
        script_rel = os.path.relpath(script_abs, new_cwd)
    except Exception:
        return cmd

    if language.lower() == "python":
        m = re.match(r"^(python3|python)\\s+(.+?\\.py)(\\s+.*)?$", cmd)
        if m:
            tail = m.group(3) or ""
            return f"python3 {quote_if_needed(script_rel)}{tail}"
        return f"python3 {quote_if_needed(script_rel)}"

    if language.lower() in {"r", "rscript"}:
        m = re.match(r"^(Rscript)\\s+(.+?\\.R)(\\s+.*)?$", cmd)
        if m:
            tail = m.group(3) or ""
            return f"Rscript {quote_if_needed(script_rel)}{tail}"
        return f"Rscript {quote_if_needed(script_rel)}"

    return cmd


def quote_if_needed(path: str) -> str:
    if any(ch in path for ch in (" ", "(", ")")):
        return f"\"{path}\""
    return path


def find_candidates(repo_dir: Path, missing_path: str) -> list[Path]:
    parts = Path(missing_path).parts
    basename = Path(missing_path).name
    candidates = []
    for p in repo_dir.rglob(basename):
        try:
            rel = p.relative_to(repo_dir)
        except Exception:
            continue
        if rel.parts[-len(parts):] == parts:
            candidates.append(p)
    if candidates:
        return sorted(candidates, key=lambda p: len(str(p)))
    # fallback: basename only
    for p in repo_dir.rglob(basename):
        candidates.append(p)
    return sorted(candidates, key=lambda p: len(str(p)))


def compute_new_cwd(repo_dir: Path, missing_path: str, candidate: Path) -> Path:
    missing_parts = Path(missing_path).parts
    if len(missing_parts) <= 1:
        return candidate.parent
    try:
        rel = candidate.relative_to(repo_dir)
    except Exception:
        return repo_dir
    return repo_dir / Path(*rel.parts[:-len(missing_parts)])


def ensure_output_dir(repo_dir: Path, cwd: Path, missing_path: str) -> bool:
    target = Path(missing_path)
    if target.is_absolute() or is_windows_abs(missing_path):
        return False
    if target.suffix.lower() not in IMAGE_EXTS:
        return False
    out_dir = (cwd / target).parent
    if repo_dir not in out_dir.parents and out_dir != repo_dir:
        return False
    out_dir.mkdir(parents=True, exist_ok=True)
    return True


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--queue", default="data/metadata/reproducibility_queue.csv")
    parser.add_argument("--out", default="data/metadata/missing_file_auto_fixes.csv")
    args = parser.parse_args()

    queue_path = Path(args.queue)
    rows = read_csv(queue_path)
    if not rows:
        print("queue: 0")
        return

    repo_dir_map = build_repo_dir_map()
    fix_rows = []
    updated = 0
    marked_ready = 0
    marked_manual = 0

    for idx, row in enumerate(rows):
        if row.get("result") != "failed":
            continue
        log_path = Path(row.get("log_path") or "")
        if not log_path.exists():
            continue
        text = read_text(log_path)
        hit = extract_missing_path(text)
        if not hit:
            continue

        repo_dir = Path(repo_dir_map.get(row.get("repo_url", ""), "") or "")
        if not repo_dir.exists():
            continue

        missing_path = hit.path
        row["failure_reason"] = f"missing_file:{missing_path}"
        row["notes"] = (row.get("notes", "") + f" | missing_path:{missing_path}").strip(" |")

        cmd = row.get("run_command", "") or ""
        cd_prefix, cmd_rest = extract_cd_prefix(cmd)
        cwd = repo_dir
        if cd_prefix:
            cd_path = Path(cd_prefix)
            if not cd_path.is_absolute():
                cd_path = repo_dir / cd_path
            cwd = cd_path

        # Try to fix missing output directory for figures.
        if hit.kind == "image_output":
            if ensure_output_dir(repo_dir, cwd, missing_path):
                row["result"] = "ready_for_run"
                row["failure_reason"] = ""
                row["notes"] = (row.get("notes", "") + " | created_output_dir").strip(" |")
                updated += 1
                marked_ready += 1
                fix_rows.append({
                    "index": idx,
                    "repo_url": row.get("repo_url", ""),
                    "script_path": row.get("script_path", ""),
                    "missing_path": missing_path,
                    "fix_action": "created_output_dir",
                    "new_command": row.get("run_command", ""),
                    "log_path": row.get("log_path", ""),
                })
                continue

        # Normalize expected path relative to repo root if absolute inside repo.
        expected = Path(missing_path)
        if expected.is_absolute() or is_windows_abs(missing_path):
            try:
                expected = expected.resolve()
            except Exception:
                expected = expected
            if repo_dir in expected.parents:
                missing_path = str(expected.relative_to(repo_dir)).replace("\\", "/")
            else:
                row["result"] = "needs_manual"
                row["failure_reason"] = "missing_external_data"
                row["notes"] = (row.get("notes", "") + " | missing_external_path").strip(" |")
                marked_manual += 1
                continue

        expected_path = repo_dir / missing_path
        if expected_path.exists():
            # If file exists under repo root, try to remove any cd prefix.
            if cd_prefix:
                new_cmd = cmd_rest
                row["run_command"] = new_cmd
                row["result"] = "ready_for_run"
                row["failure_reason"] = ""
                row["notes"] = (row.get("notes", "") + " | cd_removed_repo_root").strip(" |")
                updated += 1
                marked_ready += 1
                fix_rows.append({
                    "index": idx,
                    "repo_url": row.get("repo_url", ""),
                    "script_path": row.get("script_path", ""),
                    "missing_path": missing_path,
                    "fix_action": "remove_cd_prefix",
                    "new_command": new_cmd,
                    "log_path": row.get("log_path", ""),
                })
            continue

        candidates = find_candidates(repo_dir, missing_path)
        if not candidates:
            row["notes"] = (row.get("notes", "") + " | missing_path_not_in_repo").strip(" |")
            continue

        candidate = candidates[0]
        new_cwd = compute_new_cwd(repo_dir, missing_path, candidate)
        new_cmd = rebuild_command(cmd_rest if cd_prefix else cmd, row.get("language", ""), row.get("script_path", "") or "", repo_dir, new_cwd)
        rel_cwd = os.path.relpath(new_cwd, repo_dir)
        prefix = f"cd {quote_if_needed(rel_cwd)} && " if rel_cwd not in (".", "") else ""
        final_cmd = prefix + new_cmd

        if final_cmd != cmd:
            row["run_command"] = final_cmd
            row["result"] = "ready_for_run"
            row["failure_reason"] = ""
            row["notes"] = (row.get("notes", "") + f" | cwd_fix:{rel_cwd}").strip(" |")
            updated += 1
            marked_ready += 1
            fix_rows.append({
                "index": idx,
                "repo_url": row.get("repo_url", ""),
                "script_path": row.get("script_path", ""),
                "missing_path": missing_path,
                "fix_action": "cwd_rewrite",
                "new_command": final_cmd,
                "log_path": row.get("log_path", ""),
            })

    write_csv(queue_path, rows)

    if fix_rows:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with out_path.open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(fix_rows[0].keys()))
            w.writeheader()
            w.writerows(fix_rows)

    print(f"updated: {updated}")
    print(f"ready_for_run: {marked_ready}")
    print(f"needs_manual: {marked_manual}")


if __name__ == "__main__":
    main()
