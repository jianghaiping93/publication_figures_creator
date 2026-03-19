#!/usr/bin/env python3
"""
Build reproducibility queue from script-output links.
"""
from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path
from typing import Dict, List


def read_csv(path: Path) -> List[dict]:
    if not path.exists():
        return []
    with path.open() as f:
        return list(csv.DictReader(f))


def main() -> None:
    base = Path("data/metadata")
    tables = base / "cns_tables"

    papers = read_csv(base / "cns_paper_repo_map.csv")
    repos = read_csv(tables / "repositories.csv")
    links = read_csv(tables / "script_output_links.csv")

    repo_id_to_url = {r.get("repo_id", ""): r.get("repo_url", "") for r in repos}
    repo_url_to_papers: Dict[str, List[str]] = defaultdict(list)
    for p in papers:
        repo_urls = [u.strip() for u in (p.get("repo_urls") or "").split(";") if u.strip()]
        doi = (p.get("doi") or "").strip()
        title = (p.get("title") or "").strip()
        journal = (p.get("journal") or "").strip()
        year = (p.get("year") or "").strip()
        paper_id = doi or f"{title}::{journal}::{year}"
        for url in repo_urls:
            repo_url_to_papers[url].append(paper_id)

    out_path = base / "reproducibility_queue.csv"
    rows = []

    for link in links:
        repo_id = link.get("repo_id", "")
        repo_url = repo_id_to_url.get(repo_id, "")
        paper_ids = repo_url_to_papers.get(repo_url, [])
        paper_id = paper_ids[0] if paper_ids else ""
        rows.append({
            "paper_id": paper_id,
            "figure_label": "",
            "panel_label": "",
            "repo_url": repo_url,
            "commit_or_tag": "",
            "script_path": link.get("script_path", ""),
            "run_command": "",
            "language": link.get("language", ""),
            "dependencies_file": "",
            "container_or_env": "",
            "os": "",
            "input_data_source": "",
            "input_data_path": "",
            "output_image_path": link.get("matched_output_path", ""),
            "output_format": Path(link.get("matched_output_path", "")).suffix.lstrip("."),
            "result": "pending",
            "failure_reason": "",
            "notes": f"match_score={link.get('match_score','0')}; match_reason={link.get('match_reason','')}; paper_ids={'; '.join(paper_ids)}",
            "log_path": "",
            "screenshot_path": "",
            "timestamp": "",
        })

    fieldnames = [
        "paper_id",
        "figure_label",
        "panel_label",
        "repo_url",
        "commit_or_tag",
        "script_path",
        "run_command",
        "language",
        "dependencies_file",
        "container_or_env",
        "os",
        "input_data_source",
        "input_data_path",
        "output_image_path",
        "output_format",
        "result",
        "failure_reason",
        "notes",
        "log_path",
        "screenshot_path",
        "timestamp",
    ]

    with out_path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)

    print(f"queue: {len(rows)}")


if __name__ == "__main__":
    main()
