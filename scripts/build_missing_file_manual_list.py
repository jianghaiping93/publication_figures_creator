#!/usr/bin/env python3
"""
Build a manual list for missing file paths that are not found inside the repo.
"""
from __future__ import annotations

import csv
import re
from pathlib import Path


LOG_LIMIT = 200_000
MISSING_PATTERNS = [
    re.compile(r"FileNotFoundError: \\[Errno 2\\] No such file or directory: ['\"]([^'\"]+)['\"]"),
    re.compile(r"No such file or directory: ['\"]([^'\"]+)['\"]"),
    re.compile(r"cannot open file ['\"]([^'\"]+)['\"]", re.IGNORECASE),
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


def extract_missing_path(text: str) -> str | None:
    for pat in MISSING_PATTERNS:
        m = pat.search(text)
        if m:
            return m.group(1).strip().strip("\"'")
    return None


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--queue", default="data/metadata/reproducibility_queue.csv")
    parser.add_argument("--out", default="data/metadata/missing_file_manual.csv")
    args = parser.parse_args()

    rows = read_csv(Path(args.queue))
    if not rows:
        print("queue: 0")
        return

    repo_dir_map = build_repo_dir_map()
    out_rows = []

    for row in rows:
        if row.get("result") != "failed":
            continue
        log_path = Path(row.get("log_path") or "")
        if not log_path.exists():
            continue
        text = read_text(log_path)
        missing_path = extract_missing_path(text)
        if not missing_path:
            continue
        repo_dir = Path(repo_dir_map.get(row.get("repo_url", ""), "") or "")
        if not repo_dir.exists():
            continue
        # normalize and check if exists in repo
        norm = missing_path.replace("\\", "/")
        if norm.startswith("./"):
            norm = norm[2:]
        expected = repo_dir / norm
        if expected.exists():
            continue
        out_rows.append({
            "repo_url": row.get("repo_url", ""),
            "script_path": row.get("script_path", ""),
            "missing_path": missing_path,
            "log_path": row.get("log_path", ""),
        })

    write_csv(Path(args.out), out_rows)
    print(f"manual_missing: {len(out_rows)}")


if __name__ == "__main__":
    main()
