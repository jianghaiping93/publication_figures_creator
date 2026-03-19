"""
Unified matplotlib style preset aligned with docs/style_config.yaml.
"""
from __future__ import annotations

import os

import matplotlib as mpl
from cycler import cycler


THEMES = {
    "classic": {
        "palette": [
            "#4C78A8",
            "#F58518",
            "#54A24B",
            "#E45756",
            "#72B7B2",
            "#B279A2",
            "#FF9DA6",
            "#9D755D",
            "#BAB0AC",
        ],
        "grid": False,
    },
    "mono_ink": {
        "palette": [
            "#111111",
            "#333333",
            "#555555",
            "#777777",
            "#999999",
            "#BBBBBB",
        ],
        "grid": True,
    },
    "ocean": {
        "palette": [
            "#003F5C",
            "#2F4B7C",
            "#665191",
            "#00A6D6",
            "#4D9DE0",
            "#A0C4FF",
        ],
        "grid": True,
    },
    "forest": {
        "palette": [
            "#1B4332",
            "#2D6A4F",
            "#40916C",
            "#52B788",
            "#74C69D",
            "#95D5B2",
        ],
        "grid": True,
    },
    "solar": {
        "palette": [
            "#7F4F24",
            "#B08968",
            "#E6B8A2",
            "#DDB892",
            "#FEFAE0",
            "#BC6C25",
        ],
        "grid": True,
    },
}


def _theme_name(theme: str | None = None) -> str:
    if theme:
        name = theme.lower().replace("-", "_")
    else:
        name = os.environ.get("PFC_STYLE_THEME", "classic").lower().replace("-", "_")
    return name if name in THEMES else "classic"


def apply_matplotlib_style(theme: str | None = None) -> None:
    name = _theme_name(theme)
    palette = THEMES[name]["palette"]
    mpl.rcParams.update({
        "figure.facecolor": "white",
        "axes.facecolor": "white",
        "axes.grid": THEMES[name]["grid"],
        "axes.linewidth": 0.8,
        "axes.labelsize": 9,
        "axes.titlesize": 12,
        "font.family": "sans-serif",
        "font.sans-serif": ["Source Sans 3", "Arial"],
        "lines.linewidth": 1.0,
        "xtick.labelsize": 9,
        "ytick.labelsize": 9,
        "legend.frameon": False,
        "axes.prop_cycle": cycler(color=palette),
    })


def categorical_palette(theme: str | None = None) -> list[str]:
    return THEMES[_theme_name(theme)]["palette"]
