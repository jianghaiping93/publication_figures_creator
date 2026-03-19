#!/usr/bin/env python3
"""
Apply automated fixes to reproducibility queue run commands and status.
"""
from __future__ import annotations

import csv
import re
import shutil
from pathlib import Path


def read_csv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        return
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        w.writeheader()
        w.writerows(rows)

def build_repo_dir_map() -> dict[str, str]:
    repo_path = Path("data/metadata/cns_tables/repositories.csv")
    if not repo_path.exists():
        return {}
    with repo_path.open(newline="") as f:
        return {row.get("repo_url", ""): row.get("repo_dir", "") for row in csv.DictReader(f)}


def needs_env_prefix(cmd: str) -> bool:
    return all(token not in cmd for token in ("MPLCONFIGDIR=", "XDG_CACHE_HOME=", "TMPDIR="))


def add_env_prefix(cmd: str) -> str:
    prefix = "MPLCONFIGDIR=/tmp/mpl XDG_CACHE_HOME=/tmp TMPDIR=/tmp "
    if cmd.strip().startswith(prefix.strip()):
        return cmd
    return prefix + cmd


def quote_path(cmd: str, path: str) -> tuple[str, bool]:
    if not path or path.startswith(("\"", "'")):
        return cmd, False
    if any(ch in path for ch in (" ", "(", ")")) and path in cmd:
        return cmd.replace(path, f"\"{path}\""), True
    return cmd, False


def module_path_from_script(script_path: str) -> str:
    if not script_path.endswith(".py"):
        return ""
    mod = script_path.replace("\\", "/")
    mod = mod.lstrip("./")
    mod = mod[:-3]
    if any(tok in mod for tok in (" ", "(", ")")):
        return ""
    mod = mod.replace("/", ".")
    if not re.fullmatch(r"[A-Za-z0-9_\\.]+", mod):
        return ""
    return mod


def normalize_command(cmd: str) -> tuple[str, list[str]]:
    notes: list[str] = []
    if not cmd:
        return cmd, notes

    new_cmd = cmd

    def sub(pattern: str, repl: str, label: str) -> None:
        nonlocal new_cmd, notes
        updated = re.sub(pattern, repl, new_cmd)
        if updated != new_cmd:
            new_cmd = updated
            notes.append(label)

    sub(r"(^|[;&|]\s*)python\s+", r"\1python3 ", "python->python3")
    sub(r"(^|[;&|]\s*)python\s+-m\s+", r"\1python3 -m ", "python-m->python3-m")
    sub(r"(^|[;&|]\s*)jupyter\s+", r"\1python3 -m jupyter ", "jupyter->python3 -m jupyter")
    sub(r"(^|[;&|]\s*)Make\b", r"\1make", "Make->make")
    if "jupyter nbconvert" in new_cmd and "--to" not in new_cmd:
        new_cmd = new_cmd + " --to html"
        notes.append("nbconvert_add_to")
    m = re.match(r"^(python3\\s+)([^\"'].*?\\.py)(\\s+.*)?$", new_cmd)
    if m:
        path = m.group(2)
        if any(ch in path for ch in (" ", "(", ")")):
            new_cmd = f"{m.group(1)}\"{path}\"{m.group(3) or ''}"
            notes.append("quote_py_path")

    return new_cmd, notes


