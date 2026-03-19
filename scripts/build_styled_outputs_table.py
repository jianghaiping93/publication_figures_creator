#!/usr/bin/env python3
"""
Build a styled outputs table that records theme-aware wrapper commands.
"""
from __future__ import annotations

import csv
import hashlib
from pathlib import Path
from typing import List


THEMES = ["classic", "mono_ink", "ocean", "forest", "solar"]


def read_csv(path: Path) -> List[dict]:
    if not path.exists():
        return []
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def short_hash(value: str) -> str:
    return hashlib.sha1(value.encode("utf-8")).hexdigest()[:16]


def main() -> None:
    base = Path("data/metadata/cns_tables")
    scripts_path = base / "scripts.csv"
    repos_path = base / "repositories.csv"
    queue_path = Path("data/metadata/reproducibility_queue.csv")

    scripts = read_csv(scripts_path)
    repos = read_csv(repos_path)
    queue = read_csv(queue_path)

    repo_url_to_id = {r.get("repo_url", ""): r.get("repo_id", "") for r in repos}
    script_lookup = {(r.get("repo_id", ""), r.get("file_path", "")): r.get("script_id", "") for r in scripts}

    repo_root = Path(__file__).resolve().parents[1]
    py_wrapper = repo_root / "scripts" / "run_with_style.py"
    r_wrapper = repo_root / "scripts" / "run_with_style.R"
    m_wrapper = repo_root / "scripts" / "run_with_style_matlab.sh"

    rows: List[dict] = []
    for row in queue:
        repo_url = row.get("repo_url", "")
        repo_id = repo_url_to_id.get(repo_url, "")
        script_path = row.get("script_path", "")
        if not repo_id or not script_path:
            continue
        script_id = script_lookup.get((repo_id, script_path), "")
        if not script_id:
            continue
        language = (row.get("language", "") or "").lower()

        if language in {"python", "py"} or script_path.endswith(".py"):
            wrapper = "python"
            base_cmd = f"python {py_wrapper} {script_path}"
        elif language in {"r"} or script_path.endswith(".r"):
            wrapper = "r"
            base_cmd = f"Rscript {r_wrapper} {script_path}"
        elif language in {"matlab", "octave"} or script_path.endswith(".m"):
            wrapper = "matlab"
            base_cmd = f"bash {m_wrapper} {script_path}"
        else:
            wrapper = ""
            base_cmd = row.get("run_command", "")

        for theme in THEMES:
            styled_cmd = f"PFC_STYLE_THEME={theme} {base_cmd}".strip()
            styled_output_id = short_hash(f"{script_id}::{theme}::{styled_cmd}")
            rows.append({
                "styled_output_id": styled_output_id,
                "script_id": script_id,
                "repo_id": repo_id,
                "repo_url": repo_url,
                "script_path": script_path,
                "style_theme": theme,
                "style_wrapper": wrapper,
                "run_command_styled": styled_cmd,
                "status": "planned",
                "notes": "",
            })

    out_path = base / "styled_outputs.csv"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if rows:
        with out_path.open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
    print(f"styled_outputs: {len(rows)}")


if __name__ == "__main__":
    main()
