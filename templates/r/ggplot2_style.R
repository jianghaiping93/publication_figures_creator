# Unified ggplot2 style preset aligned with docs/style_config.yaml.

style_theme_name <- function(theme = NULL) {
  name <- theme
  if (is.null(name) || name == "") {
    name <- Sys.getenv("PFC_STYLE_THEME", "classic")
  }
  name <- gsub("-", "_", tolower(name))
  if (!name %in% c("classic", "mono_ink", "ocean", "forest", "solar")) {
    name <- "classic"
  }
  name
}

apply_ggplot_style <- function(theme = NULL) {
  name <- style_theme_name(theme)
  grid_major <- if (name == "classic") 0 else 0.2
  ggplot2::theme_minimal(base_family = "Source Sans 3", base_size = 9) +
    ggplot2::theme(
      plot.title = ggplot2::element_text(size = 12, face = "bold"),
      axis.title = ggplot2::element_text(size = 9),
      axis.text = ggplot2::element_text(size = 9),
      panel.grid.minor = ggplot2::element_blank(),
      panel.grid.major = ggplot2::element_line(size = grid_major)
    )
}

categorical_palette <- function(theme = NULL) {
  name <- style_theme_name(theme)
  if (name == "mono_ink") {
    return(c("#111111", "#333333", "#555555", "#777777", "#999999", "#BBBBBB"))
  }
  if (name == "ocean") {
    return(c("#003F5C", "#2F4B7C", "#665191", "#00A6D6", "#4D9DE0", "#A0C4FF"))
  }
  if (name == "forest") {
    return(c("#1B4332", "#2D6A4F", "#40916C", "#52B788", "#74C69D", "#95D5B2"))
  }
  if (name == "solar") {
    return(c("#7F4F24", "#B08968", "#E6B8A2", "#DDB892", "#FEFAE0", "#BC6C25"))
  }
  c(
    "#4C78A8",
    "#F58518",
    "#54A24B",
    "#E45756",
    "#72B7B2",
    "#B279A2",
    "#FF9DA6",
    "#9D755D",
    "#BAB0AC"
  )
}
