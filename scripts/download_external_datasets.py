#!/usr/bin/env python3
"""
Download external dataset files listed in external_dataset_downloads.csv using curl.
"""
from __future__ import annotations

import csv
import subprocess
from pathlib import Path


def read_csv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", default="data/metadata/external_dataset_downloads.csv")
    parser.add_argument("--max-files", type=int, default=0)
    args = parser.parse_args()

    manifest = Path(args.manifest)
    rows = read_csv(manifest)
    if not rows:
        print("manifest: 0")
        return

    selected = rows
    if args.max_files and args.max_files > 0:
        selected = rows[: args.max_files]

    downloaded = 0
    skipped = 0
    for row in selected:
        url = (row.get("url", "") or "").strip()
        dest = (row.get("dest", "") or "").strip()
        if not url or not dest:
            skipped += 1
            continue
        dest_path = Path(dest)
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        if dest_path.exists() and dest_path.stat().st_size > 0:
            skipped += 1
            continue
        cmd = ["curl", "-sS", "-L", "-o", str(dest_path), url]
        try:
            subprocess.run(cmd, check=True)
            downloaded += 1
        except subprocess.CalledProcessError:
            print(f"download_failed: {url}")

    print(f"downloaded: {downloaded}")
    print(f"skipped: {skipped}")


if __name__ == "__main__":
    main()
