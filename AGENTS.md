# Repository Guidelines

## Project Structure & Module Organization
This repository is documentation-only and does not contain application source code. Reference material lives in
`docs/`, and external resource links are centralized in `docs/github_ref.md`. Add new references under `docs/`
with clear, topical filenames such as `docs/diagram_refs.md` or `docs/figure_sources.md`. Avoid scattering
references elsewhere so that contributors can find and maintain links quickly.

## Build, Test, and Development Commands
There are no build, test, or runtime commands defined for this repository. If you introduce scripts or tooling
later, document them here with exact commands and short explanations (for example, `make lint` or
`python -m pytest`) so the workflow stays repeatable.

## Coding Style & Naming Conventions
Use Markdown for documentation. Keep lines reasonably short (around 100 characters) to preserve readability
across editors. Name files with lowercase, underscore-separated names (example: `figure_sources.md`). Use
clear, descriptive headings and avoid duplicate section titles within the same document.

## Testing Guidelines
No test framework is configured. If tests are introduced, document the framework, test location, naming
pattern (example: `test_*.py`), and how to run them in this section.

## Commit & Pull Request Guidelines
Git history is not available in this workspace, so no existing commit conventions can be verified. Suggested
commit format: short, imperative summary (example: `Add references for bio figure tools`). Pull requests should
include a concise description of what changed and why. Include links to relevant sources when you add or update
reference material. Add screenshots only if a change affects rendered documentation.

## Agent-Specific Instructions
Prefer minimal, focused edits. If you add new sections, keep the document within 200–400 words and keep the
tone professional and instructional.
