#!/usr/bin/env python3
"""Scan Crossref JSONL for GitHub URLs and emit a CSV of candidates."""

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


def extract_strings(value):
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        out = []
        for item in value:
            out.extend(extract_strings(item))
        return out
    if isinstance(value, dict):
        out = []
        for item in value.values():
            out.extend(extract_strings(item))
        return out
    return []


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
        default="data/metadata/github_candidates_from_crossref.csv",
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
            "github_url",
            "source_file",
        ])

        for path, item in iter_jsonl(paths):
            strings = extract_strings(item)
            githubs = sorted({s for s in strings if "github.com" in s.lower()})
            if not githubs:
                continue
            journal = get_container(item)
            title = get_title(item)
            doi = item.get("DOI", "")
            url = item.get("URL", "")
            for gh in githubs:
                writer.writerow([
                    journal,
                    title,
                    doi,
                    url,
                    gh,
                    str(path),
                ])

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
