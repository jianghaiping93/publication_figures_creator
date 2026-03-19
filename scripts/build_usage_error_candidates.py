#!/usr/bin/env python3
"""
Build candidate run commands for usage/argument errors by mining README files and logs.
"""
from __future__ import annotations

import csv
import re
from pathlib import Path


LOG_LIMIT = 200_000
USAGE_PATTERNS = [
    re.compile(r"error: unrecognized arguments", re.IGNORECASE),
    re.compile(r"usage: .+\\n.+error:", re.IGNORECASE),
    re.compile(r"the following arguments are required: (.+)", re.IGNORECASE),
]


def read_text(path: Path) -> str:
    try:
        return path.read_text(errors="ignore")[:LOG_LIMIT]
    except Exception:
        return ""


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


def extract_required_args(log_text: str) -> list[str]:
    m = re.search(r"the following arguments are required: (.+)", log_text, re.IGNORECASE)
    if not m:
        return []
    raw = m.group(1)
    parts = [p.strip().strip(".") for p in raw.split(",")]
    return [p for p in parts if p]


def guess_candidate_from_log(cmd: str, required: list[str]) -> str | None:
    if not required:
        return None
    args = []
    for item in required:
        if item.startswith("-"):
            args.append(f"{item} <value>")
        else:
            args.append(f"<{item}>")
    return cmd + " " + " ".join(args)


def find_readmes(repo_dir: Path) -> list[Path]:
    readmes = []
    for name in ("README.md", "README.rst", "README.txt", "Readme.md", "readme.md"):
        p = repo_dir / name
        if p.exists():
            readmes.append(p)
    # Include docs/README if present
    for p in repo_dir.glob("docs/README*"):
        readmes.append(p)
    return readmes


def extract_readme_candidates(text: str, script_basename: str) -> list[str]:
    candidates = []
    for line in text.splitlines():
        if script_basename and script_basename not in line:
            continue
        if "python" in line or "Rscript" in line:
            clean = line.strip().strip("`").strip()
            if clean:
                candidates.append(clean)
    # code blocks
    blocks = re.findall(r"```[a-zA-Z]*\\n(.*?)```", text, flags=re.DOTALL)
    for block in blocks:
        for line in block.splitlines():
            if script_basename and script_basename not in line:
                continue
            if "python" in line or "Rscript" in line:
                clean = line.strip()
                if clean:
                    candidates.append(clean)
    return candidates


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--queue", default="data/metadata/reproducibility_queue.csv")
    parser.add_argument("--out", default="data/metadata/usage_error_candidates.csv")
    args = parser.parse_args()

    queue_path = Path(args.queue)
    rows = read_csv(queue_path)
    if not rows:
        print("queue: 0")
        return

    repo_dir_map = build_repo_dir_map()
    out_rows = []
    updated = 0

    for row in rows:
        if row.get("result") != "failed":
            continue
        log_path = Path(row.get("log_path") or "")
        if not log_path.exists():
            continue
        log_text = read_text(log_path)
        if not any(p.search(log_text) for p in USAGE_PATTERNS):
            continue

        cmd = row.get("run_command", "") or ""
        required_args = extract_required_args(log_text)
        candidate_from_log = guess_candidate_from_log(cmd, required_args)

        repo_dir = Path(repo_dir_map.get(row.get("repo_url", ""), "") or "")
        readme_candidates = []
        readme_source = ""
        if repo_dir.exists():
            script_basename = Path(row.get("script_path", "") or "").name
            for readme in find_readmes(repo_dir):
                text = read_text(readme)
                found = extract_readme_candidates(text, script_basename)
                if found:
                    readme_candidates.extend(found)
                    readme_source = readme.name
                    break

        candidate = ""
        source = ""
        if readme_candidates:
            candidate = readme_candidates[0]
            source = f"readme:{readme_source}"
        elif candidate_from_log:
            candidate = candidate_from_log
            source = "log_required_args"

        out_rows.append({
            "paper_id": row.get("paper_id", ""),
            "repo_url": row.get("repo_url", ""),
            "script_path": row.get("script_path", ""),
            "run_command": cmd,
            "candidate_command": candidate,
            "source": source,
            "log_path": row.get("log_path", ""),
        })

        if candidate:
            row["run_command"] = candidate
            row["result"] = "ready_for_run"
            row["failure_reason"] = ""
            row["notes"] = (row.get("notes", "") + f" | usage_candidate:{source}").strip(" |")
            updated += 1

    write_csv(queue_path, rows)
    if out_rows:
        write_csv(Path(args.out), out_rows)

    print(f"candidates: {len(out_rows)}")
    print(f"updated_ready: {updated}")


if __name__ == "__main__":
    main()
