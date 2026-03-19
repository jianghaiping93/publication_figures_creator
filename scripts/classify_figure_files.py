#!/usr/bin/env python3
"""
Classify CNS figure-related files into taxonomy categories and build a CSV database.
"""
from __future__ import annotations

import csv
import hashlib
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List, Tuple

L1_TYPES = [
    "Heatmap",
    "Scatter Plot",
    "Line Chart",
    "Bar Chart",
    "Box/Violin Plot",
    "Histogram/Density",
    "Area/Stacked Chart",
    "Pie/Donut",
    "Treemap/Sunburst",
    "Waffle/Isotype",
    "Radar/Polar",
    "Venn/Set",
    "ROC/PR Curve",
    "Network/Graph",
    "Pathway/Diagram",
    "Image Panel",
    "Spatial/Map",
    "Tree/Phylogeny",
    "Dimensionality Reduction",
    "Genome Tracks",
    "Flow Cytometry",
    "Raster/Spike",
    "Table",
    "3D/Structure",
    "Multi-Panel Composite",
    "Plotting Script (Generic)",
    "Other/Uncategorized",
]

KEYWORD_RULES = [
    ("Flow Cytometry", ["facs", "cytometry", "flowcyto", "flow_cytometry", "gating"]),
    ("Genome Tracks", ["genome", "igv", "bigwig", "bedgraph", "bed", "track", "chip", "atac", "manhattan", "qqplot", "circos", "ideogram", "locus", "loci"]),
    ("Dimensionality Reduction", ["umap", "tsne", "t-sne", "pca", "embedding"]),
    ("Heatmap", ["heatmap", "heat_map", "clustermap", "corr", "correlation", "matrix", "tilemap"]),
    ("Scatter Plot", ["scatter", "volcano", "ma_plot", "ma-plot", "ma.plot", "dotplot", "dot_plot", "bubble"]),
    ("Line Chart", ["timeseries", "time_series", "trajectory", "trend", "curve", "lineplot"]),
    ("Bar Chart", ["barplot", "bar_plot", "stacked_bar", "grouped_bar", "barh"]),
    ("Box/Violin Plot", ["boxplot", "violin", "violinplot", "box_plot", "box_whisker"]),
    ("Histogram/Density", ["histogram", "density", "kde", "ridgeplot"]),
    ("Area/Stacked Chart", ["stackplot", "stacked_area", "area_plot", "streamgraph", "stackedarea"]),
    ("Pie/Donut", ["pie", "donut", "doughnut"]),
    ("Treemap/Sunburst", ["treemap", "sunburst"]),
    ("Waffle/Isotype", ["waffle", "isotype", "pictogram"]),
    ("Radar/Polar", ["radar", "spider", "polar"]),
    ("Venn/Set", ["venn", "upset"]),
    ("ROC/PR Curve", ["roc", "pr_curve", "precision_recall", "auc"]),
    ("Network/Graph", ["network", "graph", "ppi", "interaction", "coexpression", "co-expression", "sankey", "chord"]),
    ("Tree/Phylogeny", ["phylo", "phylogeny", "dendro", "dendrogram", "cladogram", "tree"]),
    ("Spatial/Map", ["spatial", "map", "atlas", "gis", "coordinate", "brain", "tissue", "topography"]),
    ("3D/Structure", ["3d", "surface", "mesh", "isosurface", "pdb", "structure", "molecule", "protein", "volume", "render"]),
    ("Raster/Spike", ["raster", "spike", "psth"]),
    ("Pathway/Diagram", ["pathway", "diagram", "schematic", "workflow", "circuit", "model", "cartoon"]),
    ("Table", ["table", "datatable", "sheet", "supp_table", "supplementary_table", "tab"]),
    ("Image Panel", [
        "microscopy", "image", "img", "blot", "gel", "ihc", "if", "immuno", "confocal",
        "brightfield", "histology", "stain", "em", "segmentation", "mask", "label",
        "annotation", "overlay", "dicom", "nifti", "nii", "mri", "ct", "xray", "x-ray",
        "ultrasound", "pet", "spect", "atlas", "pathology",
    ]),
    ("Multi-Panel Composite", ["panel", "figure", "fig", "supplement", "extended_data", "ed_fig", "suppfig", "supfig", "multi_panel", "multipanel"]),
    ("Plotting Script (Generic)", ["plot", "chart", "visual", "ggplot", "matplotlib", "seaborn", "plotly", "bokeh", "altair", "vega", "geom"]),
]

