#!/usr/bin/env python3
"""
Build a download manifest for external datasets (Zenodo + Mendeley).
"""
from __future__ import annotations

import csv
import json
from pathlib import Path


def main() -> None:
    zenodo_path = Path("/tmp/zenodo_12205367.json")
    mendeley_path = Path("/tmp/mendeley_tc43t3s7c5.json")

    rows = []

    if zenodo_path.exists():
        zenodo = json.loads(zenodo_path.read_text())
        for f in zenodo.get("files", []):
            key = f.get("key", "")
            url = f.get("links", {}).get("self", "")
            rows.append({
                "source": "zenodo_12205367",
                "filename": key,
                "size": f.get("size", ""),
                "url": url,
                "dest": f"data/external_datasets/PrISMa_zenodo_12205367/{key}",
            })

    if mendeley_path.exists():
        mend = json.loads(mendeley_path.read_text())
        for f in mend.get("files", []):
            filename = f.get("filename", "")
            url = f.get("content_details", {}).get("download_url", "")
            rows.append({
                "source": "mendeley_tc43t3s7c5",
                "filename": filename,
                "size": f.get("size", ""),
                "url": url,
                "dest": f"data/external_datasets/mendeley_tc43t3s7c5/{filename}",
            })

    out_path = Path("data/metadata/external_dataset_downloads.csv")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if rows:
        with out_path.open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()), lineterminator="\n")
            w.writeheader()
            w.writerows(rows)
    print(f"manifest_rows: {len(rows)} -> {out_path}")


if __name__ == "__main__":
    main()
