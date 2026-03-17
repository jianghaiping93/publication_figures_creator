# Paper Harvest Plan

## Scope
- Target journals: Nature, Science, Cell.
- Time window: last 3 years rolling. As of 2026-03-17, use 2023-03-17 to 2026-03-17.

## Output Format
- JSONL files, one record per line.
- Store raw API records for traceability.
- Location: `data/metadata/`.

## Crossref (Primary)
- Use Crossref Works API with date filters and a journal-title filter.
- Example:
  ```bash
  python scripts/harvest_papers.py crossref \
    --journal "Nature" \
    --from-date 2023-03-17 \
    --to-date 2026-03-17 \
    --mailto 914295425@qq.com \
    --output data/metadata/crossref_nature_2023_2026.jsonl
  ```

## OpenAlex (Secondary)
- Use OpenAlex Works API to cross-check completeness or enrich metadata.
- OpenAlex requires an API key for production use; pass it via `--api-key`.
- Resolve a source by ISSN first:
  ```bash
  python scripts/harvest_papers.py openalex-source --issn <ISSN>
  ```
- Then harvest by source ID or ISSN:
  ```bash
  python scripts/harvest_papers.py openalex \
    --issn <ISSN> \
    --from-date 2023-03-17 \
    --to-date 2026-03-17 \
    --api-key <OPENALEX_KEY> \
    --output data/metadata/openalex_nature_2023_2026.jsonl
  ```

## Minimal Fields to Extract (Later ETL)
- journal, year, title, doi, paper_url
- source link(s) to code repository
- funding/affiliation (optional)
