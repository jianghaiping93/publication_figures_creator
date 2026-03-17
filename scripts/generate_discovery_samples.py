#!/usr/bin/env python3
"""Generate a sample discovery CSV from Crossref JSONL files."""

from __future__ import annotations

import argparse
import csv
import json
from datetime import date
from pathlib import Path
from typing import Any, Iterable


def extract_date(rec: dict) -> date:
    for key in ("published-print", "published-online", "created", "issued"):
        parts = rec.get(key, {}).get("date-parts")
        if parts and parts[0]:
            y = parts[0][0]
            m = parts[0][1] if len(parts[0]) > 1 else 1
            d = parts[0][2] if len(parts[0]) > 2 else 1
            return date(y, m, d)
    return date(1900, 1, 1)


def find_github_urls(obj: Any) -> list[str]:
    urls: list[str] = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(v, (dict, list)):
                urls.extend(find_github_urls(v))
            elif isinstance(v, str) and "github.com" in v:
                urls.append(v)
    elif isinstance(obj, list):
        for v in obj:
            urls.extend(find_github_urls(v))
    return urls


def load_recent(path: Path, limit: int) -> list[dict]:
    items = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            rec = json.loads(line)
            items.append(rec)
    items.sort(key=extract_date, reverse=True)
    return items[:limit]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", action="append", required=True, help="journal=path.jsonl")
    ap.add_argument("--limit", type=int, default=20)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    rows = []
    for spec in args.input:
        journal, path = spec.split("=", 1)
        for rec in load_recent(Path(path), args.limit):
            github_urls = find_github_urls(rec)
            rows.append(
                {
                    "journal": journal,
                    "year": str(extract_date(rec).year),
                    "title": rec.get("title", [""])[0] if rec.get("title") else "",
                    "doi": rec.get("DOI", ""),
                    "paper_url": rec.get("URL", ""),
                    "github_url": github_urls[0] if github_urls else "",
                    "evidence": "crossref_metadata" if github_urls else "",
                }
            )

    with open(args.output, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "journal",
                "year",
                "title",
                "doi",
                "paper_url",
                "github_url",
                "evidence",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
