#!/usr/bin/env python3
"""
Retry CNS error repos by downloading GitHub tarballs (no clone), listing files,
and extracting figure-related assets. Updates index + figure files tables.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import os
import re
import subprocess
import tarfile
from pathlib import Path
from typing import Iterable, List, Tuple


CODE_EXTS = {
    ".py", ".r", ".R", ".Rmd", ".qmd", ".ipynb", ".m", ".jl", ".do", ".sas", ".sps",
    ".js", ".ts", ".mat", ".nw", ".tex"
}
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".svg", ".pdf", ".eps"}
FIG_KEYWORDS = ["fig", "figure", "figures", "plot", "chart", "graph", "panel", "extended_data", "extended-data"]


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
                if any(seg in lower for seg in ["figure", "figures", "figs", "plots", "charts", "graphs", "panels", "extended_data", "extended-data"]):
                    image_files.append(p)
        if ext in CODE_EXTS:
            if any(k in lower for k in FIG_KEYWORDS) or "/fig" in lower:
                code_files.append(p)
            else:
                if any(seg in lower for seg in ["figure", "figures", "figs", "plots", "charts", "graphs", "panels", "extended_data", "extended-data"]):
                    code_files.append(p)
    return sorted(set(code_files)), sorted(set(image_files))


def run(cmd: List[str]) -> Tuple[int, str, str]:
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    out, err = p.communicate()
    return p.returncode, out, err


def repo_slug(repo_url: str) -> str:
    m = re.match(r"https?://github\.com/([^/]+)/([^/]+)", repo_url)
    if not m:
        return "unknown__unknown"
    return f"{m.group(1)}__{m.group(2)}"


def parse_http_code(output: str) -> str:
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    if not lines:
        return ""
    last = lines[-1]
    return last if last.isdigit() else ""


def classify_curl_error(code: int, http_code: str, stderr: str) -> str:
    if http_code:
        return f"http_{http_code}"
    if code == 6:
        return "dns"
    if code == 28:
        return "timeout"
    if "Operation timed out" in stderr:
        return "timeout"
    if "Could not resolve host" in stderr:
        return "dns"
    if "SSL" in stderr or "TLS" in stderr:
        return "tls"
    return f"curl_{code}"


def download_tarball(
    repo_url: str,
    dest: Path,
    codeload_ip: str | None,
    branch: str,
    connect_timeout: int,
    max_time: int,
) -> Tuple[bool, str]:
    m = re.match(r"https?://github\.com/([^/]+)/([^/]+)", repo_url)
    if not m:
        return False, "bad_repo_url"
    owner, repo = m.group(1), m.group(2)
    url = f"https://codeload.github.com/{owner}/{repo}/tar.gz/refs/heads/{branch}"
    cmd = [
        "curl", "-sS", "-L",
        "--connect-timeout", str(connect_timeout),
        "--max-time", str(max_time),
        "-w", "\n%{http_code}\n",
        "-o", str(dest),
        url,
    ]
    if codeload_ip:
        cmd = [
            "curl", "-sS", "-L",
            "--connect-timeout", str(connect_timeout),
            "--max-time", str(max_time),
            "--resolve", f"codeload.github.com:443:{codeload_ip}",
            "-w", "\n%{http_code}\n",
            "-o", str(dest),
            url,
        ]
    code, out, err = run(cmd)
    http_code = parse_http_code(out)
    if code == 0 and dest.exists() and (http_code == "200" or http_code == ""):
        return True, ""
    return False, classify_curl_error(code, http_code, err)


def safe_extract_member(tf: tarfile.TarFile, member: tarfile.TarInfo, dest_root: Path) -> None:
    if not member.isfile():
        return
    # strip the top-level folder name
    parts = Path(member.name).parts
    rel = Path(*parts[1:]) if len(parts) > 1 else Path(parts[0])
    out_path = dest_root / rel
    out_path.parent.mkdir(parents=True, exist_ok=True)
    src = tf.extractfile(member)
    if not src:
        return
    with src, out_path.open("wb") as f:
        f.write(src.read())


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--index", default="data/metadata/cns_repo_figure_index.csv")
    ap.add_argument("--files", default="data/metadata/cns_repo_figure_files.csv")
    ap.add_argument("--assets-dir", default="data/figure_assets")
    ap.add_argument("--repos-file", default="data/metadata/cns_error_repos_urls.txt")
    ap.add_argument("--codeload-ip", default="")
    ap.add_argument("--max-assets", type=int, default=200)
    ap.add_argument("--connect-timeout", type=int, default=10)
    ap.add_argument("--max-time", type=int, default=45)
    args = ap.parse_args()

    index_path = Path(args.index)
    files_path = Path(args.files)
    assets_root = Path(args.assets_dir)
    repos_path = Path(args.repos_file)
    codeload_ip = args.codeload_ip.strip() or None

    repos = [line.strip() for line in repos_path.read_text().splitlines() if line.strip()]
    if not repos:
        print("no repos to retry")
        return

    # Load index rows
    with index_path.open() as f:
        rows = list(csv.DictReader(f))
    row_by_url = {r["repo_url"]: r for r in rows}

    # Load existing figure file rows and filter out retries
    existing_rows = []
    if files_path.exists():
        with files_path.open() as f:
            r = csv.DictReader(f)
            for row in r:
                if row.get("repo_url") not in repos:
                    existing_rows.append(row)

    new_rows = []
    today = dt.date.today().isoformat()

    for repo_url in repos:
        slug = repo_slug(repo_url)
        tar_path = Path(f"/tmp/{slug}.tar.gz")
        if tar_path.exists():
            tar_path.unlink()

        downloaded = False
        fail_reason = ""
        for branch in ("main", "master"):
            ok, reason = download_tarball(
                repo_url, tar_path, codeload_ip, branch,
                connect_timeout=args.connect_timeout,
                max_time=args.max_time,
            )
            if ok:
                downloaded = True
                break
            if reason:
                fail_reason = reason
        if not downloaded:
            row = row_by_url.get(repo_url)
            if row:
                row["scan_status"] = "error"
                row["notes"] = f"tar_download_failed:{fail_reason or 'unknown'}"
                row["last_scanned"] = today
            print(f"[tar] {repo_url} download failed ({fail_reason or 'unknown'})", flush=True)
            continue

        try:
            with tarfile.open(tar_path, "r:gz") as tf:
                paths = [m.name for m in tf.getmembers() if m.isfile()]
                # strip top-level dir in classification
                stripped = []
                for p in paths:
                    parts = Path(p).parts
                    rel = Path(*parts[1:]) if len(parts) > 1 else Path(parts[0])
                    stripped.append(str(rel))
                code_files, image_files = classify_files(stripped)

                # extract selected image assets
                extracted = 0
                dest_root = assets_root / slug
                for member in tf.getmembers():
                    if not member.isfile():
                        continue
                    parts = Path(member.name).parts
                    rel = Path(*parts[1:]) if len(parts) > 1 else Path(parts[0])
                    rel_str = str(rel)
                    if rel_str in image_files:
                        safe_extract_member(tf, member, dest_root)
                        extracted += 1
                        if extracted >= args.max_assets:
                            break

                for p in code_files:
                    new_rows.append({
                        "repo_url": repo_url,
                        "repo_slug": slug,
                        "file_kind": "code",
                        "file_path": p,
                    })
                for p in image_files:
                    new_rows.append({
                        "repo_url": repo_url,
                        "repo_slug": slug,
                        "file_kind": "image",
                        "file_path": p,
                    })

                row = row_by_url.get(repo_url)
                if row:
                    row["scan_status"] = "ok_tar"
                    row["figure_code_files"] = str(len(code_files))
                    row["figure_image_files"] = str(len(image_files))
                    row["copied_assets"] = str(extracted)
                    row["notes"] = "tar_list_extract_selected"
                    row["last_scanned"] = today
                print(
                    f"[tar] {repo_url} code={len(code_files)} images={len(image_files)} assets={extracted}",
                    flush=True,
                )
        except Exception as exc:
            row = row_by_url.get(repo_url)
            if row:
                row["scan_status"] = "error"
                row["notes"] = f"tar_process_failed: {exc}"
                row["last_scanned"] = today
            print(f"[tar] {repo_url} error: {exc}", flush=True)

    # write index
    with index_path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    # write figure files
    with files_path.open("w", newline="") as f:
        fieldnames = ["repo_url", "repo_slug", "file_kind", "file_path"]
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(existing_rows + new_rows)

    print("done", flush=True)


if __name__ == "__main__":
    main()
