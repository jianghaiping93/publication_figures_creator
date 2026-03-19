#!/usr/bin/env python3
"""
Link plotting scripts to likely output images using filename/path heuristics.
"""
from __future__ import annotations

import csv
import re
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple


OUTPUT_DIR_HINTS = {
    "fig",
    "figure",
    "figures",
    "plot",
    "plots",
    "graph",
    "graphs",
    "image",
    "images",
    "output",
    "outputs",
    "result",
    "results",
    "panel",
    "panels",
}



def normalize_token(text: str) -> List[str]:
    parts = re.split(r"[^a-z0-9]+", text.lower())
    return [p for p in parts if p and len(p) > 2]


def stem_tokens(path: str) -> List[str]:
    stem = Path(path).stem.lower()
    return normalize_token(stem)


def dir_tokens(path: str) -> List[str]:
    p = Path(path)
    return normalize_token(" ".join(p.parts[:-1]))


def extract_paths(text: str) -> List[str]:
    pattern = re.compile(r"([\\w./\\-]+\\.(?:png|pdf|svg|jpg|jpeg|tif|tiff|eps))", re.IGNORECASE)
    return [m.group(1) for m in pattern.finditer(text)]


def read_readme_mentions(repo_dir: Path) -> Tuple[List[str], List[str]]:
    if not repo_dir.exists():
        return [], []
    candidates = []
    for name in ("README.md", "readme.md", "README.txt", "readme.txt"):
        path = repo_dir / name
        if path.exists():
            candidates.append(path)
    if not candidates:
        # fallback: first README* file
        candidates = list(repo_dir.glob("README*"))
    mentioned = []
    for path in candidates:
        try:
            text = path.read_text(errors="ignore")
        except Exception:
            continue
        mentioned.extend(extract_paths(text))
    basenames = [Path(p).name for p in mentioned]
    return mentioned, basenames


def read_text(path: Path, limit: int = 200_000) -> str:
    try:
        return path.read_text(errors="ignore")[:limit]
    except Exception:
        return ""

def read_script_mentions(script_path: Path) -> Tuple[List[str], List[str]]:
    if not script_path.exists():
        return [], []
    text = read_text(script_path)
    mentioned = extract_paths(text)
    basenames = [Path(p).name for p in mentioned]
    return mentioned, basenames

def score_pair(script_path: str, output_path: str, context: dict) -> Tuple[int, str, List[str]]:
    score = 0
    reasons = []
    evidence = []

    s_dir = str(Path(script_path).parent).lower()
    o_dir = str(Path(output_path).parent).lower()
    if s_dir == o_dir:
        score += 3
        reasons.append("same_dir")
    elif s_dir and o_dir and (s_dir in o_dir or o_dir in s_dir):
        score += 2
        reasons.append("dir_prefix")

    s_tokens = set(stem_tokens(script_path))
    o_tokens = set(stem_tokens(output_path))
    shared = s_tokens & o_tokens
    if shared:
        score += min(4, len(shared))
        reasons.append("shared_tokens")

    shared_dir_tokens = set(dir_tokens(script_path)) & set(dir_tokens(output_path))
    if shared_dir_tokens:
        score += 1
        reasons.append("shared_dir_tokens")

    s_stem = Path(script_path).stem.lower()
    o_stem = Path(output_path).stem.lower()
    if s_stem and s_stem in o_stem:
        score += 2
        reasons.append("script_in_output")
    if o_stem and o_stem in s_stem:
        score += 1
        reasons.append("output_in_script")

    output_dir_tokens = set(normalize_token(o_dir))
    if OUTPUT_DIR_HINTS & output_dir_tokens:
        score += 1
        reasons.append("output_dir_hint")

    output_basename = Path(output_path).name
    mentioned_basenames = context.get("mentioned_basenames", set())
    script_basenames = context.get("script_basenames", set())
    if output_basename in mentioned_basenames:
        score += 3
        reasons.append("readme_or_log_mention")
        evidence.append(output_basename)
    if output_basename in script_basenames:
        score += 4
        reasons.append("script_mention")
        evidence.append(output_basename)

    log_paths = context.get("log_paths", set())
    if output_path in log_paths:
        score += 4
        reasons.append("log_exact_path")
        evidence.append(output_path)
    script_paths = context.get("script_paths", set())
    if output_path in script_paths:
        score += 5
        reasons.append("script_exact_path")
        evidence.append(output_path)

    return score, "+".join(reasons), evidence


