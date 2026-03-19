#!/usr/bin/env python3
"""
Summarize reproducibility results (success rate, top failures, successful repos).
"""
from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path


def read_csv(path: Path):
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def main() -> None:
    path = Path("data/metadata/reproducibility_queue.csv")
    if not path.exists():
        print("queue not found")
        return
    rows = read_csv(path)
    total = len(rows)
    results = Counter(r.get("result", "") for r in rows)
    failures = Counter(r.get("failure_reason", "") for r in rows if r.get("result") == "failed")

    success = results.get("success", 0)
    attempted = total - results.get("ready_for_run", 0) - results.get("needs_manual", 0)
    success_rate = (success / attempted * 100) if attempted else 0.0

    print(f"total: {total}")
    print(f"attempted: {attempted}")
    print(f"success: {success}")
    print(f"success_rate: {success_rate:.2f}%")
    print("top_failures:")
    for reason, count in failures.most_common(10):
        print(f"- {reason or 'unknown'}: {count}")

    repos = sorted({r.get("repo_url", "") for r in rows if r.get("result") == "success" and r.get("repo_url")})
    out_path = Path("data/metadata/repro_success_repos.txt")
    out_path.write_text("\n".join(repos) + ("\n" if repos else ""))
    print(f"success_repos: {len(repos)} -> {out_path}")


if __name__ == "__main__":
    main()
