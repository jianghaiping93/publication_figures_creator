#!/usr/bin/env python3
"""Extract a unified paper index from Crossref JSONL files."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Iterable


def iter_jsonl(paths: Iterable[Path]):
    for path in paths:
        with path.open("r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    yield path, json.loads(line)
                except json.JSONDecodeError:
                    continue


def get_title(item: dict) -> str:
    title = item.get("title") or []
    if isinstance(title, list) and title:
        return title[0]
    if isinstance(title, str):
        return title
    return ""


def get_container(item: dict) -> str:
    container = item.get("container-title") or []
    if isinstance(container, list) and container:
        return container[0]
    if isinstance(container, str):
        return container
    return ""


def get_year(item: dict) -> str:
    issued = item.get("issued", {}).get("date-parts")
    if isinstance(issued, list) and issued and issued[0]:
        return str(issued[0][0])
    return ""


def get_published_date(item: dict) -> str:
    parts = item.get("published", {}).get("date-parts")
    if isinstance(parts, list) and parts and parts[0]:
        date_parts = parts[0]
        return "-".join(str(p).zfill(2) for p in date_parts)
    return ""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--inputs",
        nargs="+",
        default=[
            "data/metadata/crossref_nature_2023_2026.jsonl",
            "data/metadata/crossref_science_2023_2026.jsonl",
            "data/metadata/crossref_cell_2023_2026.jsonl",
            "data/metadata/journals/*.jsonl",
        ],
    )
    parser.add_argument(
        "--out",
        default="data/metadata/papers_index.csv",
    )
    args = parser.parse_args()

    paths = []
    for pattern in args.inputs:
        paths.extend(Path().glob(pattern))

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "journal",
            "title",
            "doi",
            "url",
            "year",
            "published_date",
            "source_file",
        ])
        for path, item in iter_jsonl(paths):
            journal = get_container(item)
            title = get_title(item)
            doi = item.get("DOI", "")
            url = item.get("URL", "")
            year = get_year(item)
            published_date = get_published_date(item)
            writer.writerow([
                journal,
                title,
                doi,
                url,
                year,
                published_date,
                str(path),
            ])

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
