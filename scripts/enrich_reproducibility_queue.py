#!/usr/bin/env python3
"""
Enrich reproducibility queue with inferred commands and dependency hints.
Static analysis only (no code execution).
"""
from __future__ import annotations

import csv
import re
from pathlib import Path
from typing import Dict, List, Tuple

COMMAND_PATTERNS = [
    re.compile(r"\bpython\b[^\n]*\.py\b", re.IGNORECASE),
    re.compile(r"\bpython3\b[^\n]*\.py\b", re.IGNORECASE),
    re.compile(r"\bRscript\b[^\n]*\.R\b", re.IGNORECASE),
    re.compile(r"\bjupyter\b[^\n]*\.ipynb\b", re.IGNORECASE),
    re.compile(r"\bmatlab\b[^\n]*-batch[^\n]*", re.IGNORECASE),
    re.compile(r"\bsnakemake\b[^\n]*", re.IGNORECASE),
    re.compile(r"\bmake\b\s+[a-zA-Z0-9_\-]+", re.IGNORECASE),
]

BAD_SCRIPT_FILENAMES = {
    "__init__.py",
    "config.py",
    "default_config.py",
    "utils.py",
    "setup.py",
}

BAD_DIR_TOKENS = {
    "config",
    "configs",
    "core",
    "utils",
    "tests",
    "test",
    "docs",
    "doc",
}

STOPWORD_MAKE_TARGETS = {"the", "this", "that"}


def read_csv(path: Path) -> List[dict]:
    if not path.exists():
        return []
    with path.open() as f:
        return list(csv.DictReader(f))


def find_dependency_file(repo_dir: Path, language: str) -> str:
    candidates: List[str] = []
    if language in {"python", "notebook", ""}:
        candidates += [
            "requirements.txt",
            "environment.yml",
            "environment.yaml",
            "pyproject.toml",
            "setup.cfg",
            "setup.py",
            "Pipfile",
            "conda.yml",
            "conda.yaml",
        ]
    if language in {"r", "rmd", ""}:
        candidates += ["renv.lock", "DESCRIPTION"]

    for name in candidates:
        p = repo_dir / name
        if p.exists():
            return str(p)

    # lightweight fallback: top-level requirements*.txt only
    for p in repo_dir.glob("requirements*.txt"):
        return str(p)

    return ""


def find_readme_command(repo_dir: Path) -> str:
    readmes = list(repo_dir.glob("README*")) + list(repo_dir.glob("docs/README*"))
    for readme in readmes:
        try:
            text = readme.read_text(errors="ignore")[:20000]
        except OSError:
            continue
        for pattern in COMMAND_PATTERNS:
            match = pattern.search(text)
            if match:
                cmd = match.group(0).strip()
                if is_safe_command(cmd, repo_dir):
                    return cmd
    return ""

def is_bad_script_path(script_path: str) -> bool:
    if not script_path:
        return True
    p = Path(script_path)
    if p.name in BAD_SCRIPT_FILENAMES:
        return True
    parts = [part.lower() for part in p.parts]
    if any(t in parts for t in BAD_DIR_TOKENS):
        # allow if explicitly under figure/plot dirs
        if not any(tok in parts for tok in ("figure", "figures", "plot", "plots", "visualization", "viz")):
            return True
    return False


def is_safe_command(cmd: str, repo_dir: Path) -> bool:
    if not cmd:
        return False
    if cmd.lower().startswith("make "):
        target = cmd.split(maxsplit=1)[1].strip().lower()
        if target in STOPWORD_MAKE_TARGETS:
            return False
    if "python" in cmd.lower() and ".py" in cmd:
        parts = cmd.split()
        py_files = [p for p in parts if p.endswith(".py")]
        for py in py_files:
            if is_bad_script_path(py):
                return False
            if not (repo_dir / py).exists():
                return False
    return True

def infer_command(language: str, script_path: str) -> Tuple[str, str]:
    if not script_path:
        return "", ""
    if is_bad_script_path(script_path):
        return "", ""
    if language == "python" or script_path.endswith(".py"):
        return f"python {script_path}", "inferred_python"
    if language in {"r", "rmd"} or script_path.lower().endswith(".r"):
        return f"Rscript {script_path}", "inferred_r"
    if language == "notebook" or script_path.lower().endswith(".ipynb"):
        return f"jupyter nbconvert --execute {script_path}", "inferred_notebook"
    if language == "matlab" or script_path.lower().endswith(".m"):
        return f"matlab -batch \"run('{script_path}')\"", "inferred_matlab"
    if language == "julia" or script_path.lower().endswith(".jl"):
        return f"julia {script_path}", "inferred_julia"
    return "", ""


def main() -> None:
    base = Path("data/metadata")
    tables = base / "cns_tables"

    repos = read_csv(tables / "repositories.csv")
    queue_path = base / "reproducibility_queue.csv"
    queue = read_csv(queue_path)

    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--only-failed", action="store_true", default=False)
    parser.add_argument("--reset-failed", action="store_true", default=False)
    args = parser.parse_args()

    repo_id_to_dir: Dict[str, str] = {r.get("repo_id", ""): r.get("repo_dir", "") for r in repos}
    repo_url_to_id: Dict[str, str] = {r.get("repo_url", ""): r.get("repo_id", "") for r in repos}

    updated = []
    stats = {"ready": 0, "needs_manual": 0}

    for row in queue:
        if args.only_failed and row.get("result") != "failed":
            updated.append(row)
            continue
        repo_url = row.get("repo_url", "")
        repo_id = repo_url_to_id.get(repo_url, "")
        repo_dir = Path(repo_id_to_dir.get(repo_id, "")) if repo_id else None

        deps = row.get("dependencies_file", "")
        run_cmd = row.get("run_command", "")
        notes = row.get("notes", "")

        if repo_dir and repo_dir.exists():
            if not deps:
                deps = find_dependency_file(repo_dir, row.get("language", ""))
                if deps:
                    notes = (notes + " | deps_found").strip(" |")
            if run_cmd and not is_safe_command(run_cmd, repo_dir):
                run_cmd = ""
                notes = (notes + " | invalid_cmd").strip(" |")
            if not run_cmd:
                readme_cmd = find_readme_command(repo_dir)
                if readme_cmd:
                    run_cmd = readme_cmd
                    notes = (notes + " | readme_cmd").strip(" |")
                else:
                    inferred, tag = infer_command(row.get("language", ""), row.get("script_path", ""))
                    if inferred:
                        run_cmd = inferred
                        notes = (notes + f" | {tag}").strip(" |")

        status = "ready_for_run" if run_cmd else "needs_manual"
        if status == "ready_for_run":
            stats["ready"] += 1
        else:
            stats["needs_manual"] += 1

        row.update({
            "dependencies_file": deps,
            "run_command": run_cmd,
            "result": status if (args.reset_failed or row.get("result") in {"pending", "ready_for_run", "needs_manual"}) else row.get("result"),
            "notes": notes,
        })
        updated.append(row)

    if not updated:
        print("queue: 0")
        return

    with queue_path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=updated[0].keys())
        w.writeheader()
        w.writerows(updated)

    print(f"ready_for_run: {stats['ready']}")
    print(f"needs_manual: {stats['needs_manual']}")


if __name__ == "__main__":
    main()
