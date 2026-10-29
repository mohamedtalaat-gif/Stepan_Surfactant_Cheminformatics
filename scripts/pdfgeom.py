# Created by Muhammad Talaat, Faculty of Pharmacy, Ain Shams University
# SPDX-FileCopyrightText: 2026 Muhammad Talaat
# SPDX-License-Identifier: MIT

"""Geometry helpers for reading chart data straight from vector PDF pages.

The seminar decks were exported from presentation software, so most charts are
stored as drawing instructions (rectangles, Bezier curves) rather than as
pictures.  Reading those instructions and the axis tick labels beside them
gives chart values to the resolution of the drawing, which is far finer than
reading a value by eye.  Raster charts are handled in rasterchart.py.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pymupdf


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def open_page(pdf: Path, page_number: int) -> pymupdf.Page:
    """Return a page (1-based numbering, as printed on the slides)."""
    return pymupdf.open(pdf)[page_number - 1]


def hexcolor(rgb) -> str | None:
    if rgb is None:
        return None
    return "#%02x%02x%02x" % tuple(int(round(v * 255)) for v in rgb)


def drawings(page: pymupdf.Page) -> list[dict]:
    out = []
    for i, d in enumerate(page.get_drawings()):
        d = dict(d)
        d["index"] = i
        d["fill_hex"] = hexcolor(d.get("fill"))
        d["stroke_hex"] = hexcolor(d.get("color"))
        out.append(d)
    return out


def words(page: pymupdf.Page) -> list[tuple[float, float, float, float, str]]:
    return [(w[0], w[1], w[2], w[3], w[4]) for w in page.get_text("words")]


@dataclass
class Axis:
    """Linear map between page coordinates (points) and data values."""

    slope: float
    intercept: float
    residual: float = 0.0

    @classmethod
    def fit(cls, pixels, values) -> Axis:
        pixels = np.asarray(pixels, float)
        values = np.asarray(values, float)
        a, b = np.polyfit(pixels, values, 1)
        res = float(np.max(np.abs(a * pixels + b - values))) if len(pixels) > 2 else 0.0
        return cls(float(a), float(b), res)

    def __call__(self, px):
        return self.slope * np.asarray(px, float) + self.intercept

    def inverse(self, value):
        return (np.asarray(value, float) - self.intercept) / self.slope


def numeric_words(page, x_range=None, y_range=None):
    """Words that parse as numbers, with their centre coordinates."""
    out = []
    for x0, y0, x1, y1, t in words(page):
        s = t.replace(",", ".").replace("%", "").strip()
        try:
            v = float(s)
        except ValueError:
            continue
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        if x_range and not (x_range[0] <= cx <= x_range[1]):
            continue
        if y_range and not (y_range[0] <= cy <= y_range[1]):
            continue
        out.append((v, cx, cy))
    return out


def y_axis_from_ticks(page, x_range, y_range=None) -> Axis:
    """Value-axis calibration from numeric tick labels stacked in a column."""
    ticks = numeric_words(page, x_range=x_range, y_range=y_range)
    return Axis.fit([t[2] for t in ticks], [t[0] for t in ticks])


def x_axis_from_ticks(page, y_range, x_range=None) -> Axis:
    ticks = numeric_words(page, x_range=x_range, y_range=y_range)
    return Axis.fit([t[1] for t in ticks], [t[0] for t in ticks])


def bezier(p0, p1, p2, p3, n=16):
    t = np.linspace(0, 1, n)[:, None]
    p0, p1, p2, p3 = (np.array([p.x, p.y]) for p in (p0, p1, p2, p3))
    return (1 - t) ** 3 * p0 + 3 * (1 - t) ** 2 * t * p1 + 3 * (1 - t) * t**2 * p2 + t**3 * p3


def path_polyline(drawing: dict, n=16) -> np.ndarray:
    """Sample a stroked path (lines and cubic Bezier segments) as an (N, 2) array."""
    pts: list[np.ndarray] = []
    for it in drawing["items"]:
        kind = it[0]
        if kind == "l":
            pts.extend([np.array([it[1].x, it[1].y]), np.array([it[2].x, it[2].y])])
        elif kind == "c":
            pts.extend(list(bezier(it[1], it[2], it[3], it[4], n)))
        elif kind == "re":
            r = it[1]
            pts.extend([np.array([r.x0, r.y0]), np.array([r.x1, r.y1])])
    arr = np.array(pts)
    # drop exact repeats created by joined segments
    keep = [0] + [i for i in range(1, len(arr)) if np.hypot(*(arr[i] - arr[i - 1])) > 1e-6]
    return arr[keep]


def subrects(drawing: dict) -> list[tuple[float, float, float, float]]:
    """Split a filled path made only of straight segments into its rectangles.

    Chart bars of one series are often exported as a single compound path.
    Each closed loop of line segments is reduced to its bounding box.
    """
    loops: list[list[tuple[float, float]]] = []
    cur: list[tuple[float, float]] = []
    last_end = None
    for it in drawing["items"]:
        if it[0] == "re":
            r = it[1]
            loops.append([(r.x0, r.y0), (r.x1, r.y1)])
            continue
        if it[0] != "l":
            continue
        a, b = (it[1].x, it[1].y), (it[2].x, it[2].y)
        if last_end is not None and (abs(a[0] - last_end[0]) > 1e-3 or abs(a[1] - last_end[1]) > 1e-3):
            if cur:
                loops.append(cur)
            cur = []
        if not cur:
            cur = [a]
        cur.append(b)
        last_end = b
        if abs(b[0] - cur[0][0]) < 1e-3 and abs(b[1] - cur[0][1]) < 1e-3 and len(cur) >= 4:
            loops.append(cur)
            cur, last_end = [], None
    if cur:
        loops.append(cur)
    boxes = []
    for loop in loops:
        xs = [p[0] for p in loop]
        ys = [p[1] for p in loop]
        boxes.append((min(xs), min(ys), max(xs), max(ys)))
    boxes.sort(key=lambda b: b[0])
    return boxes


def centreline_of_outline(drawing: dict, x_axis: Axis, step: float, n=8) -> list[tuple[float, float]]:
    """Centre line of a dashed stroke that was exported as filled outlines.

    Dashed lines are stored as thin polygons.  Binning the polygon vertices by x
    and averaging y recovers the original line within the stroke width.
    """
    pts = path_polyline(drawing, n=n)
    xs = x_axis(pts[:, 0])
    bins = np.round(xs / step).astype(int)
    out = []
    for b in sorted(set(bins)):
        sel = bins == b
        out.append((b * step, float(np.mean(pts[sel, 1]))))
    return out


# ---------------------------------------------------------------------------
# Automatic axis detection
# ---------------------------------------------------------------------------

def _num(text: str):
    s = text.replace(",", ".").replace("%", "").replace("−", "-").strip()
    try:
        return float(s)
    except ValueError:
        return None


def find_axes(page: pymupdf.Page, min_ticks: int = 4, tol: float = 3.0):
    """Detect value-axis columns and category-axis rows built from numeric tick labels.

    Returns ``(columns, rows)``.  Each entry is a dict with the fitted
    :class:`Axis`, the tick count, the right-edge x (columns) or centre y (rows)
    and the span covered.  Columns are sorted left to right, rows top to bottom.
    """
    items = []
    for x0, y0, x1, y1, t in words(page):
        v = _num(t)
        if v is not None:
            items.append((v, x0, x1, (x0 + x1) / 2, (y0 + y1) / 2))

    def cluster(key):
        groups: list[list[tuple]] = []
        for it in sorted(items, key=key):
            if groups and abs(key(it) - key(groups[-1][-1])) <= tol:
                groups[-1].append(it)
            else:
                groups.append([it])
        return groups

    columns = []
    for g in cluster(lambda it: it[2]):  # right edge
        if len({round(i[0], 6) for i in g}) < min_ticks:
            continue
        ax = Axis.fit([i[4] for i in g], [i[0] for i in g])
        span = max(i[0] for i in g) - min(i[0] for i in g)
        if span > 0 and ax.residual / span < 0.02:
            columns.append({"axis": ax, "n": len(g), "x": float(np.mean([i[2] for i in g])),
                            "y0": min(i[4] for i in g), "y1": max(i[4] for i in g),
                            "vmin": min(i[0] for i in g), "vmax": max(i[0] for i in g)})
    rows = []
    for g in cluster(lambda it: it[4]):  # centre y
        if len({round(i[0], 6) for i in g}) < min_ticks:
            continue
        ax = Axis.fit([i[3] for i in g], [i[0] for i in g])
        span = max(i[0] for i in g) - min(i[0] for i in g)
        if span > 0 and ax.residual / span < 0.02:
            rows.append({"axis": ax, "n": len(g), "y": float(np.mean([i[4] for i in g])),
                         "x0": min(i[3] for i in g), "x1": max(i[3] for i in g),
                         "vmin": min(i[0] for i in g), "vmax": max(i[0] for i in g)})
    columns.sort(key=lambda c: c["x"])
    rows.sort(key=lambda r: r["y"])
    return columns, rows
