#!/usr/bin/env python3
"""Harvest Crossref metadata for a list of journals.

Reads a CSV with a `journal_title` column and writes per-journal JSONL files,
plus a manifest CSV with counts and status.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import time
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Dict, List

CROSSREF_ENDPOINT = "https://api.crossref.org/v1/works"


def fetch_json(url: str, params: Dict[str, str], user_agent: str) -> dict:
    query = urllib.parse.urlencode(params)
    req = urllib.request.Request(f"{url}?{query}", headers={"User-Agent": user_agent})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))


def write_jsonl(items, out_path: Path) -> int:
    count = 0
    with out_path.open("a", encoding="utf-8") as f:
        for item in items:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
            count += 1
    return count


def slugify(value: str) -> str:
    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9]+", "_", value)
    return value.strip("_")


def harvest_journal(
    journal: str,
    out_path: Path,
    from_date: str,
    to_date: str,
    rows: int,
    sleep: float,
    limit: int,
    mailto: str,
    user_agent: str,
) -> int:
    cursor = "*"
    total = 0
    while True:
        filters = [
            f"from-pub-date:{from_date}",
            f"until-pub-date:{to_date}",
            "type:journal-article",
        ]
        params = {
            "filter": ",".join(filters),
            "rows": str(rows),
            "cursor": cursor,
            "query.container-title": journal,
        }
        if mailto:
            params["mailto"] = mailto

        data = fetch_json(CROSSREF_ENDPOINT, params, user_agent)
        items = data.get("message", {}).get("items", [])
        if not items:
            break
        total += write_jsonl(items, out_path)

        next_cursor = data.get("message", {}).get("next-cursor")
        if not next_cursor or next_cursor == cursor:
            break
        cursor = next_cursor

        if limit and total >= limit:
            break
        time.sleep(sleep)
    return total


def load_journals(csv_path: Path) -> List[str]:
    with csv_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if "journal_title" not in reader.fieldnames:
            raise ValueError("CSV must include a journal_title column")
        return [row["journal_title"].strip() for row in reader if row.get("journal_title")]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--journals-csv", required=True)
    parser.add_argument("--out-dir", default="data/metadata/journals")
    parser.add_argument("--from-date", required=True, help="YYYY-MM-DD")
    parser.add_argument("--to-date", required=True, help="YYYY-MM-DD")
    parser.add_argument("--rows", type=int, default=1000)
    parser.add_argument("--sleep", type=float, default=0.2)
    parser.add_argument("--limit-per-journal", type=int, default=0)
    parser.add_argument("--max-journals", type=int, default=0)
    parser.add_argument("--mailto", default="")
    parser.add_argument("--user-agent", default="publication-figures/0.1")
    parser.add_argument(
        "--manifest",
        default="data/metadata/journal_harvest_manifest.csv",
        help="CSV summary of harvest results",
    )
    args = parser.parse_args()

    journals = load_journals(Path(args.journals_csv))
    if args.max_journals:
        journals = journals[: args.max_journals]

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    manifest_path = Path(args.manifest)
    manifest_exists = manifest_path.exists()

    with manifest_path.open("a", newline="", encoding="utf-8") as mf:
        writer = csv.writer(mf)
        if not manifest_exists:
            writer.writerow([
                "timestamp",
                "journal_title",
                "output_file",
                "from_date",
                "to_date",
                "count",
                "status",
                "notes",
            ])

        for journal in journals:
            slug = slugify(journal)
            out_file = out_dir / f"crossref_{slug}_{args.from_date}_{args.to_date}.jsonl"
            if out_file.exists():
                writer.writerow([
                    datetime.utcnow().isoformat() + "Z",
                    journal,
                    str(out_file),
                    args.from_date,
                    args.to_date,
                    0,
                    "skipped_exists",
                    "output already exists",
                ])
                continue
            try:
                count = harvest_journal(
                    journal,
                    out_file,
                    args.from_date,
                    args.to_date,
                    args.rows,
                    args.sleep,
                    args.limit_per_journal,
                    args.mailto,
                    args.user_agent,
                )
                status = "ok" if count else "no_items"
                writer.writerow([
                    datetime.utcnow().isoformat() + "Z",
                    journal,
                    str(out_file),
                    args.from_date,
                    args.to_date,
                    count,
                    status,
                    "",
                ])
            except Exception as exc:  # noqa: BLE001
                writer.writerow([
                    datetime.utcnow().isoformat() + "Z",
                    journal,
                    str(out_file),
                    args.from_date,
                    args.to_date,
                    0,
                    "error",
                    repr(exc),
                ])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
