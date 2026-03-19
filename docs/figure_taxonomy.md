# Figure Taxonomy

## Purpose
Define a consistent, extensible set of figure types for classifying plots across papers and repositories.

## Primary Types (L1)
1. Heatmap
2. Scatter Plot
3. Line Chart
4. Bar Chart
5. Box/Violin Plot
6. Histogram/Density
7. Area/Stacked Chart
8. Pie/Donut
9. Treemap/Sunburst
10. Waffle/Isotype
11. Radar/Polar
12. Venn/Set
13. ROC/PR Curve
14. Network/Graph
15. Pathway/Diagram
16. Image Panel (microscopy/gel/clinical imaging)
17. Spatial/Map (tissue/geo)
18. Tree/Phylogeny
19. Dimensionality Reduction (PCA/UMAP/t-SNE)
20. Genome Tracks
21. Flow Cytometry
22. Raster/Spike
23. Table
24. 3D/Structure
25. Multi-Panel Composite
26. Plotting Script (Generic)
27. Other/Uncategorized

## Common Subtypes (L2 Examples)
- Heatmap: clustered heatmap, correlation matrix
- Scatter: volcano, MA plot, dot plot
- Line: time series, trajectory
- Bar: grouped, stacked, horizontal
- Box/Violin: box plot, violin plot
- Histogram/Density: histogram, KDE overlay
- Area/Stacked: stacked area, streamgraph
- Pie/Donut: pie, donut
- Treemap/Sunburst: treemap, sunburst
- Waffle/Isotype: waffle, pictogram
- Radar/Polar: radar, polar
- Venn/Set: Venn, UpSet
- ROC/PR: ROC, precision-recall
- Network: interaction, Sankey, chord
- Pathway: signaling, workflow, schematic
- Image Panel: IF, IHC, EM, blot/gel, segmentation mask, clinical imaging (MRI/CT/US/X-ray), atlas/reference
- Spatial/Map: spatial transcriptomics, brain atlas
- Tree: dendrogram, phylogeny
- Dimensionality Reduction: PCA, UMAP, t-SNE
- Genome Tracks: IGV tracks, Manhattan/QQ
- Flow Cytometry: gating plots
- Raster/Spike: raster, PSTH
- Table: supplementary table, data table
- 3D/Structure: surface, protein structure
- Plotting Script: plot script, visualization utility

## Tagging Rules
- Assign exactly one L1 type per figure panel when possible.
- Allow multi-tag when a single panel clearly mixes types (example: scatter + marginal density).
- Multi-panel figures should be split into panel-level entries, then grouped under one figure.

## Style Notes
- Keep type names stable and short.
- Add new L2 subtypes only when they recur across multiple papers.

## References For Standard Chart Types
- ChartDataset2023 (Bajić et al., 2024) includes common chart types such as area, bar, box, bubble, donut,
  heatmap, histogram, line, pie, scatter, sunburst, table, and waffle.
