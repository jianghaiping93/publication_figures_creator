#!/usr/bin/env python3
"""Harvest paper metadata from Crossref or OpenAlex into JSONL.

Minimal dependencies: Python standard library only.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.parse
import urllib.request
from datetime import date

CROSSREF_ENDPOINT = "https://api.crossref.org/v1/works"
OPENALEX_ENDPOINT = "https://api.openalex.org/works"


def fetch_json(url: str, params: dict[str, str], user_agent: str) -> dict:
    query = urllib.parse.urlencode(params)
    req = urllib.request.Request(f"{url}?{query}", headers={"User-Agent": user_agent})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))


def write_jsonl(items, out_path: str) -> int:
    count = 0
    with open(out_path, "a", encoding="utf-8") as f:
        for item in items:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
            count += 1
    return count


def crossref_harvest(args: argparse.Namespace) -> int:
    cursor = "*"
    total = 0
    while True:
        filters = [
            f"from-pub-date:{args.from_date}",
            f"until-pub-date:{args.to_date}",
            f"container-title:{args.journal}",
            "type:journal-article",
        ]
        params = {
            "filter": ",".join(filters),
            "rows": str(args.rows),
            "cursor": cursor,
            "cursor-max": str(args.rows),
        }
        if args.mailto:
            params["mailto"] = args.mailto

        data = fetch_json(CROSSREF_ENDPOINT, params, args.user_agent)
        items = data.get("message", {}).get("items", [])
        if not items:
            break
        total += write_jsonl(items, args.output)

        next_cursor = data.get("message", {}).get("next-cursor")
        if not next_cursor or next_cursor == cursor:
            break
        cursor = next_cursor

        if args.limit and total >= args.limit:
            break
        time.sleep(args.sleep)
    return total


def openalex_harvest(args: argparse.Namespace) -> int:
    cursor = "*"
    total = 0
    while True:
        filters = [
            f"from_publication_date:{args.from_date}",
            f"to_publication_date:{args.to_date}",
        ]
        if args.source_id:
            filters.append(f"primary_location.source.id:{args.source_id}")
        if args.issn:
            filters.append(f"primary_location.source.issn:{args.issn}")
        params = {
            "filter": ",".join(filters),
            "per-page": str(args.rows),
            "cursor": cursor,
        }
        if args.mailto:
            params["mailto"] = args.mailto
        if args.api_key:
            params["api_key"] = args.api_key

        data = fetch_json(OPENALEX_ENDPOINT, params, args.user_agent)
        items = data.get("results", [])
        if not items:
            break
        total += write_jsonl(items, args.output)

        next_cursor = data.get("meta", {}).get("next_cursor")
        if not next_cursor or next_cursor == cursor:
            break
        cursor = next_cursor

        if args.limit and total >= args.limit:
            break
        time.sleep(args.sleep)
    return total


def openalex_source_lookup(args: argparse.Namespace) -> int:
    # Resolve an OpenAlex Source by ISSN
    url = f"https://api.openalex.org/sources/issn:{args.issn}"
    params = {"select": "id,display_name,issn,issn_l"}
    if args.api_key:
        params["api_key"] = args.api_key
    data = fetch_json(url, params, args.user_agent)
    print(json.dumps(data, ensure_ascii=False, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_crossref = sub.add_parser("crossref", help="Harvest from Crossref works API")
    p_crossref.add_argument("--journal", required=True, help="Exact journal title")
    p_crossref.add_argument("--from-date", required=True, help="YYYY-MM-DD")
    p_crossref.add_argument("--to-date", required=True, help="YYYY-MM-DD")
    p_crossref.add_argument("--mailto", default="", help="Email for polite pool")
    p_crossref.add_argument("--rows", type=int, default=1000)
    p_crossref.add_argument("--sleep", type=float, default=0.2)
    p_crossref.add_argument("--limit", type=int, default=0)
    p_crossref.add_argument("--output", required=True)
    p_crossref.add_argument("--user-agent", default="publication-figures/0.1")
    p_crossref.set_defaults(func=crossref_harvest)

    p_openalex = sub.add_parser("openalex", help="Harvest from OpenAlex works API")
    p_openalex.add_argument("--source-id", default="", help="OpenAlex source ID URL")
    p_openalex.add_argument("--issn", default="", help="ISSN for source filter")
    p_openalex.add_argument("--from-date", required=True, help="YYYY-MM-DD")
    p_openalex.add_argument("--to-date", required=True, help="YYYY-MM-DD")
    p_openalex.add_argument("--mailto", default="", help="Email for polite pool")
    p_openalex.add_argument("--api-key", default="", help="OpenAlex API key")
    p_openalex.add_argument("--rows", type=int, default=200)
    p_openalex.add_argument("--sleep", type=float, default=0.2)
    p_openalex.add_argument("--limit", type=int, default=0)
    p_openalex.add_argument("--output", required=True)
    p_openalex.add_argument("--user-agent", default="publication-figures/0.1")
    p_openalex.set_defaults(func=openalex_harvest)

    p_source = sub.add_parser("openalex-source", help="Resolve OpenAlex source by ISSN")
    p_source.add_argument("--issn", required=True)
    p_source.add_argument("--user-agent", default="publication-figures/0.1")
    p_source.add_argument("--api-key", default="", help="OpenAlex API key")
    p_source.set_defaults(func=openalex_source_lookup)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
