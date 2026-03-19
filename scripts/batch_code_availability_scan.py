#!/usr/bin/env python3
"""Batch scan paper landing pages for code/data availability and GitHub links."""
from __future__ import annotations

import argparse
import csv
import random
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List, Tuple
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

TARGET_HEADINGS = {
    "code availability",
    "data availability",
    "data and materials availability",
    "data availability statement",
    "code and data availability",
}

GITHUB_HOSTS = ("github.com", "gitlab.com", "bitbucket.org")
NON_GITHUB_HOST_HINTS = (
    "zenodo.org",
    "figshare.com",
    "osf.io",
    "dryad",
    "datadryad",
    "synapse.org",
)

CORRECTION_PREFIXES = (
    "author correction",
    "publisher correction",
    "correction",
    "erratum",
    "retraction",
    "expression of concern",
)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}


def is_correction(title: str) -> bool:
    t = (title or "").strip().lower()
    return any(t.startswith(p) for p in CORRECTION_PREFIXES)


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def truncate(text: str, limit: int = 500) -> str:
    text = normalize_text(text)
    if len(text) <= limit:
        return text
    return text[:limit - 1].rstrip() + "…"


def extract_sections(html: str, base_url: str) -> Tuple[Dict[str, Dict[str, str]], List[str]]:
    soup = BeautifulSoup(html, "html.parser")
    sections: Dict[str, Dict[str, str]] = {}

    for heading in soup.find_all(["h2", "h3", "h4"]):
        heading_text = normalize_text(heading.get_text(" ", strip=True)).lower()
        if heading_text in TARGET_HEADINGS:
            text_parts: List[str] = []
            links: List[str] = []
            for sib in heading.find_next_siblings():
                if sib.name in ("h2", "h3", "h4"):
                    break
                text_parts.append(sib.get_text(" ", strip=True))
                for a in sib.find_all("a", href=True):
                    links.append(urljoin(base_url, a["href"]))
            sections[heading_text] = {
                "text": normalize_text(" ".join(text_parts)),
                "links": "; ".join(sorted(set(links))),
            }

    all_links = [urljoin(base_url, a["href"]) for a in soup.find_all("a", href=True)]
    return sections, all_links


def regex_fallback(html: str) -> Dict[str, str]:
    text = normalize_text(BeautifulSoup(html, "html.parser").get_text("\n"))
    for heading in TARGET_HEADINGS:
        pattern = rf"{re.escape(heading)}\s*[:\-]?\s*(.{0,800})"
        m = re.search(pattern, text, flags=re.IGNORECASE)
        if m:
            return {"heading": heading, "text": truncate(m.group(1))}
    return {}


def classify_links(links: List[str]) -> Tuple[List[str], List[str]]:
    github_links = []
    other_code_links = []
    for link in links:
        lower = link.lower()
        if any(host in lower for host in GITHUB_HOSTS):
            github_links.append(link)
        elif any(hint in lower for hint in NON_GITHUB_HOST_HINTS):
            other_code_links.append(link)
    return sorted(set(github_links)), sorted(set(other_code_links))


def fetch_availability(url: str, timeout: int = 20) -> Tuple[str, str, str]:
    session = requests.Session()
    resp = session.get(url, headers=HEADERS, timeout=timeout, allow_redirects=True)
    final_url = resp.url
    html = resp.text
    return html, final_url, str(resp.status_code)


