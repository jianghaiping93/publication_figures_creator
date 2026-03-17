# Agent System Design

## Goal
Enable users to request figures by intent and receive consistent, reproducible outputs using sourced code.

## Core Flow
1. User intent parsing (figure type, dataset shape, constraints).
2. Retrieval (find candidate papers/repos/figures).
3. Selection (score by match, reproducibility, recency).
4. Adaptation (map user data to template inputs).
5. Rendering (run source code with unified style guide).
6. Validation (check output, log, and metadata).

## Components
- `IntentParser`: extracts figure type, required variables, and constraints.
- `Retriever`: queries database by figure type, journal, year, tags.
- `Scorer`: ranks candidates by match and reproducibility.
- `Renderer`: executes scripts in controlled environment.
- `StyleEnforcer`: applies palette, fonts, and layout rules.
- `Logger`: writes execution logs and output metadata.

## Inputs & Outputs
- Input: dataset path, desired figure type, constraints (size, color, labels).
- Output: figure file, provenance info, exact command, and logs.

## Error Handling
- If render fails, return top 3 alternative candidates.
- Persist failure logs and suggested fixes.

## MVP Interface (CLI)
- `figgen search --type heatmap --year 2024`
- `figgen render --paper n2024_001 --figure fig2 --data data.csv`

## Security Notes
- Run untrusted code in isolated environments.
- Pin dependencies to recorded versions.