def is_test_like(script_path: str) -> bool:
    if not script_path:
        return False
    lowered = script_path.replace("\\", "/").lower()
    if any(token in lowered for token in ("/tests/", "/test/")):
        return True
    name = Path(lowered).name
    return name.startswith("test_") or name.endswith("_test.py") or name.endswith("_tests.py") or name == "config_test.py"


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--queue", default="data/metadata/reproducibility_queue.csv")
    args = parser.parse_args()

    queue_path = Path(args.queue)
    rows = read_csv(queue_path)
    if not rows:
        print("queue: 0")
        return

    repo_dir_map = build_repo_dir_map()

    has_rscript = shutil.which("Rscript") is not None
    micromamba_path = shutil.which("micromamba")
    if not micromamba_path:
        candidate = Path.home() / ".local" / "bin" / "micromamba"
        if candidate.exists():
            micromamba_path = str(candidate)
    has_micromamba = micromamba_path is not None
    has_matlab = shutil.which("matlab") is not None

    updated = 0
    marked_manual = 0
    marked_ready = 0

    rscript_wrapper = ""
    if not has_rscript and has_micromamba and micromamba_path:
        rscript_wrapper = f"{micromamba_path} run -n pfc-r Rscript"

    for row in rows:
        cmd = row.get("run_command", "") or ""
        new_cmd, notes = normalize_command(cmd)
        if new_cmd != cmd:
            row["run_command"] = new_cmd
            updated += 1
            if notes:
                row["notes"] = (row.get("notes", "") + " | " + ",".join(notes)).strip(" |")

        lower_cmd = new_cmd.lower()
        failure_reason = row.get("failure_reason", "") or ""

        if failure_reason.startswith("missing_python_module:tkinter") or failure_reason.startswith(
            "missing_python_module:idlelib"
        ):
            row["result"] = "needs_manual"
            row["failure_reason"] = f"missing_system_python_module:{failure_reason.split(':',1)[1]}"
            marked_manual += 1

        if row.get("result") == "failed" and failure_reason.startswith("permission_denied"):
            if needs_env_prefix(new_cmd):
                new_cmd = add_env_prefix(new_cmd)
                row["run_command"] = new_cmd
                row["notes"] = (row.get("notes", "") + " | add_tmp_env").strip(" |")
                updated += 1
            row["result"] = "ready_for_run"
            row["failure_reason"] = ""
            marked_ready += 1

        if row.get("result") == "failed" and failure_reason.startswith("path_error:"):
            missing_path = failure_reason.split(":", 1)[1]
            new_cmd, did_quote = quote_path(new_cmd, missing_path)
            if did_quote:
                row["run_command"] = new_cmd
                row["notes"] = (row.get("notes", "") + " | quote_path").strip(" |")
                updated += 1
            repo_dir = repo_dir_map.get(row.get("repo_url", ""), "")
            script_path = row.get("script_path", "") or ""
            if repo_dir and script_path:
                candidate = Path(repo_dir) / script_path
                if candidate.exists() and row.get("language", "") == "python":
                    cmd_candidate = f"python3 \"{script_path}\"" if any(ch in script_path for ch in (" ", "(", ")")) else f"python3 {script_path}"
                    if cmd_candidate != new_cmd:
                        row["run_command"] = cmd_candidate
                        row["notes"] = (row.get("notes", "") + " | use_script_path").strip(" |")
                        updated += 1
                        row["result"] = "ready_for_run"
                        row["failure_reason"] = ""
                        marked_ready += 1

        if row.get("result") == "failed" and failure_reason.startswith("relative_import"):
            module_path = module_path_from_script(row.get("script_path", "") or "")
            if module_path:
                row["run_command"] = f"python3 -m {module_path}"
                row["notes"] = (row.get("notes", "") + " | python_module_run").strip(" |")
                row["result"] = "ready_for_run"
                row["failure_reason"] = ""
                updated += 1
                marked_ready += 1

        if row.get("result") == "failed" and is_test_like(row.get("script_path", "")):
            row["result"] = "needs_manual"
            row["failure_reason"] = "non_figure_script_test"
            row["notes"] = (row.get("notes", "") + " | test_script").strip(" |")
            marked_manual += 1

        if "](" in new_cmd and "http" in lower_cmd:
            row["result"] = "needs_manual"
            row["failure_reason"] = "invalid_markdown_command"
            marked_manual += 1
        if "rscript" in lower_cmd and not has_rscript:
            if rscript_wrapper:
                new_cmd = re.sub(r"(^|[;&|]\s*)Rscript\b", rf"\1{rscript_wrapper}", new_cmd)
                row["run_command"] = new_cmd
                row["notes"] = (row.get("notes", "") + " | rscript->micromamba").strip(" |")
                updated += 1
            else:
                row["result"] = "needs_manual"
                row["failure_reason"] = "missing_rscript"
                marked_manual += 1
        if ("matlab" in lower_cmd) and not has_matlab:
            row["result"] = "needs_manual"
            row["failure_reason"] = "missing_matlab"
            marked_manual += 1

        if row.get("result") == "failed" and row.get("failure_reason", "").startswith("nonzero_exit_127"):
            # Retry after command normalization (python/jupyter/make)
            if "missing_rscript" not in row.get("failure_reason", "") and "missing_matlab" not in row.get(
                "failure_reason", ""
            ):
                row["result"] = "ready_for_run"
                row["failure_reason"] = ""

    write_csv(queue_path, rows)
    print(f"updated_commands: {updated}")
    print(f"marked_needs_manual: {marked_manual}")
    print(f"marked_ready_for_run: {marked_ready}")


if __name__ == "__main__":
    main()
