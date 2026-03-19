#!/usr/bin/env bash
set -euo pipefail

python3 scripts/build_failure_fix_queue.py
python3 scripts/run_reproducibility_queue_parallel.py --max-items 0 --timeout-seconds 300 --max-workers 8 --flush-every 50
