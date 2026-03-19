#!/usr/bin/env python3
"""
Create styled run commands for reproducibility queue entries.
"""
from __future__ import annotations

import csv
from pathlib import Path
from typing import List


def read_csv(path: Path) -> List[dict]:
    if not path.exists():
        return []
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--theme", default="classic", help="Style theme name")
    args = parser.parse_args()

    queue_path = Path("data/metadata/reproducibility_queue.csv")
    rows = read_csv(queue_path)
    if not rows:
        print("queue: 0")
        return

    repo_root = Path(__file__).resolve().parents[1]
    py_wrapper = repo_root / "scripts" / "run_with_style.py"
    r_wrapper = repo_root / "scripts" / "run_with_style.R"
    m_wrapper = repo_root / "scripts" / "run_with_style_matlab.sh"

    out_rows = []
    for row in rows:
        script_path = row.get("script_path", "")
        language = (row.get("language", "") or "").lower()
        styled_cmd = ""
        theme_prefix = f"PFC_STYLE_THEME={args.theme} " if args.theme else ""
        if language in {"python", "py"} or script_path.endswith(".py"):
            styled_cmd = f"{theme_prefix}python {py_wrapper} {script_path}"
            wrapper = "python"
        elif language in {"r"} or script_path.endswith(".r"):
            styled_cmd = f"{theme_prefix}Rscript {r_wrapper} {script_path}"
            wrapper = "r"
        elif language in {"matlab", "octave"} or script_path.endswith(".m"):
            styled_cmd = f"{theme_prefix}bash {m_wrapper} {script_path}"
            wrapper = "matlab"
        else:
            styled_cmd = f"{theme_prefix}{row.get('run_command', '')}".strip()
            wrapper = ""

        new_row = dict(row)
        new_row["run_command_styled"] = styled_cmd
        new_row["style_wrapper"] = wrapper
        out_rows.append(new_row)

    out_path = Path("data/metadata/reproducibility_queue_styled.csv")
    with out_path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(out_rows[0].keys()))
        w.writeheader()
        w.writerows(out_rows)

    print(f"styled_queue: {len(out_rows)}")


if __name__ == "__main__":
    main()
