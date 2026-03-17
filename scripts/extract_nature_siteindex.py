#!/usr/bin/env python3
"""Extract journals from Nature.com site index and build filtered Nature Portfolio list.

Outputs:
- data/metadata/nature_siteindex_journals.csv
- data/metadata/nature_portfolio_journals.csv
"""

from __future__ import annotations

import argparse
import csv
import html
import urllib.request
from html.parser import HTMLParser
from pathlib import Path
from typing import List, Tuple

SITEINDEX_URL = "https://www.nature.com/siteindex"


class SiteIndexParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.in_index = False
        self.capture_anchor = False
        self.current_href = ""
        self.current_title = ""
        self.results: List[Tuple[str, str]] = []
        self._index_depth = 0

    def handle_starttag(self, tag: str, attrs):
        attrs_dict = dict(attrs)
        if tag == "div" and attrs_dict.get("id") == "journals-az":
            self.in_index = True
            self._index_depth = 1
            return

        if self.in_index and tag == "div":
            self._index_depth += 1

        if self.in_index and tag == "a":
            href = attrs_dict.get("href", "")
            title = attrs_dict.get("data-track-action", "")
            if href and title:
                self.capture_anchor = True
                self.current_href = href
                self.current_title = title

    def handle_endtag(self, tag: str):
        if self.in_index and tag == "div":
            self._index_depth -= 1
            if self._index_depth <= 0:
                self.in_index = False

        if self.capture_anchor and tag == "a":
            self.capture_anchor = False
            if self.current_href and self.current_title:
                self.results.append((self.current_title.strip(), self.current_href.strip()))
            self.current_href = ""
            self.current_title = ""

    def handle_data(self, data: str):
        # Titles are in data-track-action; no need to parse inner text
        pass


def download_siteindex(url: str, out_path: Path) -> None:
    req = urllib.request.Request(url, headers={"User-Agent": "publication-figures/0.1"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        out_path.write_bytes(resp.read())


def classify_title(title: str) -> str:
    title_l = title.lower()
    if title == "Nature":
        return "nature_main"
    if title.startswith("Nature Reviews"):
        return "nature_reviews"
    if title.startswith("Nature Protocols"):
        return "nature_protocols"
    if title.startswith("Nature "):
        return "nature_research"
    if title.startswith("Communications "):
        return "communications"
    if title_l.startswith("npj "):
        return "npj"
    if title in {"Scientific Reports", "Scientific Data"}:
        return "scientific"
    return "other"


def should_include(title: str) -> bool:
    if title == "Nature":
        return True
    if title.startswith("Nature "):
        return True
    if title.startswith("Communications "):
        return True
    if title.lower().startswith("npj "):
        return True
    if title in {"Scientific Reports", "Scientific Data"}:
        return True
    return False


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--html", default="data/metadata/nature_siteindex.html")
    parser.add_argument("--url", default=SITEINDEX_URL)
    parser.add_argument("--out-all", default="data/metadata/nature_siteindex_journals.csv")
    parser.add_argument("--out-filtered", default="data/metadata/nature_portfolio_journals.csv")
    args = parser.parse_args()

    html_path = Path(args.html)
    html_path.parent.mkdir(parents=True, exist_ok=True)

    if not html_path.exists():
        download_siteindex(args.url, html_path)

    parser_obj = SiteIndexParser()
    parser_obj.feed(html_path.read_text(encoding="utf-8", errors="ignore"))

    # Deduplicate by (title, href)
    unique = sorted(set(parser_obj.results), key=lambda x: x[0].lower())

    out_all = Path(args.out_all)
    out_all.parent.mkdir(parents=True, exist_ok=True)
    with out_all.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["journal_title", "journal_path", "journal_url"])
        for title, href in unique:
            href = html.unescape(href)
            url = f"https://www.nature.com{href}"
            writer.writerow([title, href, url])

    out_filtered = Path(args.out_filtered)
    with out_filtered.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["journal_title", "journal_path", "journal_url", "series"])
        for title, href in unique:
            if should_include(title):
                url = f"https://www.nature.com{href}"
                writer.writerow([title, href, url, classify_title(title)])

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
