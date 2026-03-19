#!/usr/bin/env python3
"""
Execute reproducibility queue entries and update results.
"""
from __future__ import annotations

import csv
import subprocess
import time
from pathlib import Path
from typing import Dict, List


def read_csv(path: Path) -> List[dict]:
    if not path.exists():
        return []
    with path.open() as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: List[dict]) -> None:
    if not rows:
        return
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        w.writeheader()
        w.writerows(rows)


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--start-index", type=int, default=0)
    parser.add_argument("--end-index", type=int, default=-1)
    parser.add_argument("--max-items", type=int, default=50)
    parser.add_argument("--timeout-seconds", type=int, default=1200)
    parser.add_argument("--only-ready", action="store_true", default=True)
    parser.add_argument("--continue-on-fail", action="store_true", default=True)
    parser.add_argument("--logs-dir", default="logs/repro_runs")
    args = parser.parse_args()

    queue_path = Path("data/metadata/reproducibility_queue.csv")
    rows = read_csv(queue_path)
    if not rows:
        print("queue: 0")
        return

    logs_dir = Path(args.logs_dir)
    logs_dir.mkdir(parents=True, exist_ok=True)

    selected = []
    for r in rows:
        if args.only_ready and r.get("result") != "ready_for_run":
            continue
        selected.append(r)

    if args.end_index >= 0:
        selected = selected[args.start_index:args.end_index]
    else:
        selected = selected[args.start_index:]

    if args.max_items > 0:
        selected = selected[: args.max_items]

    print(f"selected: {len(selected)}")

    repo_url_to_dir: Dict[str, str] = {}
    repos = read_csv(Path("data/metadata/cns_tables/repositories.csv"))
    for r in repos:
        repo_url_to_dir[r.get("repo_url", "")] = r.get("repo_dir", "")

    processed = 0
    for row in rows:
        if row not in selected:
            continue
        processed += 1
        repo_url = row.get("repo_url", "")
        repo_dir = repo_url_to_dir.get(repo_url, "")
        run_cmd = row.get("run_command", "")

        if not repo_dir or not run_cmd:
            row["result"] = "failed"
            row["failure_reason"] = "missing_repo_dir_or_command"
            continue

        ts = time.strftime("%Y%m%d_%H%M%S")
        log_path = logs_dir / f"run_{processed:04d}_{ts}.log"

        try:
            proc = subprocess.run(
                ["/bin/bash", "-lc", run_cmd],
                cwd=repo_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=args.timeout_seconds,
                text=True,
            )
            log_path.write_text(proc.stdout or "")
            row["log_path"] = str(log_path)
            row["timestamp"] = ts
            if proc.returncode == 0:
                row["result"] = "success"
                row["failure_reason"] = ""
            else:
                row["result"] = "failed"
                row["failure_reason"] = f"nonzero_exit_{proc.returncode}"
                if not args.continue_on_fail:
                    break
        except subprocess.TimeoutExpired as exc:
            log_path.write_text((exc.stdout or "") + "\nTIMEOUT\n")
            row["log_path"] = str(log_path)
            row["timestamp"] = ts
            row["result"] = "failed"
            row["failure_reason"] = "timeout"
            if not args.continue_on_fail:
                break
        except Exception as exc:
            row["result"] = "failed"
            row["failure_reason"] = f"error_{type(exc).__name__}"
            if not args.continue_on_fail:
                break

    write_csv(queue_path, rows)
    print(f"processed: {processed}")


if __name__ == "__main__":
    main()
