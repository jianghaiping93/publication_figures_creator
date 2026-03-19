#!/usr/bin/env bash
set -euo pipefail

LOG=${LOG:-logs/cns_github_figure_miner.log}
OUT_INDEX=${OUT_INDEX:-data/metadata/cns_repo_figure_index.csv}
RETRY_INDEX=${RETRY_INDEX:-data/metadata/cns_repo_figure_index_retry.csv}
ERROR_LIST=${ERROR_LIST:-data/metadata/cns_batches/retry_repos.txt}
REPORT=${REPORT:-docs/cns_figure_report.md}

scripts/run_cns_github_batches.sh

python3 - <<'PY'
import csv
from pathlib import Path

out = Path('data/metadata/cns_batches/retry_repos.txt')
idx = Path('data/metadata/cns_repo_figure_index.csv')
rows = list(csv.DictReader(idx.open()))
errors = [r for r in rows if r.get('scan_status') == 'error']
repos = sorted({r['repo_url'] for r in errors if r.get('repo_url')})
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text("\n".join(repos) + ("\n" if repos else ""))
print(len(repos))
PY

if [ -s "$ERROR_LIST" ]; then
  echo "[retry] starting $(date -u +%FT%TZ)" >> "$LOG"
  python3 -u scripts/github_figure_miner.py \
    --repos-file "$ERROR_LIST" \
    --out-index "$RETRY_INDEX" \
    --max-workers 4 \
    --clone-timeout 120 \
    --verbose >> "$LOG" 2>&1 || true

  python3 - <<'PY'
import csv
from pathlib import Path

main_path = Path('data/metadata/cns_repo_figure_index.csv')
retry_path = Path('data/metadata/cns_repo_figure_index_retry.csv')
if not retry_path.exists():
    raise SystemExit(0)
main_rows = list(csv.DictReader(main_path.open()))
retry_rows = list(csv.DictReader(retry_path.open()))
by_url = {r['repo_url']: r for r in main_rows if r.get('repo_url')}
for r in retry_rows:
    url = r.get('repo_url')
    if not url:
        continue
    by_url[url] = r

fieldnames = main_rows[0].keys() if main_rows else retry_rows[0].keys()
with main_path.open('w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=fieldnames)
    w.writeheader()
    w.writerows(by_url.values())
PY
fi

python3 - <<'PY'
import csv
from collections import Counter
from pathlib import Path

def split_list(s):
    if not s:
        return []
    return [p for p in s.split('; ') if p]

idx = Path('data/metadata/cns_repo_figure_index.csv')
rows = list(csv.DictReader(idx.open())) if idx.exists() else []
status = Counter(r.get('scan_status','') for r in rows)

code_counts = []
img_counts = []
for r in rows:
    code_counts.append(len(split_list(r.get('figure_code_files',''))))
    img_counts.append(len(split_list(r.get('figure_image_files',''))))

pairs = []
for r in rows:
    code_n = len(split_list(r.get('figure_code_files','')))
    img_n = len(split_list(r.get('figure_image_files','')))
    pairs.append((code_n + img_n, r.get('repo_url','')))

pairs = sorted(pairs, reverse=True)[:20]
errors = [r for r in rows if r.get('scan_status') == 'error']

out = Path('docs/cns_figure_report.md')
out.parent.mkdir(parents=True, exist_ok=True)

lines = []
lines.append('# CNS Figure Mining Report')
lines.append('')
lines.append('## Summary')
lines.append(f"- Total repos scanned: {len(rows)}")
for k, v in status.most_common():
    lines.append(f"- {k}: {v}")
lines.append('')
lines.append('## Figure File Counts')
if rows:
    lines.append(f"- Median code files per repo: {sorted(code_counts)[len(code_counts)//2]}")
    lines.append(f"- Median image files per repo: {sorted(img_counts)[len(img_counts)//2]}")
lines.append('')
lines.append('## Top Repos By Figure Assets')
for total, url in pairs:
    if not url:
        continue
    lines.append(f"- {total} files: {url}")
lines.append('')
lines.append('## Errors')
if not errors:
    lines.append('- None')
else:
    for r in errors[:50]:
        lines.append(f"- {r.get('repo_url')}: {r.get('notes')}")

out.write_text('\n'.join(lines) + '\n')
PY


echo "[pipeline] done $(date -u +%FT%TZ)" >> "$LOG"