L2_RULES = [
    ("Heatmap", "Correlation Matrix", ["corr", "correlation", "matrix"]),
    ("Heatmap", "Clustered Heatmap", ["clustermap"]),
    ("Scatter Plot", "Volcano", ["volcano"]),
    ("Scatter Plot", "MA Plot", ["ma_plot", "ma-plot", "ma.plot"]),
    ("Scatter Plot", "Dot Plot", ["dotplot", "dot_plot"]),
    ("Scatter Plot", "Bubble Plot", ["bubble"]),
    ("Line Chart", "Time Series", ["time", "timeseries", "time_series"]),
    ("Line Chart", "Trajectory", ["trajectory"]),
    ("Bar Chart", "Grouped Bar", ["grouped_bar"]),
    ("Bar Chart", "Stacked Bar", ["stacked_bar"]),
    ("Bar Chart", "Horizontal Bar", ["barh"]),
    ("Box/Violin Plot", "Box Plot", ["box", "boxplot"]),
    ("Box/Violin Plot", "Violin Plot", ["violin"]),
    ("Histogram/Density", "Histogram", ["hist", "histogram"]),
    ("Histogram/Density", "Density/KDE", ["density", "kde", "ridgeplot"]),
    ("Area/Stacked Chart", "Stacked Area", ["stackplot", "stacked_area", "stackedarea"]),
    ("Area/Stacked Chart", "Streamgraph", ["streamgraph"]),
    ("Pie/Donut", "Pie Chart", ["pie"]),
    ("Pie/Donut", "Donut Chart", ["donut", "doughnut"]),
    ("Treemap/Sunburst", "Treemap", ["treemap"]),
    ("Treemap/Sunburst", "Sunburst", ["sunburst"]),
    ("Waffle/Isotype", "Waffle Chart", ["waffle"]),
    ("Waffle/Isotype", "Isotype/Pictogram", ["isotype", "pictogram"]),
    ("Radar/Polar", "Radar Chart", ["radar", "spider"]),
    ("Radar/Polar", "Polar Chart", ["polar"]),
    ("Venn/Set", "Venn Diagram", ["venn"]),
    ("Venn/Set", "UpSet", ["upset"]),
    ("ROC/PR Curve", "ROC", ["roc"]),
    ("ROC/PR Curve", "Precision-Recall", ["pr_curve", "precision_recall"]),
    ("Network/Graph", "Sankey", ["sankey"]),
    ("Network/Graph", "Chord Diagram", ["chord"]),
    ("Pathway/Diagram", "Workflow", ["workflow"]),
    ("Pathway/Diagram", "Schematic", ["schematic", "cartoon"]),
    ("Image Panel", "Microscopy", ["microscopy", "confocal", "brightfield"]),
    ("Image Panel", "Western Blot/Gel", ["blot", "gel"]),
    ("Image Panel", "Histology/IHC/IF", ["ihc", "if", "immuno", "histology", "stain"]),
    ("Image Panel", "EM", ["em"]),
    ("Image Panel", "Segmentation/Mask", ["segmentation", "mask", "label", "annotation", "overlay"]),
    ("Image Panel", "Clinical Imaging (MRI/CT/US/X-ray)", ["mri", "ct", "xray", "x-ray", "ultrasound", "pet", "spect", "dicom", "nifti", "nii"]),
    ("Image Panel", "Atlas/Reference", ["atlas", "template", "labelmap", "label_map"]),
    ("Image Panel", "Pathology", ["pathology", "histopath", "whole_slide", "wsi"]),
    ("Spatial/Map", "Atlas/Map", ["atlas", "map"]),
    ("Spatial/Map", "Brain/Tissue Map", ["brain", "tissue"]),
    ("Spatial/Map", "Spatial Transcriptomics", ["visium", "spatial_transcript", "spatialtranscript"]),
    ("Tree/Phylogeny", "Phylogeny", ["phylo", "phylogeny"]),
    ("Tree/Phylogeny", "Dendrogram", ["dendro", "dendrogram"]),
    ("Dimensionality Reduction", "UMAP", ["umap"]),
    ("Dimensionality Reduction", "t-SNE", ["tsne", "t-sne"]),
    ("Dimensionality Reduction", "PCA", ["pca"]),
    ("Genome Tracks", "Genome Browser Track", ["igv", "track", "bigwig", "bedgraph"]),
    ("Genome Tracks", "Circos/Ideogram", ["circos", "ideogram"]),
    ("Genome Tracks", "Manhattan/QQ", ["manhattan", "qqplot"]),
    ("Flow Cytometry", "Gating", ["gating"]),
    ("Raster/Spike", "Raster Plot", ["raster"]),
    ("Raster/Spike", "Spike/PSTH", ["spike", "psth"]),
    ("Table", "Supplementary Table", ["supp_table", "supplementary_table"]),
    ("Table", "Data Table", ["table", "datatable", "sheet", "tab"]),
    ("3D/Structure", "3D Surface", ["surface", "mesh", "isosurface"]),
    ("3D/Structure", "Protein/Structure", ["pdb", "protein", "structure", "molecule"]),
    ("Multi-Panel Composite", "Supplement/Extended", ["supplement", "extended_data", "ed_fig", "suppfig", "supfig"]),
    ("Multi-Panel Composite", "Figure Panel", ["panel", "figure", "fig"]),
    ("Plotting Script (Generic)", "Plot Script", ["plot", "chart", "visual", "ggplot", "matplotlib", "seaborn", "plotly", "bokeh", "altair", "vega", "geom"]),
]


