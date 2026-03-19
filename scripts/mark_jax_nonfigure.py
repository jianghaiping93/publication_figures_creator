#!/usr/bin/env python3
"""
Mark JAX-related numpy2 retry failures as non-figure library tests.
"""
from __future__ import annotations

import csv
import re
from pathlib import Path


LOG_LIMIT = 200_000
JAX_TOKENS = ("jax", "jaxlib", "flax", "haiku", "optax")


def read_text(path: Path) -> str:
    try:
        return path.read_text(errors="ignore")[:LOG_LIMIT].lower()
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


def load_indices(path: Path) -> set[int]:
    indices = set()
    if not path.exists():
        return indices
    with path.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                indices.add(int(line))
            except Exception:
                continue
    return indices


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--queue", default="data/metadata/reproducibility_queue.csv")
    parser.add_argument("--numpy2-indices", default="data/metadata/repro_numpy2_indices.txt")
    parser.add_argument("--out", default="data/metadata/excluded_non_figure_scripts.csv")
    args = parser.parse_args()

    queue_path = Path(args.queue)
    rows = read_csv(queue_path)
    if not rows:
        print("queue: 0")
        return

    indices = load_indices(Path(args.numpy2_indices))
    if not indices:
        print("numpy2_indices: 0")
        return

    excluded = []
    marked = 0
    for idx in indices:
        if idx < 0 or idx >= len(rows):
            continue
        row = rows[idx]
        if row.get("result") != "failed":
            continue
        log_path = Path(row.get("log_path") or "")
        if not log_path.exists():
            continue
        text = read_text(log_path)
        if not any(tok in text for tok in JAX_TOKENS):
            continue
        row["result"] = "needs_manual"
        row["failure_reason"] = "non_figure_library_test_jax"
        row["notes"] = (row.get("notes", "") + " | exclude_jax_nonfigure").strip(" |")
        excluded.append({
            "index": idx,
            "repo_url": row.get("repo_url", ""),
            "script_path": row.get("script_path", ""),
            "reason": "library_test_nonfigure_jax",
            "log_path": row.get("log_path", ""),
        })
        marked += 1

    write_csv(queue_path, rows)

    if excluded:
        out_path = Path(args.out)
        if out_path.exists():
            existing = read_csv(out_path)
            excluded = existing + excluded
        write_csv(out_path, excluded)

    print(f"marked: {marked}")


if __name__ == "__main__":
    main()
