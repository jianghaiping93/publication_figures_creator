#!/usr/bin/env python3
"""
Run a Python plotting script with unified matplotlib style applied.
"""
from __future__ import annotations

import argparse
import os
import runpy
import sys
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("script", help="Path to the python script to run")
    parser.add_argument("--theme", default="", help="Style theme name (classic, mono_ink, ocean, forest, solar)")
    parser.add_argument("script_args", nargs=argparse.REMAINDER, help="Arguments for the script")
    args = parser.parse_args()

    script_path = Path(args.script)
    if not script_path.exists():
        raise SystemExit(f"script not found: {script_path}")

    os.environ.setdefault("MPLBACKEND", "Agg")
    if args.theme:
        os.environ["PFC_STYLE_THEME"] = args.theme

    repo_root = Path(__file__).resolve().parents[1]
    style_dir = repo_root / "templates" / "python"
    sys.path.insert(0, str(style_dir))

    try:
        import matplotlib_style
        matplotlib_style.apply_matplotlib_style(args.theme or None)
    except Exception as exc:
        print(f"[style] failed to apply matplotlib style: {exc}")

    sys.argv = [str(script_path)] + args.script_args
    runpy.run_path(str(script_path), run_name="__main__")


if __name__ == "__main__":
    main()
