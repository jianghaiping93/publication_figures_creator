#!/usr/bin/env python3
"""
Run reproducibility queue entries in parallel and update results.
"""
from __future__ import annotations

import csv
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List, Tuple


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


def run_one(
    idx: int, row: dict, repo_dir: str, run_cmd: str, logs_dir: Path, timeout: int, venv: str | None
) -> Tuple[int, dict]:
    ts = time.strftime("%Y%m%d_%H%M%S")
    log_path = logs_dir / f"run_{idx:05d}_{ts}.log"
    result = dict(row)

    if not repo_dir or not run_cmd:
        result["result"] = "failed"
        result["failure_reason"] = "missing_repo_dir_or_command"
        return idx, result

    try:
        cmd = run_cmd
        if venv:
            cmd = f"source {venv}/bin/activate && {run_cmd}"
        proc = subprocess.run(
            ["/bin/bash", "-lc", cmd],
            cwd=repo_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
            text=True,
        )
        log_path.write_text(proc.stdout or "")
        result["log_path"] = str(log_path)
        result["timestamp"] = ts
        if proc.returncode == 0:
            result["result"] = "success"
            result["failure_reason"] = ""
        else:
            result["result"] = "failed"
            result["failure_reason"] = f"nonzero_exit_{proc.returncode}"
    except subprocess.TimeoutExpired as exc:
        log_path.write_text((exc.stdout or "") + "\nTIMEOUT\n")
        result["log_path"] = str(log_path)
        result["timestamp"] = ts
        result["result"] = "failed"
        result["failure_reason"] = "timeout"
    except Exception as exc:
        result["result"] = "failed"
        result["failure_reason"] = f"error_{type(exc).__name__}"

    return idx, result


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--max-items", type=int, default=0)
    parser.add_argument("--timeout-seconds", type=int, default=600)
    parser.add_argument("--max-workers", type=int, default=6)
    parser.add_argument("--flush-every", type=int, default=50)
    parser.add_argument("--logs-dir", default="logs/repro_runs")
    parser.add_argument("--venv", default="")
    parser.add_argument("--index-file", default="")
    parser.add_argument("--filter-failure", default="")
    args = parser.parse_args()

    queue_path = Path("data/metadata/reproducibility_queue.csv")
    rows = read_csv(queue_path)
    if not rows:
        print("queue: 0")
        return

    repos = read_csv(Path("data/metadata/cns_tables/repositories.csv"))
    repo_url_to_dir: Dict[str, str] = {r.get("repo_url", ""): r.get("repo_dir", "") for r in repos}

    selected_indices = [i for i, r in enumerate(rows) if r.get("result") == "ready_for_run"]
    if args.index_file:
        try:
            indices = []
            with Path(args.index_file).open() as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    indices.append(int(line))
            selected_indices = [i for i in selected_indices if i in set(indices)]
        except Exception:
            pass
    if args.filter_failure:
        token = args.filter_failure
        selected_indices = [i for i in selected_indices if token in (rows[i].get("failure_reason") or "")]
    if args.max_items > 0:
        selected_indices = selected_indices[: args.max_items]

    logs_dir = Path(args.logs_dir)
    logs_dir.mkdir(parents=True, exist_ok=True)

    print(f"selected: {len(selected_indices)}")

    completed = 0
    with ThreadPoolExecutor(max_workers=args.max_workers) as ex:
        futures = []
        for idx in selected_indices:
            row = rows[idx]
            repo_dir = repo_url_to_dir.get(row.get("repo_url", ""), "")
            run_cmd = row.get("run_command", "")
            venv = args.venv or None
            futures.append(ex.submit(run_one, idx, row, repo_dir, run_cmd, logs_dir, args.timeout_seconds, venv))

        for fut in as_completed(futures):
            idx, updated = fut.result()
            rows[idx] = updated
            completed += 1
            if args.flush_every > 0 and completed % args.flush_every == 0:
                write_csv(queue_path, rows)
                print(f"progress: {completed}/{len(selected_indices)}")

    write_csv(queue_path, rows)
    print(f"processed: {len(selected_indices)}")


if __name__ == "__main__":
    main()
