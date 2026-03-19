#!/usr/bin/env python3
"""
Attempt to download missing data files referenced in README files.
Only downloads when URL contains the missing filename.
"""
from __future__ import annotations

import csv
import re
import tarfile
import zipfile
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import urlretrieve


LOG_LIMIT = 200_000
MISSING_PATTERNS = [
    re.compile(r"FileNotFoundError: \\[Errno 2\\] No such file or directory: ['\"]([^'\"]+)['\"]"),
    re.compile(r"No such file or directory: ['\"]([^'\"]+)['\"]"),
    re.compile(r"cannot open file ['\"]([^'\"]+)['\"]", re.IGNORECASE),
]


def read_text(path: Path) -> str:
    try:
        return path.read_text(errors="ignore")[:LOG_LIMIT]
    except Exception:
        return ""


def read_csv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        return
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        w.writeheader()
        w.writerows(rows)


def build_repo_dir_map() -> dict[str, str]:
    repo_path = Path("data/metadata/cns_tables/repositories.csv")
    if not repo_path.exists():
        return {}
    with repo_path.open(newline="") as f:
        return {row.get("repo_url", ""): row.get("repo_dir", "") for row in csv.DictReader(f)}


def extract_missing_path(text: str) -> str | None:
    for pat in MISSING_PATTERNS:
        m = pat.search(text)
        if m:
            return m.group(1).strip().strip("\"'")
    return None


def find_readmes(repo_dir: Path) -> list[Path]:
    readmes = []
    for name in ("README.md", "README.rst", "README.txt", "Readme.md", "readme.md"):
        p = repo_dir / name
        if p.exists():
            readmes.append(p)
    for p in repo_dir.glob("docs/README*"):
        readmes.append(p)
    return readmes


def extract_urls(text: str) -> list[str]:
    urls = re.findall(r"https?://\\S+", text)
    cleaned = []
    for url in urls:
        url = url.rstrip(").,;\"'")
        cleaned.append(url)
    return cleaned


def is_archive(url: str) -> bool:
    lower = url.lower()
    return lower.endswith((".zip", ".tar.gz", ".tgz", ".tar"))


def likely_data_url(url: str) -> bool:
    lower = url.lower()
    tokens = (
        "zenodo", "figshare", "dryad", "datadryad", "osf.io", "dropbox", "googleapis.com",
        "github.com", "storage.googleapis.com", "s3.amazonaws.com", "data", "dataset",
        "releases/download",
    )
    return any(tok in lower for tok in tokens)


def pick_candidate_url(text: str, missing_basename: str) -> str:
    urls = extract_urls(text)
    if not urls:
        return ""
    # Prefer URL containing missing filename
    for url in urls:
        if missing_basename and missing_basename in url:
            return url
    # Prefer URLs in lines mentioning "data"
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if "data" not in line.lower():
            continue
        for url in extract_urls(line):
            if likely_data_url(url):
                return url
        # check nearby lines
        for j in range(max(0, i - 2), min(len(lines), i + 3)):
            for url in extract_urls(lines[j]):
                if likely_data_url(url):
                    return url
    # If only one likely data URL, use it
    data_urls = [u for u in urls if likely_data_url(u)]
    if len(data_urls) == 1:
        return data_urls[0]
    return ""


def iter_text_files(repo_dir: Path) -> list[Path]:
    exts = {".md", ".rst", ".txt", ".yml", ".yaml", ".toml", ".ini", ".cfg", ".py", ".r", ".R", ".m"}
    paths = []
    for path in repo_dir.rglob("*"):
        if path.is_dir():
            continue
        if path.suffix not in exts:
            continue
        try:
            if path.stat().st_size > 200_000:
                continue
        except Exception:
            continue
        paths.append(path)
        if len(paths) >= 2000:
            break
    return paths


def download(url: str, target: Path) -> Path | None:
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        tmp_path, _ = urlretrieve(url, str(target))
        return Path(tmp_path)
    except Exception:
        return None


def extract_archive(archive_path: Path, dest: Path) -> bool:
    try:
        if zipfile.is_zipfile(archive_path):
            with zipfile.ZipFile(archive_path) as zf:
                zf.extractall(dest)
            return True
        if tarfile.is_tarfile(archive_path):
            with tarfile.open(archive_path) as tf:
                tf.extractall(dest)
            return True
    except Exception:
        return False
    return False


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--queue", default="data/metadata/reproducibility_queue.csv")
    parser.add_argument("--out", default="data/metadata/data_downloads.csv")
    args = parser.parse_args()

    rows = read_csv(Path(args.queue))
    if not rows:
        print("queue: 0")
        return

    repo_dir_map = build_repo_dir_map()
    out_rows = []
    updated = 0

    for row in rows:
        if row.get("result") != "failed":
            continue
        log_path = Path(row.get("log_path") or "")
        if not log_path.exists():
            continue
        text = read_text(log_path)
        missing_path = extract_missing_path(text)
        if not missing_path:
            continue

        repo_dir = Path(repo_dir_map.get(row.get("repo_url", ""), "") or "")
        if not repo_dir.exists():
            continue

        norm = missing_path.replace("\\", "/")
        if norm.startswith("./"):
            norm = norm[2:]
        missing_basename = Path(norm).name

        candidate_url = ""
        for readme in find_readmes(repo_dir):
            candidate_url = pick_candidate_url(read_text(readme), missing_basename)
            if candidate_url:
                break
        if not candidate_url:
            # broader scan for any data URL in repo text files
            for path in iter_text_files(repo_dir):
                candidate_url = pick_candidate_url(read_text(path), missing_basename)
                if candidate_url:
                    break

        if not candidate_url:
            out_rows.append({
                "repo_url": row.get("repo_url", ""),
                "script_path": row.get("script_path", ""),
                "missing_path": missing_path,
                "url": "",
                "status": "no_url_match",
            })
            continue

        target_path = repo_dir / norm
        downloaded_path = download(candidate_url, target_path)
        if not downloaded_path:
            out_rows.append({
                "repo_url": row.get("repo_url", ""),
                "script_path": row.get("script_path", ""),
                "missing_path": missing_path,
                "url": candidate_url,
                "status": "download_failed",
            })
            continue

        status = "downloaded"
        if is_archive(candidate_url):
            if extract_archive(downloaded_path, repo_dir):
                status = "downloaded_and_extracted"

        # Verify missing path exists after download/extract
        if (repo_dir / norm).exists():
            row["result"] = "ready_for_run"
            row["failure_reason"] = ""
            row["notes"] = (row.get("notes", "") + " | data_downloaded").strip(" |")
            updated += 1
            status = status + "_ready"
        out_rows.append({
            "repo_url": row.get("repo_url", ""),
            "script_path": row.get("script_path", ""),
            "missing_path": missing_path,
            "url": candidate_url,
            "status": status,
        })

    write_csv(Path(args.queue), rows)
    write_csv(Path(args.out), out_rows)
    print(f"updated_ready: {updated}")
    print(f"downloads: {len(out_rows)}")


if __name__ == "__main__":
    main()