def read_csv(path: Path) -> List[dict]:
    with path.open() as f:
        return list(csv.DictReader(f))


def main() -> None:
    base = Path("data/metadata/cns_tables")
    scripts_path = base / "scripts.csv"
    outputs_path = base / "outputs.csv"
    out_path = base / "script_output_links.csv"
    repos_path = base / "repositories.csv"
    repro_path = Path("data/metadata/reproducibility_queue.csv")

    scripts = read_csv(scripts_path)
    outputs = read_csv(outputs_path)
    repos = read_csv(repos_path)
    repro_rows = read_csv(repro_path) if repro_path.exists() else []

    repo_id_to_dir = {r.get("repo_id", ""): r.get("repo_dir", "") for r in repos}
    repo_url_to_id = {r.get("repo_url", ""): r.get("repo_id", "") for r in repos}

    repo_log_paths: Dict[str, set] = defaultdict(set)
    for row in repro_rows:
        log_path = row.get("log_path", "")
        if not log_path:
            continue
        repo_id = repo_url_to_id.get(row.get("repo_url", ""), "")
        if not repo_id:
            continue
        log_file = Path(log_path)
        if not log_file.exists():
            continue
        text = read_text(log_file)
        for p in extract_paths(text):
            repo_log_paths[repo_id].add(p)

    outputs_by_repo: Dict[str, List[dict]] = defaultdict(list)
    for o in outputs:
        outputs_by_repo[o.get("repo_id", "")].append(o)

    rows = []
    for s in scripts:
        repo_id = s.get("repo_id", "")
        candidates = outputs_by_repo.get(repo_id, [])
        repo_dir = Path(repo_id_to_dir.get(repo_id, "")) if repo_id_to_dir.get(repo_id, "") else None
        mentioned_paths, mentioned_basenames = read_readme_mentions(repo_dir) if repo_dir else ([], [])
        script_paths, script_basenames = ([], [])
        if repo_dir:
            script_file = repo_dir / s.get("file_path", "")
            script_paths, script_basenames = read_script_mentions(script_file)
        context = {
            "mentioned_paths": set(mentioned_paths),
            "mentioned_basenames": set(mentioned_basenames),
            "log_paths": repo_log_paths.get(repo_id, set()),
            "script_paths": set(script_paths),
            "script_basenames": set(script_basenames),
        }
        scored = []
        for o in candidates:
            score, reason, evidence = score_pair(
                s.get("file_path", ""),
                o.get("file_path", ""),
                context,
            )
            if score > 0:
                scored.append((score, reason, evidence, o))
        scored.sort(key=lambda x: x[0], reverse=True)
        top = scored[0] if scored else None

        rows.append({
            "script_id": s.get("script_id", ""),
            "figure_id": s.get("figure_id", ""),
            "repo_id": repo_id,
            "script_path": s.get("file_path", ""),
            "language": s.get("language", ""),
            "figure_type_l1": s.get("figure_type_l1", ""),
            "figure_type_l2": s.get("figure_type_l2", ""),
            "matched_output_path": top[3].get("file_path", "") if top else "",
            "match_score": str(top[0]) if top else "0",
            "match_reason": top[1] if top else "",
            "match_evidence": "; ".join(top[2]) if top else "",
            "candidate_outputs": "; ".join([c[3].get("file_path", "") for c in scored[:5]]),
        })

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=[
            "script_id",
            "figure_id",
            "repo_id",
            "script_path",
            "language",
            "figure_type_l1",
            "figure_type_l2",
            "matched_output_path",
            "match_score",
            "match_reason",
            "match_evidence",
            "candidate_outputs",
        ])
        w.writeheader()
        w.writerows(rows)

    print(f"links: {len(rows)}")


if __name__ == "__main__":
    main()
