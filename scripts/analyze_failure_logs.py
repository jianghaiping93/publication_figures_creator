#!/usr/bin/env python3
"""
Parse reproducibility logs and assign more specific failure reasons.
Updates reproducibility_queue.csv in-place and emits a summary CSV.
"""
from __future__ import annotations

import csv
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, Tuple


LOG_LIMIT = 200_000

PATTERNS = {
    "missing_python_module": [
        re.compile(r"ModuleNotFoundError: No module named ['\"]([^'\"]+)['\"]"),
        re.compile(r"ImportError: No module named ['\"]([^'\"]+)['\"]"),
    ],
    "missing_r_package": [
        re.compile(r"there is no package called ['\"]([^'\"]+)['\"]", re.IGNORECASE),
    ],
    "command_not_found": [
        re.compile(r"command not found", re.IGNORECASE),
        re.compile(r"not found: (python|python3|R|Rscript|matlab|make)", re.IGNORECASE),
    ],
    "permission_denied": [
        re.compile(r"Permission denied", re.IGNORECASE),
    ],
    "missing_gpu": [
        re.compile(r"CUDA|cudnn|cuDNN|torch\.cuda|no CUDA", re.IGNORECASE),
    ],
    "version_conflict": [
        re.compile(r"requires numpy[<>=!]=?\\s*([0-9.]+)", re.IGNORECASE),
        re.compile(r"numpy.*incompatible", re.IGNORECASE),
        re.compile(r"version.*conflict", re.IGNORECASE),
    ],
    "system_lib": [
        re.compile(r"GLIBC_|libstdc\\+\\+", re.IGNORECASE),
    ],
    "resource": [
        re.compile(r"out of memory|killed|oom", re.IGNORECASE),
    ],
    "bad_arguments": [
        re.compile(r"error: unrecognized arguments", re.IGNORECASE),
        re.compile(r"usage: .+\\n.+error:", re.IGNORECASE),
    ],
    "relative_import": [
        re.compile(r"attempted relative import with no known parent package", re.IGNORECASE),
    ],
}

DATA_EXTS = {".csv", ".tsv", ".txt", ".h5", ".hdf5", ".npz", ".npy", ".bam", ".fastq", ".fasta", ".mtx"}
SCRIPT_EXTS = {".py", ".r", ".R", ".m", ".ipynb", ".jl"}


def read_text(path: Path) -> str:
    try:
        return path.read_text(errors="ignore")[:LOG_LIMIT]
    except Exception:
        return ""


def classify_log(text: str) -> Tuple[str, str]:
    # FileNotFound handling first.
    m = re.search(r"FileNotFoundError: \\[Errno 2\\] No such file or directory: ['\"]([^'\"]+)['\"]", text)
    if m:
        missing_path = m.group(1)
        ext = Path(missing_path).suffix.lower()
        if ext in SCRIPT_EXTS:
            return "path_error", missing_path
        if ext in DATA_EXTS or any(tok in missing_path.lower() for tok in ("data", "dataset", "input")):
            return "missing_data", missing_path
        return "missing_file", missing_path

    # Script missing via python -m / can't open file
    m = re.search(r"can't open file ['\"]([^'\"]+)['\"]", text, re.IGNORECASE)
    if m:
        return "path_error", m.group(1)

    # Relative import issues.
    for pat in PATTERNS["relative_import"]:
        if pat.search(text):
            return "relative_import", ""

    # Bad arguments / usage errors.
    for pat in PATTERNS["bad_arguments"]:
        if pat.search(text):
            return "bad_arguments", ""

    # Missing modules/packages.
    for pat in PATTERNS["missing_python_module"]:
        m = pat.search(text)
        if m:
            return "missing_python_module", m.group(1)
    for pat in PATTERNS["missing_r_package"]:
        m = pat.search(text)
        if m:
            return "missing_r_package", m.group(1)

    # Other categories.
    for bucket in ("command_not_found", "permission_denied", "missing_gpu", "version_conflict", "system_lib", "resource"):
        for pat in PATTERNS[bucket]:
            if pat.search(text):
                return bucket, ""

    return "nonzero_exit", ""


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--queue", default="data/metadata/reproducibility_queue.csv")
    parser.add_argument("--summary", default="data/metadata/repro_failure_detail_summary.csv")
    args = parser.parse_args()

    queue_path = Path(args.queue)
    rows = []
    counts = Counter()
    dep_counts: Dict[str, Counter] = defaultdict(Counter)

    with queue_path.open(newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []
        for row in reader:
            if row.get("result") != "failed":
                rows.append(row)
                continue
            log_path = Path(row.get("log_path") or "")
            text = read_text(log_path) if log_path.exists() else ""
            bucket, detail = classify_log(text)
            row["failure_reason"] = bucket if not detail else f"{bucket}:{detail}"
            if detail:
                row["notes"] = (row.get("notes") or "") + (f" | {bucket}:{detail}" if row.get("notes") else f"{bucket}:{detail}")
            counts[bucket] += 1
            if detail and bucket in {"missing_python_module", "missing_r_package", "missing_data", "path_error"}:
                dep_counts[bucket][detail] += 1
            rows.append(row)

    with queue_path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    with Path(args.summary).open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["bucket", "count"])
        for bucket, count in counts.most_common():
            writer.writerow([bucket, count])

        writer.writerow([])
        writer.writerow(["bucket", "detail", "count"])
        for bucket, c in dep_counts.items():
            for detail, count in c.most_common(50):
                writer.writerow([bucket, detail, count])

    print(f"updated: {queue_path}")
    print(f"summary: {args.summary}")


if __name__ == "__main__":
    main()
