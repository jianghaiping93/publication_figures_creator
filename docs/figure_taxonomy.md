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
7. Network/Graph
8. Pathway/Diagram
9. Image Panel (microscopy/gel)
10. Spatial/Map (tissue/geo)
11. Tree/Phylogeny
12. Dimensionality Reduction (PCA/UMAP/t-SNE)
13. Multi-Panel Composite

## Common Subtypes (L2 Examples)
- Heatmap: clustered heatmap, correlation matrix
- Scatter: volcano, MA plot
- Line: time series, trajectory
- Bar: grouped, stacked
- Box/Violin: split by condition
- Histogram/Density: KDE overlay
- Network: interaction, co-expression
- Pathway: signaling, regulatory
- Image Panel: IF, IHC, EM
- Spatial/Map: spatial transcriptomics, brain atlas
- Tree: dendrogram, phylogeny
- Dimensionality Reduction: colored by cluster, feature overlay

## Tagging Rules
- Assign exactly one L1 type per figure panel when possible.
- Allow multi-tag when a single panel clearly mixes types (example: scatter + marginal density).
- Multi-panel figures should be split into panel-level entries, then grouped under one figure.

## Style Notes
- Keep type names stable and short.
- Add new L2 subtypes only when they recur across multiple papers.
