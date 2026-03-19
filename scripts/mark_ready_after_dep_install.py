#!/usr/bin/env python3
"""
Mark failed rows as ready_for_run when missing Python deps were installed.
"""
from __future__ import annotations

import csv
from pathlib import Path


def load_failed_deps(path: Path) -> set[str]:
    if not path.exists():
        return set()
    return {line.strip() for line in path.read_text().splitlines() if line.strip()}


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--queue", default="data/metadata/reproducibility_queue.csv")
    parser.add_argument("--failed-deps", default="data/metadata/missing_python_deps_failed.txt")
    args = parser.parse_args()

    queue_path = Path(args.queue)
    failed_deps = load_failed_deps(Path(args.failed_deps))

    rows = []
    updated = 0
    with queue_path.open(newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []
        for row in reader:
            if row.get("result") == "failed":
                reason = row.get("failure_reason", "")
                if reason.startswith("missing_python_module:"):
                    dep = reason.split(":", 1)[1].strip()
                    if dep and dep not in failed_deps:
                        row["result"] = "ready_for_run"
                        row["failure_reason"] = ""
                        row["notes"] = (row.get("notes") or "") + (" | retry_after_dep_install" if row.get("notes") else "retry_after_dep_install")
                        updated += 1
            rows.append(row)

    with queue_path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"marked_ready: {updated}")


if __name__ == "__main__":
    main()
