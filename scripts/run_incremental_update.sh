#!/usr/bin/env bash
set -euo pipefail

FROM_DATE=${FROM_DATE:-$(date -u -d '90 days ago' +%F)}
TO_DATE=${TO_DATE:-$(date -u +%F)}
MAILTO=${MAILTO:-"914295425@qq.com"}

OUT_DIR="data/metadata/incremental/${FROM_DATE}_to_${TO_DATE}"
mkdir -p "$OUT_DIR"

python3 scripts/harvest_papers.py crossref \
  --journal "Nature" \
  --from-date "$FROM_DATE" \
  --to-date "$TO_DATE" \
  --mailto "$MAILTO" \
  --output "$OUT_DIR/crossref_nature.jsonl"

python3 scripts/harvest_papers.py crossref \
  --journal "Science" \
  --from-date "$FROM_DATE" \
  --to-date "$TO_DATE" \
  --mailto "$MAILTO" \
  --output "$OUT_DIR/crossref_science.jsonl"

python3 scripts/harvest_papers.py crossref \
  --journal "Cell" \
  --from-date "$FROM_DATE" \
  --to-date "$TO_DATE" \
  --mailto "$MAILTO" \
  --output "$OUT_DIR/crossref_cell.jsonl"

python3 scripts/extract_crossref_index.py \
  --inputs "$OUT_DIR/*.jsonl" \
  --out "$OUT_DIR/papers_index.csv"

python3 scripts/find_github_in_crossref.py \
  --inputs "$OUT_DIR/*.jsonl" \
  --out "$OUT_DIR/github_candidates.csv"

printf "[incremental] done %s -> %s\n" "$FROM_DATE" "$TO_DATE"