def process_row(row: Dict[str, str]) -> Dict[str, str]:
    title = row.get("title", "")
    if is_correction(title):
        return {
            "search_status": "not_research",
            "notes": "Correction / non-research content.",
        }

    url = row.get("url") or ""
    doi = row.get("doi") or ""
    if not url:
        url = f"https://doi.org/{doi}"

    try:
        html, final_url, status_code = fetch_availability(url)
    except Exception as exc:
        return {
            "search_status": "fetch_failed",
            "notes": f"Fetch failed: {exc}",
        }

    sections, all_links = extract_sections(html, final_url)
    github_links, other_code_links = classify_links(all_links)

    code_text = ""
    code_links = ""
    data_text = ""
    data_links = ""

    if "code availability" in sections:
        code_text = truncate(sections["code availability"].get("text", ""))
        code_links = sections["code availability"].get("links", "")
    if "data availability" in sections:
        data_text = truncate(sections["data availability"].get("text", ""))
        data_links = sections["data availability"].get("links", "")
    if not code_text and not data_text:
        fallback = regex_fallback(html)
        if fallback:
            code_text = fallback.get("text", "")

    status = "no_code_availability_found"
    notes = f"HTTP {status_code}"

    if github_links:
        status = "github_found_web"
        notes = "GitHub link found in page links."
    elif code_text or data_text or other_code_links:
        status = "code_available_non_github"
        notes = "Code/data availability found without GitHub."

    return {
        "search_status": status,
        "notes": notes,
        "availability_source_url": final_url,
        "code_availability_text": code_text,
        "code_availability_links": code_links,
        "data_availability_text": data_text,
        "data_availability_links": data_links,
        "github_candidates": "; ".join(github_links),
    }


def ensure_columns(fieldnames: List[str], new_cols: List[str]) -> List[str]:
    for col in new_cols:
        if col not in fieldnames:
            fieldnames.append(col)
    return fieldnames


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--queue", default="data/metadata/repo_discovery_queue.csv")
    ap.add_argument("--journals", default="Nature,Science,Cell")
    ap.add_argument("--journals-file", default="")
    ap.add_argument("--year-min", type=int, default=2023)
    ap.add_argument("--max-workers", type=int, default=12)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--batch-size", type=int, default=200)
    ap.add_argument("--sleep", type=float, default=0.2)
    args = ap.parse_args()

    target_journals = {j.strip() for j in args.journals.split(",") if j.strip()}
    if args.journals_file:
        jf = Path(args.journals_file)
        if jf.exists():
            with jf.open() as f:
                reader = csv.DictReader(f)
                for row in reader:
                    name = (
                        row.get("journal")
                        or row.get("name")
                        or row.get("title")
                        or row.get("journal_title")
                        or ""
                    ).strip()
                    if name:
                        target_journals.add(name)

    queue_path = Path(args.queue)
    rows: List[Dict[str, str]] = []
    with queue_path.open() as f:
        r = csv.DictReader(f)
        fieldnames = r.fieldnames or []
        for row in r:
            rows.append(row)

    new_cols = [
        "availability_source_url",
        "code_availability_text",
        "code_availability_links",
        "data_availability_text",
        "data_availability_links",
    ]
    fieldnames = ensure_columns(list(fieldnames), new_cols)

    targets: List[int] = []
    for idx, row in enumerate(rows):
        journal = (row.get("journal") or "").strip()
        year = int((row.get("year") or 0) or 0)
        status = (row.get("search_status") or "").strip() or "pending"
        if journal in target_journals and year >= args.year_min and status == "pending":
            targets.append(idx)

    if args.limit:
        targets = targets[: args.limit]

    total_targets = len(targets)
    if not total_targets:
        print("No targets to process.")
        return 0

    processed = 0
    for start in range(0, total_targets, args.batch_size):
        batch = targets[start : start + args.batch_size]
        with ThreadPoolExecutor(max_workers=args.max_workers) as ex:
            futures = {ex.submit(process_row, rows[i]): i for i in batch}
            for fut in as_completed(futures):
                idx = futures[fut]
                update = fut.result()
                for k, v in update.items():
                    rows[idx][k] = v
                processed += 1
                if args.sleep:
                    time.sleep(args.sleep + random.random() * args.sleep)

        tmp_path = queue_path.with_suffix(".tmp")
        with tmp_path.open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            w.writerows(rows)
        tmp_path.replace(queue_path)

        print(f"Processed {processed}/{total_targets}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
