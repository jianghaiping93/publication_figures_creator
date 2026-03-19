# Database Schema (MVP)

## Goals
- Store paper, repository, and figure panel metadata.
- Enable search by journal, year, figure type, and reproducibility status.
- Track provenance (commit/tag) and execution details.

## Core Tables

### papers
- `paper_id` (pk)
- `journal` (nature/science/cell)
- `year`
- `title`
- `doi`
- `paper_url`

### repositories
- `repo_id` (pk)
- `paper_id` (fk)
- `github_url`
- `license`
- `default_branch`
- `commit_or_tag`
- `has_figure_code` (bool)

### figures
- `figure_id` (pk)
- `paper_id` (fk)
- `repo_id` (fk)
- `figure_label` (example: "Fig. 2")
- `panel_label` (example: "B")
- `figure_type_l1`
- `figure_type_l2`
- `multi_panel_group` (bool)

### scripts
- `script_id` (pk)
- `figure_id` (fk)
- `path`
- `run_command`
- `language`
- `dependencies`

### outputs
- `output_id` (pk)
- `figure_id` (fk)
- `image_path`
- `status` (success/failed)
- `log_path`
- `notes`

### styled_outputs (optional)
- `styled_output_id` (pk)
- `script_id` (fk)
- `repo_id` (fk)
- `style_theme` (classic/mono_ink/ocean/forest/solar)
- `style_wrapper` (python/r/matlab)
- `run_command_styled`
- `status` (planned/success/failed)

## Minimal Indexes
- `papers(journal, year)`
- `figures(figure_type_l1)`
- `repositories(github_url)`

## File Layout Suggestion
- Metadata CSV/JSON: `data/metadata/`
- Generated figures: `data/outputs/`
- Execution logs: `data/logs/`

## Validation Rules
- `figure_type_l1` must be in the taxonomy list.
- `run_command` required when `has_figure_code=true`.
- `status=failed` requires a `notes` entry.
