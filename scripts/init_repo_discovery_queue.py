#!/usr/bin/env python3
"""Initialize discovery queue from papers_index.csv with search status fields."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input",
        default="data/metadata/papers_index.csv",
    )
    parser.add_argument(
        "--out",
        default="data/metadata/repo_discovery_queue.csv",
    )
    args = parser.parse_args()

    in_path = Path(args.input)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with in_path.open(newline="", encoding="utf-8") as f_in, out_path.open(
        "w", newline="", encoding="utf-8"
    ) as f_out:
        reader = csv.DictReader(f_in)
        fieldnames = (
            reader.fieldnames
            + [
                "search_status",
                "github_candidates",
                "notes",
            ]
        )
        writer = csv.DictWriter(f_out, fieldnames=fieldnames)
        writer.writeheader()
        for row in reader:
            row["search_status"] = "pending"
            row["github_candidates"] = ""
            row["notes"] = ""
            writer.writerow(row)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
