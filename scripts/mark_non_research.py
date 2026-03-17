#!/usr/bin/env python3
"""Mark obvious non-research items (e.g., Nature news/editorial) in the queue."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--queue",
        default="data/metadata/repo_discovery_queue.csv",
    )
    args = parser.parse_args()

    path = Path(args.queue)
    rows = []
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []
        for row in reader:
            doi = (row.get("doi") or "").strip()
            if doi.startswith("10.1038/d41586"):
                row["search_status"] = "not_research"
                note = row.get("notes") or ""
                if "nature news" not in note.lower():
                    row["notes"] = (note + " " if note else "") + "Nature News/Editorial (d41586)."
            rows.append(row)

    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
