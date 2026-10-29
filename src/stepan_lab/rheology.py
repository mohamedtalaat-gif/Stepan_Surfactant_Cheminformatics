# Created by Muhammad Talaat, Faculty of Pharmacy, Ain Shams University
# SPDX-FileCopyrightText: 2026 Muhammad Talaat
# SPDX-License-Identifier: MIT

"""Metrics for viscosity-against-salt curves (the "S-curve" or salt curve of a surfactant system).

Adding sodium chloride screens the head-group repulsion of an anionic/amphoteric micelle, which lets
spherical micelles grow into entangled rods and raises viscosity; past an optimum the network breaks
down and viscosity falls again.  The curves are summarised here by quantities a formulator reads off
them: the peak, the salt needed to reach a target, the width of the useful window.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def first_crossing(x: np.ndarray, y: np.ndarray, level: float) -> float:
    """Smallest x at which y reaches the level, by linear interpolation; NaN if it never does."""
    above = np.nonzero(y >= level)[0]
    if len(above) == 0:
        return float("nan")
    i = above[0]
    if i == 0:
        return float(x[0])
    x0, x1, y0, y1 = x[i - 1], x[i], y[i - 1], y[i]
    return float(x0 + (level - y0) * (x1 - x0) / (y1 - y0)) if y1 != y0 else float(x1)


def window(x: np.ndarray, y: np.ndarray, low: float, high: float) -> tuple[float, float]:
    """First and last x where the curve lies between two viscosities (the 'workability range')."""
    inside = np.nonzero((y >= low) & (y <= high))[0]
    if len(inside) == 0:
        return float("nan"), float("nan")
    return float(x[inside[0]]), float(x[inside[-1]])


def curve_metrics(x, y, target_cp: float = 5000.0) -> dict:
    x = np.asarray(x, float)
    y = np.asarray(y, float)
    order = np.argsort(x)
    x, y = x[order], y[order]
    i = int(np.argmax(y))
    peak = float(y[i])
    half = peak / 2
    # width of the half-height region around the peak
    left = np.nonzero(y[: i + 1] >= half)[0]
    right = np.nonzero(y[i:] >= half)[0]
    width = float(x[i + right[-1]] - x[left[0]]) if len(left) and len(right) else float("nan")
    slope = np.gradient(y, x)
    j = int(np.argmax(slope))
    return {
        "peak_cP": peak,
        "salt_at_peak_pct": float(x[i]),
        "salt_for_target_pct": first_crossing(x, y, target_cp),
        "target_cP": target_cp,
        "half_height_width_pct": width,
        "steepest_rise_cP_per_pct": float(slope[j]),
        "salt_at_steepest_rise_pct": float(x[j]),
        "area_cP_pct": float(np.trapezoid(y, x)),
        "x_max_in_data": float(x[-1]),
        "peak_at_edge": bool(i >= len(x) - 2),
    }


def metrics_table(df: pd.DataFrame, target_cp: float = 5000.0) -> pd.DataFrame:
    rows = []
    for name, g in df.groupby("series", sort=False):
        if len(g) < 5:
            continue
        rows.append({"series": name, **curve_metrics(g["x"].astype(float), g["y"].astype(float), target_cp)})
    columns = ["series", *curve_metrics([0.0, 1.0, 2.0], [0.0, 1.0, 0.5], target_cp)]
    return pd.DataFrame(rows, columns=columns)
