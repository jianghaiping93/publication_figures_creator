#!/usr/bin/env python3
"""
Install missing Python dependencies inferred from reproducibility logs.
"""
from __future__ import annotations

import csv
import subprocess
from importlib import metadata
from collections import Counter
from pathlib import Path


STD_LIB = {
    "tkinter",
    "idlelib",
    "distutils",
    "typing",
    "json",
    "csv",
    "pathlib",
    "math",
    "statistics",
    "itertools",
    "functools",
    "collections",
    "logging",
    "argparse",
    "re",
}

BLOCKLIST = {
    # Heavy GPU or system-lib dependencies; handle manually.
    "brainbox",
    "phylorank",
    "dolfinx",
    # Not on PyPI / requires manual setup.
    "consensus_variables",
    "storm_control",
    "tabix",
    "data_exploration_gui",
    "neuropixel",
    "genomicsurveillance",
    # Potentially heavy or version-sensitive.
    "jaxlib",
}

ALIASES = {
    "Bio": "biopython",
    "Bio._py3k": "biopython",
    "sklearn": "scikit-learn",
    "cv2": "opencv-python",
    "PIL": "pillow",
    "mpl_toolkits": "matplotlib",
    "yaml": "pyyaml",
    "bs4": "beautifulsoup4",
    "ruamel": "ruamel.yaml",
    "ruamel_yaml": "ruamel.yaml",
    "jax.jaxlib": "jaxlib",
    "pip._vendor.six": "six",
    "phy.gui": "phy",
    "prospect.fitting": "prospect",
    "gunpowder.contrib": "gunpowder",
}


def read_csv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--fix-queue", default="data/metadata/repro_fix_queue.csv")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    rows = read_csv(Path(args.fix_queue))
    deps: list[str] = []
    for r in rows:
        if r.get("fix_bucket") != "missing_python_module":
            continue
        dep = (r.get("dependency") or "").strip()
        if not dep or dep in STD_LIB:
            continue
        if dep in BLOCKLIST:
            continue
        if "." in dep and dep not in ALIASES:
            # Skip internal modules (e.g., package.submodule)
            continue
        if dep.startswith("pip."):
            continue
        deps.append(ALIASES.get(dep, dep))

    if not deps:
        print("deps: 0")
        return

    counts = Counter(deps)
    unique = [d for d, _ in counts.most_common()]
    print(f"unique_deps: {len(unique)}")

    failed: list[str] = []
    for dep in unique:
        if dep in BLOCKLIST:
            failed.append(dep)
            print("skip_blocklist:", dep)
            continue
        try:
            metadata.version(dep)
            print("already_installed:", dep)
            continue
        except metadata.PackageNotFoundError:
            pass
        cmd = ["python3", "-m", "pip", "install", "--user", dep]
        print("install:", dep)
        if args.dry_run:
            continue
        proc = subprocess.run(cmd, check=False)
        if proc.returncode != 0:
            failed.append(dep)

    if failed:
        out = Path("data/metadata/missing_python_deps_failed.txt")
        out.write_text("\n".join(failed) + "\n")
        print(f"failed_deps: {len(failed)} -> {out}")


if __name__ == "__main__":
    main()
