#!/usr/bin/env Rscript
# Run an R plotting script with unified ggplot2 style applied.

args <- commandArgs(trailingOnly = TRUE)
if (length(args) < 1) {
  stop("usage: run_with_style.R <script.R> [args]")
}

script_path <- args[1]
script_args <- if (length(args) > 1) args[-1] else character(0)

this_file <- normalizePath(sys.frame(1)$ofile)
repo_root <- normalizePath(file.path(dirname(this_file), ".."))
style_path <- file.path(repo_root, "templates", "r", "ggplot2_style.R")

if (file.exists(style_path)) {
  source(style_path)
  if (requireNamespace("ggplot2", quietly = TRUE)) {
    ggplot2::theme_set(apply_ggplot_style(Sys.getenv("PFC_STYLE_THEME", "")))
  }
}

assign(".pfc_args", script_args, envir = .GlobalEnv)
source(script_path, chdir = TRUE)
