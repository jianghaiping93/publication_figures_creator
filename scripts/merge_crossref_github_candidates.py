#!/usr/bin/env python3
"""Merge Crossref-discovered GitHub URLs into discovery queue."""

from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--candidates",
        default="data/metadata/github_candidates_from_crossref.csv",
    )
    parser.add_argument(
        "--queue",
        default="data/metadata/repo_discovery_queue.csv",
    )
    parser.add_argument(
        "--out",
        default="data/metadata/repo_discovery_queue.csv",
    )
    args = parser.parse_args()

    cand_map = defaultdict(list)
    with Path(args.candidates).open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            doi = (row.get("doi") or "").strip()
            gh = (row.get("github_url") or "").strip()
            if doi and gh:
                cand_map[doi].append(gh)

    queue_path = Path(args.queue)
    rows = []
    with queue_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []
        for row in reader:
            doi = (row.get("doi") or "").strip()
            if doi in cand_map:
                githubs = sorted(set(cand_map[doi]))
                row["github_candidates"] = " | ".join(githubs)
                if row.get("search_status") in {"", "pending"}:
                    row["search_status"] = "github_found_crossref"
                note = row.get("notes") or ""
                if "crossref" not in note.lower():
                    row["notes"] = (note + " " if note else "") + "GitHub links from Crossref metadata."
            rows.append(row)

    with Path(args.out).open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
