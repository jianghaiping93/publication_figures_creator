#!/usr/bin/env python3
"""
Mine GitHub repos linked to CNS (Nature/Science/Cell) papers for figure code and figure assets.

Outputs:
- data/metadata/cns_paper_repo_map.csv
- data/metadata/cns_repo_figure_index.csv
- data/figure_assets/<owner>__<repo>/ (selected files)
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import os
import re
import shutil
import subprocess
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Iterable, List, Dict, Tuple, Set

GITHUB_RE = re.compile(r"https?://github\.com/[^\s;,)\]]+")

CODE_EXTS = {
    ".py", ".r", ".R", ".Rmd", ".qmd", ".ipynb", ".m", ".jl", ".do", ".sas", ".sps",
    ".js", ".ts", ".mat", ".nw", ".tex"
}
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".svg", ".pdf", ".eps"}
FIG_KEYWORDS = ["fig", "figure", "figures", "plot", "chart", "graph", "panel", "extended_data", "extended-data"]


def run(cmd: List[str], cwd: Path | None = None, timeout: int | None = None) -> Tuple[int, str, str]:
    p = subprocess.Popen(
        cmd,
        cwd=str(cwd) if cwd else None,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        out, err = p.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        p.kill()
        out, err = p.communicate()
        return 124, out, err
    return p.returncode, out, err


def extract_github_urls(text: str) -> List[str]:
    if not text:
        return []
    urls = GITHUB_RE.findall(text)
    # also catch bare github.com/owner/repo
    for token in re.split(r"\s|;|,", text):
        if token.startswith("github.com/"):
            urls.append("https://" + token)
    return urls


def normalize_repo_url(url: str) -> str | None:
    # keep https://github.com/owner/repo
    url = url.strip().rstrip(").,;]\"'")
    parsed = urlparse(url)
    if parsed.netloc.lower() != "github.com":
        return None
    parts = [p for p in parsed.path.split("/") if p]
    if len(parts) < 2:
        return None
    owner, repo = parts[0], parts[1]
    repo = repo.replace(".git", "")
    if repo in {".", "..", "tree", "issues", "pull", "pulls"}:
        return None
    if not re.match(r"^[A-Za-z0-9_.-]+$", owner):
        return None
    if not re.match(r"^[A-Za-z0-9_.-]+$", repo):
        return None
    return f"https://github.com/{owner}/{repo}"


def parse_repos_from_row(row: Dict[str, str]) -> List[str]:
    texts = [
        row.get("github_candidates", ""),
        row.get("code_availability_links", ""),
        row.get("data_availability_links", ""),
        row.get("notes", ""),
    ]
    urls: List[str] = []
    for t in texts:
        urls.extend(extract_github_urls(t))
    repos = []
    for u in urls:
        n = normalize_repo_url(u)
        if n:
            repos.append(n)
    return sorted(set(repos))


def is_cns(row: Dict[str, str]) -> bool:
    return (row.get("journal") or "").lower() in {"nature", "science", "cell"}


def load_queue(path: Path) -> List[Dict[str, str]]:
    with path.open() as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: List[Dict[str, str]], fieldnames: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)


def load_repos_from_file(path: Path) -> List[str]:
    if path.suffix.lower() == ".csv":
        rows = list(csv.DictReader(path.open()))
        repos: Set[str] = set()
        for r in rows:
            for key in ("repo_url", "repo_urls"):
                val = r.get(key, "")
                if not val:
                    continue
                for token in val.split(";"):
                    n = normalize_repo_url(token.strip())
                    if n:
                        repos.add(n)
        return sorted(repos)
    repos = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        n = normalize_repo_url(line)
        if n:
            repos.append(n)
    return sorted(set(repos))


def repo_slug(repo_url: str) -> str:
    m = re.match(r"https?://github\.com/([^/]+)/([^/]+)", repo_url)
    if not m:
        return "unknown__unknown"
    return f"{m.group(1)}__{m.group(2)}"


def list_repo_files(repo_dir: Path) -> List[str]:
    code, out, err = run(["git", "ls-tree", "-r", "--name-only", "HEAD"], cwd=repo_dir, timeout=30)
    if code != 0:
        if code == 124:
            raise RuntimeError("git ls-tree timed out")
        raise RuntimeError(err.strip() or "git ls-tree failed")
    return [line.strip() for line in out.splitlines() if line.strip()]


def classify_files(paths: Iterable[str]) -> Tuple[List[str], List[str]]:
    code_files = []
    image_files = []
    for p in paths:
        lower = p.lower()
        ext = os.path.splitext(p)[1]
        if ext in IMAGE_EXTS:
            if any(k in lower for k in FIG_KEYWORDS) or "/fig" in lower or "fig" in os.path.basename(lower):
                image_files.append(p)
            else:
                # keep images if directory suggests figures
                if any(seg in lower for seg in ["figure", "figures", "figs", "plots", "charts", "graphs", "panels", "extended_data", "extended-data"]):
                    image_files.append(p)
            continue
        if ext in CODE_EXTS:
            if any(k in lower for k in FIG_KEYWORDS):
                code_files.append(p)
                continue
            # include notebooks and scripts in figure directories
            if any(seg in lower for seg in ["figure", "figures", "figs", "plots", "charts", "graphs", "panels", "extended_data", "extended-data"]):
                code_files.append(p)
    return code_files, image_files


def sparse_checkout(repo_dir: Path, paths: List[str]) -> None:
    run(["git", "sparse-checkout", "init", "--cone"], cwd=repo_dir, timeout=30)
    # switch to no-cone to allow file paths
    run(["git", "sparse-checkout", "set", "--no-cone"] + paths, cwd=repo_dir, timeout=60)


def copy_selected(repo_dir: Path, assets_dir: Path, paths: List[str]) -> Tuple[int, int]:
    lfs_ptrs = 0
    copied = 0
    for rel in paths:
        src = repo_dir / rel
        if not src.exists():
            continue
        dest = assets_dir / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        # detect lfs pointer
        try:
            with src.open("rb") as f:
                head = f.read(200)
            if b"git-lfs" in head and b"spec/v1" in head:
                lfs_ptrs += 1
                # still copy pointer for traceability
        except Exception:
            pass
        shutil.copy2(src, dest)
        copied += 1
    return copied, lfs_ptrs


def scan_repo(
    repo_url: str,
    repos_dir: Path,
    assets_root: Path,
    max_files_per_repo: int,
    max_assets_per_repo: int,
    skip_clone: bool,
    clone_timeout: int,
    verbose: bool,
) -> Dict[str, str]:
    slug = repo_slug(repo_url)
    repo_dir = repos_dir / slug
    status = "ok"
    notes = ""
    code_files: List[str] = []
    image_files: List[str] = []
    lfs_ptrs = 0
    copied = 0
    try:
        if verbose:
            print(f"[scan] {repo_url}")
        if repo_dir.exists() and not skip_clone:
            code, _, _ = run(["git", "rev-parse", "HEAD"], cwd=repo_dir, timeout=10)
            if code != 0:
                shutil.rmtree(repo_dir, ignore_errors=True)
        if not repo_dir.exists() and not skip_clone:
            code, out, err = run(
                [
                    "git",
                    "clone",
                    "--depth",
                    "1",
                    "--filter=blob:none",
                    "--sparse",
                    repo_url,
                    str(repo_dir),
                ],
                timeout=clone_timeout,
            )
            if code != 0:
                if code == 124:
                    shutil.rmtree(repo_dir, ignore_errors=True)
                    raise RuntimeError("git clone timed out")
                shutil.rmtree(repo_dir, ignore_errors=True)
                raise RuntimeError(err.strip() or out.strip() or "git clone failed")
        files = list_repo_files(repo_dir)
        code_files, image_files = classify_files(files)

        # limit selections
        code_files = code_files[:max_files_per_repo]
        image_files = image_files[: max(0, max_files_per_repo - len(code_files))]
        selected = code_files + image_files

        if selected and not skip_clone:
            sparse_checkout(repo_dir, selected)
            assets_dir = assets_root / slug
            copied, lfs_ptrs = copy_selected(repo_dir, assets_dir, selected[:max_assets_per_repo])
        else:
            notes = "no_figure_files_detected"
    except Exception as e:
        status = "error"
        notes = str(e)
        if verbose:
            print(f"[error] {repo_url} :: {notes}")

    return {
        "repo_url": repo_url,
        "repo_slug": slug,
        "repo_dir": str(repo_dir),
        "scan_status": status,
        "figure_code_files": "; ".join(code_files),
        "figure_image_files": "; ".join(image_files),
        "copied_assets": str(copied),
        "lfs_pointers": str(lfs_ptrs),
        "notes": notes,
        "last_scanned": dt.datetime.utcnow().isoformat() + "Z",
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--queue", default="data/metadata/repo_discovery_queue.csv")
    ap.add_argument("--out-map", default="data/metadata/cns_paper_repo_map.csv")
    ap.add_argument("--out-index", default="data/metadata/cns_repo_figure_index.csv")
    ap.add_argument("--repos-dir", default="data/github_repos")
    ap.add_argument("--assets-dir", default="data/figure_assets")
    ap.add_argument("--max-repos", type=int, default=0, help="0 for no limit")
    ap.add_argument("--start-index", type=int, default=0)
    ap.add_argument("--end-index", type=int, default=0, help="0 means until end")
    ap.add_argument("--max-files-per-repo", type=int, default=300)
    ap.add_argument("--max-assets-per-repo", type=int, default=200)
    ap.add_argument("--max-workers", type=int, default=6)
    ap.add_argument("--clone-timeout", type=int, default=120, help="seconds")
    ap.add_argument("--verbose", action="store_true")
    ap.add_argument("--skip-clone", action="store_true")
    ap.add_argument("--repos-file", default="")
    ap.add_argument("--map-only", action="store_true")
    args = ap.parse_args()

    paper_repo_rows = []
    repos: Set[str] = set()
    if args.repos_file:
        repos = set(load_repos_from_file(Path(args.repos_file)))
    else:
        queue = load_queue(Path(args.queue))
        cns = [r for r in queue if is_cns(r)]
        for r in cns:
            repo_list = parse_repos_from_row(r)
            if not repo_list:
                continue
            repos.update(repo_list)
            paper_repo_rows.append({
                "journal": r.get("journal", ""),
                "title": r.get("title", ""),
                "doi": r.get("doi", ""),
                "year": r.get("year", ""),
                "repo_urls": "; ".join(repo_list),
            })

    if not args.repos_file or args.map_only:
        write_csv(Path(args.out_map), paper_repo_rows, ["journal", "title", "doi", "year", "repo_urls"])
    if args.map_only:
        print(f"papers with repos: {len(paper_repo_rows)}")
        return

    repo_list = sorted(repos)
    if args.start_index:
        repo_list = repo_list[args.start_index :]
    if args.end_index:
        repo_list = repo_list[: args.end_index]
    if args.max_repos:
        repo_list = repo_list[: args.max_repos]

    repos_dir = Path(args.repos_dir)
    assets_root = Path(args.assets_dir)
    repos_dir.mkdir(parents=True, exist_ok=True)
    assets_root.mkdir(parents=True, exist_ok=True)

    index_rows = []
    if args.max_workers <= 1:
        for repo_url in repo_list:
            index_rows.append(
                scan_repo(
                    repo_url,
                    repos_dir,
                    assets_root,
                    args.max_files_per_repo,
                    args.max_assets_per_repo,
                    args.skip_clone,
                    args.clone_timeout,
                    args.verbose,
                )
            )
    else:
        with ThreadPoolExecutor(max_workers=args.max_workers) as ex:
            futs = [
                ex.submit(
                    scan_repo,
                    repo_url,
                    repos_dir,
                    assets_root,
                    args.max_files_per_repo,
                    args.max_assets_per_repo,
                    args.skip_clone,
                    args.clone_timeout,
                    args.verbose,
                )
                for repo_url in repo_list
            ]
            for fut in as_completed(futs):
                index_rows.append(fut.result())

    write_csv(
        Path(args.out_index),
        index_rows,
        [
            "repo_url",
            "repo_slug",
            "repo_dir",
            "scan_status",
            "figure_code_files",
            "figure_image_files",
            "copied_assets",
            "lfs_pointers",
            "notes",
            "last_scanned",
        ],
    )

    print(f"repos: {len(repo_list)}")
    print(f"papers with repos: {len(paper_repo_rows)}")


if __name__ == "__main__":
    main()
