#!/usr/bin/env python3
"""
Split CNS figure database into normalized tables:
- papers
- repositories
- figures
- scripts
- outputs
"""
from __future__ import annotations

import csv
import hashlib
from pathlib import Path
from typing import Dict, List


def short_hash(value: str) -> str:
    return hashlib.sha1(value.encode("utf-8")).hexdigest()[:16]


def read_csv(path: Path) -> List[dict]:
    if not path.exists():
        return []
    with path.open() as f:
        return list(csv.DictReader(f))


def main() -> None:
    base = Path("data/metadata")
    papers_path = base / "cns_paper_repo_map.csv"
    repos_path = base / "cns_repo_figure_index_success.csv"
    figures_path = base / "cns_figure_db.csv"

    out_dir = base / "cns_tables"
    out_dir.mkdir(parents=True, exist_ok=True)

    paper_rows = read_csv(papers_path)
    repo_rows = read_csv(repos_path)
    figure_rows = read_csv(figures_path)

    papers = []
    repo_to_papers: Dict[str, List[str]] = {}

    for r in paper_rows:
        doi = (r.get("doi") or "").strip()
        title = (r.get("title") or "").strip()
        journal = (r.get("journal") or "").strip()
        year = (r.get("year") or "").strip()
        paper_key = doi or f"{title}::{journal}::{year}"
        paper_id = short_hash(paper_key)
        papers.append({
            "paper_id": paper_id,
            "journal": journal,
            "year": year,
            "doi": doi,
            "title": title,
        })

        repo_urls = [u.strip() for u in (r.get("repo_urls") or "").split(";") if u.strip()]
        for url in repo_urls:
            repo_to_papers.setdefault(url, [])
            if paper_id not in repo_to_papers[url]:
                repo_to_papers[url].append(paper_id)

    repositories = []
    for r in repo_rows:
        repo_url = (r.get("repo_url") or "").strip()
        repo_id = short_hash(repo_url)
        repositories.append({
            "repo_id": repo_id,
            "repo_url": repo_url,
            "repo_slug": r.get("repo_slug", ""),
            "repo_dir": r.get("repo_dir", ""),
            "scan_status": r.get("scan_status", ""),
            "notes": r.get("notes", ""),
            "last_scanned": r.get("last_scanned", ""),
            "paper_ids": "; ".join(repo_to_papers.get(repo_url, [])),
        })

    figures = []
    scripts = []
    outputs = []

    for r in figure_rows:
        repo_url = (r.get("repo_url") or "").strip()
        repo_id = short_hash(repo_url)
        figure_id = r.get("figure_id", "")
        file_path = r.get("file_path", "")
        file_kind = r.get("file_kind", "")
        figure_type_l1 = r.get("figure_type_l1", "")
        figure_type_l2 = r.get("figure_type_l2", "")
        tags = r.get("tags", "")
        paper_ids = "; ".join(repo_to_papers.get(repo_url, []))

        figures.append({
            "figure_id": figure_id,
            "repo_id": repo_id,
            "file_kind": file_kind,
            "file_path": file_path,
            "figure_type_l1": figure_type_l1,
            "figure_type_l2": figure_type_l2,
            "tags": tags,
            "paper_ids": paper_ids,
        })

        ext = Path(file_path).suffix.lower().lstrip(".")
        if file_kind == "code":
            lang_map = {
                "py": "python",
                "r": "r",
                "rmd": "rmd",
                "qmd": "quarto",
                "ipynb": "notebook",
                "m": "matlab",
                "jl": "julia",
            }
            scripts.append({
                "script_id": figure_id,
                "figure_id": figure_id,
                "repo_id": repo_id,
                "file_path": file_path,
                "language": lang_map.get(ext, ""),
                "figure_type_l1": figure_type_l1,
                "figure_type_l2": figure_type_l2,
                "tags": tags,
                "paper_ids": paper_ids,
            })
        elif file_kind == "image":
            outputs.append({
                "output_id": figure_id,
                "figure_id": figure_id,
                "repo_id": repo_id,
                "file_path": file_path,
                "asset_type": ext,
                "figure_type_l1": figure_type_l1,
                "figure_type_l2": figure_type_l2,
                "tags": tags,
                "paper_ids": paper_ids,
            })

    def write_csv(path: Path, rows: List[dict], fieldnames: List[str]) -> None:
        with path.open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            w.writerows(rows)

    write_csv(out_dir / "papers.csv", papers, ["paper_id", "journal", "year", "doi", "title"])
    write_csv(out_dir / "repositories.csv", repositories, [
        "repo_id",
        "repo_url",
        "repo_slug",
        "repo_dir",
        "scan_status",
        "notes",
        "last_scanned",
        "paper_ids",
    ])
    write_csv(out_dir / "figures.csv", figures, [
        "figure_id",
        "repo_id",
        "file_kind",
        "file_path",
        "figure_type_l1",
        "figure_type_l2",
        "tags",
        "paper_ids",
    ])
    write_csv(out_dir / "scripts.csv", scripts, [
        "script_id",
        "figure_id",
        "repo_id",
        "file_path",
        "language",
        "figure_type_l1",
        "figure_type_l2",
        "tags",
        "paper_ids",
    ])
    write_csv(out_dir / "outputs.csv", outputs, [
        "output_id",
        "figure_id",
        "repo_id",
        "file_path",
        "asset_type",
        "figure_type_l1",
        "figure_type_l2",
        "tags",
        "paper_ids",
    ])

    print(f"papers: {len(papers)}")
    print(f"repositories: {len(repositories)}")
    print(f"figures: {len(figures)}")
    print(f"scripts: {len(scripts)}")
    print(f"outputs: {len(outputs)}")


if __name__ == "__main__":
    main()
