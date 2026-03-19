#!/usr/bin/env bash
set -euo pipefail

BATCH_SIZE=${BATCH_SIZE:-50}
MAX_WORKERS=${MAX_WORKERS:-6}
CLONE_TIMEOUT=${CLONE_TIMEOUT:-120}
LOG=${LOG:-logs/cns_github_figure_miner.log}

BATCH_DIR=${BATCH_DIR:-data/metadata/cns_batches}
OUT_INDEX=${OUT_INDEX:-data/metadata/cns_repo_figure_index.csv}
OUT_MAP=${OUT_MAP:-data/metadata/cns_paper_repo_map.csv}
REPO_LIST=${REPO_LIST:-$BATCH_DIR/repo_list.txt}

mkdir -p "$BATCH_DIR"

python3 - <<'PY'
import csv
from pathlib import Path
from urllib.parse import urlparse
import re

out = Path("data/metadata/cns_batches/repo_list.txt")

def normalize_repo_url(url: str) -> str | None:
    url = url.strip().rstrip(").,;]\"'")
    parsed = urlparse(url)
    if parsed.netloc.lower() != "github.com":
        return None
    parts = [p for p in parsed.path.split("/") if p]
    if len(parts) < 2:
        return None
    owner, repo = parts[0], parts[1]
    repo = repo.replace(".git", "")
    if repo in {".", "..", "tree", "issues", "pull", "pulls"}:
        return None
    if not re.match(r"^[A-Za-z0-9_.-]+$", owner):
        return None
    if not re.match(r"^[A-Za-z0-9_.-]+$", repo):
        return None
    return f"https://github.com/{owner}/{repo}"

path = Path('data/metadata/repo_discovery_queue.csv')
rows = list(csv.DictReader(path.open()))
repos = set()
for r in rows:
    if (r.get('journal') or '').lower() not in {'nature','science','cell'}:
        continue
    for key in ('github_candidates','code_availability_links','data_availability_links','notes'):
        text = r.get(key,'') or ''
        for token in re.split(r"\s|;|,", text):
            if 'github.com' in token:
                if token.startswith('github.com/'):
                    token = 'https://' + token
                url = normalize_repo_url(token)
                if url:
                    repos.add(url)
repo_list = sorted(repos)
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text("\n".join(repo_list) + ("\n" if repo_list else ""))
print(len(repo_list))
PY

TOTAL=$(wc -l < "$REPO_LIST" | tr -d ' ')

echo "[batch] total_repos=${TOTAL} batch_size=${BATCH_SIZE} workers=${MAX_WORKERS} timeout=${CLONE_TIMEOUT}" >> "$LOG"

# generate paper->repo map once
python3 scripts/github_figure_miner.py --map-only --out-map "$OUT_MAP" --skip-clone --max-workers 1 >> "$LOG" 2>&1 || true

# reset index
rm -f "$OUT_INDEX"

START=0
while [ "$START" -lt "$TOTAL" ]; do
  END=$((START + BATCH_SIZE))
  if [ "$END" -gt "$TOTAL" ]; then END="$TOTAL"; fi
  echo "[batch] start=${START} end=${END} $(date -u +%FT%TZ)" >> "$LOG"
  BATCH_FILE="$BATCH_DIR/repo_list_${START}_${END}.txt"
  BATCH_OUT="$BATCH_DIR/index_${START}_${END}.csv"
  sed -n "$((START+1)),$((END))p" "$REPO_LIST" > "$BATCH_FILE"

  python3 -u scripts/github_figure_miner.py \
    --repos-file "$BATCH_FILE" \
    --out-index "$BATCH_OUT" \
    --max-workers "$MAX_WORKERS" \
    --clone-timeout "$CLONE_TIMEOUT" \
    --verbose >> "$LOG" 2>&1 || true

  if [ -f "$BATCH_OUT" ]; then
    if [ ! -f "$OUT_INDEX" ]; then
      cat "$BATCH_OUT" > "$OUT_INDEX"
    else
      tail -n +2 "$BATCH_OUT" >> "$OUT_INDEX"
    fi
  fi

  START=$END
  sleep 2
done

echo "[batch] done $(date -u +%FT%TZ)" >> "$LOG"
