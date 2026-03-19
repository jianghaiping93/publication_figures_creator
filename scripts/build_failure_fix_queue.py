#!/usr/bin/env python3
"""
Build a reproducibility failure fix queue by parsing run logs and results.
"""
from __future__ import annotations

import csv
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Tuple


FAIL_PATTERNS: List[Tuple[str, re.Pattern]] = [
    ("missing_python_module", re.compile(r"ModuleNotFoundError: No module named ['\"]([^'\"]+)['\"]")),
    ("missing_python_module", re.compile(r"ImportError: No module named ([\w\.]+)")),
    ("missing_python_module", re.compile(r"cannot import name ([\w_]+)")),
    ("relative_import", re.compile(r"attempted relative import with no known parent package", re.IGNORECASE)),
    ("bad_arguments", re.compile(r"error: unrecognized arguments", re.IGNORECASE)),
    ("bad_arguments", re.compile(r"usage: .+\\n.+error:", re.IGNORECASE)),
    ("missing_r_package", re.compile(r"there is no package called ['`\"]([^'`\"]+)['`\"]", re.IGNORECASE)),
    ("missing_r_package", re.compile(r"Error in library\(([^)]+)\)")),
    ("missing_r_package", re.compile(r"package ['`\"]([^'`\"]+)['`\"] is not available", re.IGNORECASE)),
    ("missing_matlab_function", re.compile(r"Undefined function or variable '([^']+)'")),
    ("missing_data", re.compile(r"FileNotFoundError: \[Errno 2\] No such file or directory: ['\"]([^'\"]+)['\"]")),
    ("missing_data", re.compile(r"No such file or directory: ['\"]([^'\"]+)['\"]")),
    ("missing_data", re.compile(r"cannot open file ['\"]([^'\"]+)['\"]", re.IGNORECASE)),
    ("missing_data", re.compile(r"does not exist: ['\"]([^'\"]+)['\"]", re.IGNORECASE)),
    ("path_error", re.compile(r"No such file or directory")),
    ("permission_error", re.compile(r"Permission denied")),
    ("timeout", re.compile(r"TIMEOUT")),
]


def read_csv(path: Path) -> List[dict]:
    if not path.exists():
        return []
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def read_text(path: Path, limit: int = 200_000) -> str:
    try:
        return path.read_text(errors="ignore")[:limit]
    except Exception:
        return ""


def infer_failure(log_text: str, failure_reason: str) -> Tuple[str, str, str]:
    dependency = ""
    missing_path = ""
    for bucket, pattern in FAIL_PATTERNS:
        m = pattern.search(log_text)
        if m:
            if bucket in {"missing_python_module", "missing_r_package", "missing_matlab_function"}:
                dependency = m.group(1).strip() if m.groups() else ""
            if bucket == "missing_data":
                missing_path = m.group(1).strip() if m.groups() else ""
            return bucket, dependency, missing_path

    if failure_reason == "timeout":
        return "timeout", "", ""
    if failure_reason.startswith("relative_import"):
        return "relative_import", "", ""
    if failure_reason.startswith("missing_system_python_module"):
        return "missing_system_python_module", "", ""
    if failure_reason.startswith("nonzero_exit"):
        return "nonzero_exit", "", ""
    if failure_reason.startswith("error_"):
        return "runtime_error", "", ""

    return "unknown", "", ""


def suggested_fix(bucket: str, dependency: str, missing_path: str) -> str:
    if bucket == "missing_python_module":
        return f"Install Python dependency: {dependency}" if dependency else "Install missing Python dependencies"
    if bucket == "missing_system_python_module":
        return "Manual: requires system Python modules (e.g., tkinter/idlelib)"
    if bucket == "missing_r_package":
        return f"Install R package: {dependency}" if dependency else "Install missing R packages"
    if bucket == "missing_matlab_function":
        return f"Add MATLAB toolbox or function: {dependency}" if dependency else "Install missing MATLAB toolbox"
    if bucket == "missing_data":
        return f"Fetch missing dataset: {missing_path}" if missing_path else "Download missing input data"
    if bucket == "path_error":
        return "Quote paths or use script_path relative to repo root"
    if bucket == "permission_error":
        return "Retry with MPLCONFIGDIR=/tmp/mpl XDG_CACHE_HOME=/tmp TMPDIR=/tmp"
    if bucket == "relative_import":
        return "Run via python -m package.module"
    if bucket == "bad_arguments":
        return "Check required CLI arguments; update run_command per README usage"
    if bucket == "timeout":
        return "Increase timeout or reduce dataset size"
    if bucket == "nonzero_exit":
        return "Inspect logs for exit code; ensure dependencies and data are available"
    if bucket == "runtime_error":
        return "Inspect runtime error; add missing deps or fix environment"
    return "Manual inspection required"


def main() -> None:
    queue_path = Path("data/metadata/reproducibility_queue.csv")
    rows = read_csv(queue_path)
    if not rows:
        print("queue: 0")
        return

    out_rows = []
    for row in rows:
        if row.get("result") != "failed":
            continue
        log_path = Path(row.get("log_path") or "")
        log_text = read_text(log_path) if log_path.exists() else ""
        bucket, dependency, missing_path = infer_failure(log_text, row.get("failure_reason", ""))
        out_rows.append({
            "repo_url": row.get("repo_url", ""),
            "script_path": row.get("script_path", ""),
            "language": row.get("language", ""),
            "failure_reason": row.get("failure_reason", ""),
            "fix_bucket": bucket,
            "dependency": dependency,
            "missing_path": missing_path,
            "fix_action": suggested_fix(bucket, dependency, missing_path),
            "suggested_fix": suggested_fix(bucket, dependency, missing_path),
            "log_path": row.get("log_path", ""),
        })

    out_path = Path("data/metadata/repro_fix_queue.csv")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if out_rows:
        with out_path.open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(out_rows[0].keys()))
            w.writeheader()
            w.writerows(out_rows)

    summary = Counter(r["fix_bucket"] for r in out_rows)
    summary_path = Path("data/metadata/repro_fix_summary.csv")
    with summary_path.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["fix_bucket", "count"])
        for bucket, count in summary.most_common():
            w.writerow([bucket, count])

    print(f"fix_queue: {len(out_rows)}")


if __name__ == "__main__":
    main()