def normalize(text: str) -> str:
    return re.sub(r"[^a-z0-9_\-/]", "", text.lower())


def classify(path: str) -> Tuple[str, str, List[str]]:
    p = normalize(path)
    tags = []
    # prefer explicit keywords
    for l1, kws in KEYWORD_RULES:
        for kw in kws:
            if kw in p:
                tags.append(kw)
                return l1, l2_for(l1, p), tags
    # fallback based on file extension
    if any(p.endswith(ext) for ext in [".png", ".jpg", ".jpeg", ".tif", ".tiff", ".svg", ".pdf", ".eps"]):
        return "Image Panel", "", tags
    if any(p.endswith(ext) for ext in [".py", ".r", ".rmd", ".qmd", ".ipynb", ".m", ".jl"]):
        return "Plotting Script (Generic)", "", tags
    return "Other/Uncategorized", "", tags


def l2_for(l1: str, normalized_path: str) -> str:
    for rule_l1, l2, kws in L2_RULES:
        if rule_l1 != l1:
            continue
        for kw in kws:
            if kw in normalized_path:
                return l2
    return ""


def load_repo_paper_map(path: Path) -> Dict[str, List[Dict[str, str]]]:
    rows = list(csv.DictReader(path.open())) if path.exists() else []
    mapping: Dict[str, List[Dict[str, str]]] = defaultdict(list)
    for r in rows:
        urls = [u.strip() for u in (r.get("repo_urls", "") or "").split(";") if u.strip()]
        for url in urls:
            mapping[url].append(r)
    return mapping


def main() -> None:
    files_path = Path("data/metadata/cns_repo_figure_files.csv")
    map_path = Path("data/metadata/cns_paper_repo_map.csv")
    out_path = Path("data/metadata/cns_figure_db.csv")
    summary_path = Path("data/metadata/cns_figure_type_summary.csv")

    file_rows = list(csv.DictReader(files_path.open()))
    repo_map = load_repo_paper_map(map_path)

    out_rows = []
    type_counter = Counter()

    for r in file_rows:
        repo_url = r.get("repo_url", "")
        repo_slug = r.get("repo_slug", "")
        file_kind = r.get("file_kind", "")
        file_path = r.get("file_path", "")

        l1, l2, tags = classify(file_path)
        type_counter[l1] += 1

        papers = repo_map.get(repo_url, [])
        journals = sorted({p.get("journal", "") for p in papers if p.get("journal")})
        years = sorted({p.get("year", "") for p in papers if p.get("year")})
        dois = sorted({p.get("doi", "") for p in papers if p.get("doi")})
        titles = sorted({p.get("title", "") for p in papers if p.get("title")})

        fig_id = hashlib.sha1(f"{repo_url}::{file_path}".encode("utf-8")).hexdigest()[:16]

        out_rows.append({
            "figure_id": fig_id,
            "repo_url": repo_url,
            "repo_slug": repo_slug,
            "file_kind": file_kind,
            "file_path": file_path,
            "figure_type_l1": l1,
            "figure_type_l2": l2,
            "tags": "; ".join(tags),
            "journals": "; ".join(journals),
            "years": "; ".join(years),
            "paper_dois": "; ".join(dois),
            "paper_titles": "; ".join(titles),
        })

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "figure_id",
                "repo_url",
                "repo_slug",
                "file_kind",
                "file_path",
                "figure_type_l1",
                "figure_type_l2",
                "tags",
                "journals",
                "years",
                "paper_dois",
                "paper_titles",
            ],
        )
        w.writeheader()
        w.writerows(out_rows)

    with summary_path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["figure_type_l1", "count"])
        w.writeheader()
        for k, v in type_counter.most_common():
            w.writerow({"figure_type_l1": k, "count": v})

    print(f"rows: {len(out_rows)}")


if __name__ == "__main__":
    main()
