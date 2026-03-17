#!/usr/bin/env python3
"""Parse Nature Portfolio journal metrics page to extract JIF values."""

from __future__ import annotations

import argparse
import csv
from html.parser import HTMLParser
from pathlib import Path
from typing import List


class MetricsParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.in_table = False
        self.in_td = False
        self.current_row: List[str] = []
        self.rows: List[List[str]] = []
        self._capture_tables = False
        self._header_row_seen = False
        self._current_cell = ""

    def handle_starttag(self, tag: str, attrs):
        if tag == "table":
            self.in_table = True
            self._header_row_seen = False
            self._capture_tables = False
            self.current_row = []
            return
        if self.in_table and tag == "tr":
            self.current_row = []
            return
        if self.in_table and tag == "td":
            self.in_td = True
            self._current_cell = ""
            return

    def handle_endtag(self, tag: str):
        if self.in_table and tag == "td":
            self.in_td = False
            self.current_row.append(self._current_cell.strip())
            self._current_cell = ""
            return
        if self.in_table and tag == "tr":
            if not self.current_row:
                return
            # Detect header row with Journal Impact Factor
            if any("Journal Impact Factor" in cell for cell in self.current_row):
                self._capture_tables = True
                self._header_row_seen = True
            else:
                if self._capture_tables and self._header_row_seen:
                    self.rows.append(self.current_row)
            self.current_row = []
            return
        if tag == "table" and self.in_table:
            self.in_table = False
            self._capture_tables = False
            self._header_row_seen = False
            return

    def handle_data(self, data: str):
        if self.in_td:
            self._current_cell += data


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--html",
        default="data/metadata/nature_portfolio_metrics.html",
    )
    parser.add_argument(
        "--out",
        default="data/metadata/nature_portfolio_jif.csv",
    )
    parser.add_argument(
        "--out-filtered",
        default="data/metadata/nature_journals_if_gt10.csv",
    )
    args = parser.parse_args()

    html = Path(args.html).read_text(encoding="utf-8", errors="ignore")
    parser_obj = MetricsParser()
    parser_obj.feed(html)

    rows = []
    for row in parser_obj.rows:
        if len(row) < 2:
            continue
        journal = row[0]
        jif = row[1]
        rows.append((journal, jif))

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["journal_title", "impact_factor"])
        for journal, jif in rows:
            writer.writerow([journal, jif])

    filtered_path = Path(args.out_filtered)
    with filtered_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["journal_title", "impact_factor"])
        for journal, jif in rows:
            try:
                val = float(jif)
            except ValueError:
                continue
            if val > 10:
                writer.writerow([journal, jif])

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
