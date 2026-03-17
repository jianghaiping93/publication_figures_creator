# GitHub Discovery & Reproducibility Rules

## Discovery Rules
- Primary sources:
  - Paper landing page (code availability section).
  - Supplementary materials (PDF/ZIP).
  - Author/project website.
- Secondary sources:
  - References in README or citations within related repos.
  - Issue/Discussion links mentioning “code” or “figure”.
- Query keywords (case-insensitive):
  - `code`, `github`, `repository`, `reproducibility`
  - `figure`, `fig`, `plot`, `visualization`

## Repository Qualification
- Must be public and accessible.
- Must include figure-generation scripts or notebooks.
- Prefer repos with clear usage instructions and pinned dependencies.

## Reproducibility Levels
- Level A: One-command figure generation with documented environment.
- Level B: Multi-step but fully documented; minor manual steps allowed.
- Level C: Code exists but missing dependencies or steps.
- Level D: Code incomplete or missing figure scripts.

## Evidence to Record
- Exact script path(s).
- Command used to generate figure.
- Dependency file (e.g., `requirements.txt`, `environment.yml`).
- Output files and logs.

## Exclusion Rules
- Non-public repos.
- Proprietary datasets required with no public alternative.
- Figures only available as static images (no code).
