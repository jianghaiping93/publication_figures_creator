#!/usr/bin/env python3
"""
Minimal CLI for figure recommendation and styled rendering.
"""
from __future__ import annotations

import argparse
import csv
import subprocess
import time
from pathlib import Path
from typing import List


def read_csv(path: Path) -> List[dict]:
    if not path.exists():
        return []
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def normalize_token(text: str) -> List[str]:
    import re

    parts = re.split(r"[^a-z0-9]+", text.lower())
    return [p for p in parts if p]


def score_links(query: str, language: str) -> list[tuple[int, int, dict]]:
    links = read_csv(Path("data/metadata/cns_tables/script_output_links.csv"))
    tokens = set(normalize_token(query))
    scored = []
    for row in links:
        if language and row.get("language", "").lower() != language.lower():
            continue
        l2 = row.get("figure_type_l2", "")
        l1 = row.get("figure_type_l1", "")
        row_tokens = set(normalize_token(l2 + " " + l1))
        score = len(tokens & row_tokens)
        if score == 0 and tokens:
            continue
        scored.append((score, int(row.get("match_score", "0") or 0), row))
    if not scored:
        scored = [(0, int(r.get("match_score", "0") or 0), r) for r in links]
    scored.sort(key=lambda x: (x[0], x[1]), reverse=True)
    return scored


def recommend(args: argparse.Namespace) -> None:
    repos = read_csv(Path("data/metadata/cns_tables/repositories.csv"))
    repo_id_to_url = {r.get("repo_id", ""): r.get("repo_url", "") for r in repos}

    scored = score_links(args.query, args.language)

    print("script_id\trepo_url\tscript_path\toutput_path\tfigure_type_l2")
    for _, _, row in scored[: args.top]:
        repo_url = repo_id_to_url.get(row.get("repo_id", ""), "")
        print(
            f"{row.get('script_id','')}\t{repo_url}\t{row.get('script_path','')}\t{row.get('matched_output_path','')}\t{row.get('figure_type_l2','')}"
        )


def report(args: argparse.Namespace) -> None:
    repos = read_csv(Path("data/metadata/cns_tables/repositories.csv"))
    repo_id_to_url = {r.get("repo_id", ""): r.get("repo_url", "") for r in repos}
    queue_styled = Path("data/metadata/reproducibility_queue_styled.csv")
    queue = Path("data/metadata/reproducibility_queue.csv")
    queue_rows = read_csv(queue_styled) if queue_styled.exists() else read_csv(queue)
    scored = score_links(args.query, args.language)

    logs_dir = Path("logs/cli_reports")
    logs_dir.mkdir(parents=True, exist_ok=True)
    ts = time.strftime("%Y%m%d_%H%M%S")
    report_path = logs_dir / f"report_{ts}.md"

    lines = []
    lines.append("# Figure Recommendation Report")
    lines.append("")
    lines.append(f"- query: {args.query}")
    lines.append(f"- language: {args.language or 'any'}")
    lines.append(f"- theme: {args.theme or 'classic'}")
    lines.append("")
    lines.append("## Top Matches")
    lines.append("")
    lines.append("script_id | repo_url | script_path | output_path | figure_type_l2")
    lines.append("--- | --- | --- | --- | ---")
    for _, _, row in scored[: args.top]:
        repo_url = repo_id_to_url.get(row.get("repo_id", ""), "")
        lines.append(
            f"{row.get('script_id','')} | {repo_url} | {row.get('script_path','')} | "
            f"{row.get('matched_output_path','')} | {row.get('figure_type_l2','')}"
        )

    if scored:
        top = scored[0][2]
        repo_url = repo_id_to_url.get(top.get("repo_id", ""), "")
        script_path = top.get("script_path", "")
        qrow = next(
            (r for r in queue_rows if r.get("repo_url") == repo_url and r.get("script_path") == script_path),
            {},
        )
        run_cmd = qrow.get("run_command_styled") or qrow.get("run_command") or ""
        lines.append("")
        lines.append("## Reproducible Command (Top-1)")
        lines.append("")
        theme_prefix = f"PFC_STYLE_THEME={args.theme} " if args.theme else ""
        lines.append("```bash")
        lines.append(f"{theme_prefix}{run_cmd}".strip())
        lines.append("```")

    report_path.write_text("\n".join(lines) + "\n")
    print(f"[report] {report_path}")


def render(args: argparse.Namespace) -> None:
    links = read_csv(Path("data/metadata/cns_tables/script_output_links.csv"))
    repos = read_csv(Path("data/metadata/cns_tables/repositories.csv"))
    queue_styled = Path("data/metadata/reproducibility_queue_styled.csv")
    queue = Path("data/metadata/reproducibility_queue.csv")

    queue_rows = read_csv(queue_styled) if queue_styled.exists() else read_csv(queue)

    link = next((r for r in links if r.get("script_id") == args.script_id), None)
    if not link:
        raise SystemExit(f"script_id not found: {args.script_id}")

    repo = next((r for r in repos if r.get("repo_id") == link.get("repo_id")), None)
    if not repo:
        raise SystemExit("repo not found for script")

    repo_url = repo.get("repo_url", "")
    script_path = link.get("script_path", "")

    qrow = next(
        (r for r in queue_rows if r.get("repo_url") == repo_url and r.get("script_path") == script_path),
        None,
    )
    if not qrow:
        raise SystemExit("no run command found in reproducibility queue")

    run_cmd = qrow.get("run_command_styled") or qrow.get("run_command")
    if not run_cmd:
        raise SystemExit("run command is empty")
    if args.theme:
        run_cmd = f"PFC_STYLE_THEME={args.theme} {run_cmd}".strip()

    logs_dir = Path("logs/cli_runs")
    logs_dir.mkdir(parents=True, exist_ok=True)
    ts = time.strftime("%Y%m%d_%H%M%S")
    log_path = logs_dir / f"cli_{args.script_id}_{ts}.log"

    print(f"[run] {run_cmd}")
    proc = subprocess.run(
        ["/bin/bash", "-lc", run_cmd],
        cwd=repo.get("repo_dir", None),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    log_path.write_text(proc.stdout or "")
    print(f"[log] {log_path}")
    print(f"[exit] {proc.returncode}")


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_rec = sub.add_parser("recommend", help="Recommend scripts by query")
    p_rec.add_argument("--query", required=True)
    p_rec.add_argument("--top", type=int, default=10)
    p_rec.add_argument("--language", default="")
    p_rec.set_defaults(func=recommend)

    p_render = sub.add_parser("render", help="Render a script by script_id")
    p_render.add_argument("--script-id", required=True)
    p_render.add_argument("--theme", default="")
    p_render.set_defaults(func=render)

    p_report = sub.add_parser("report", help="Generate a recommendation report")
    p_report.add_argument("--query", required=True)
    p_report.add_argument("--top", type=int, default=10)
    p_report.add_argument("--language", default="")
    p_report.add_argument("--theme", default="classic")
    p_report.set_defaults(func=report)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
