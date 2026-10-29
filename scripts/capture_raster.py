# Created by Muhammad Talaat, Faculty of Pharmacy, Ain Shams University
# SPDX-FileCopyrightText: 2026 Muhammad Talaat
# SPDX-License-Identifier: MIT

"""Digitise the few charts that were pasted into the slides as pictures.

The pictures are extracted at their native resolution and marks are found by
colour.  Axes are calibrated on the printed tick labels (found as text blobs) or
on the plot gridlines.  The estimated precision is about one pixel, i.e. around
0.5 % of the axis span; every value taken this way is flagged ``raster`` in
``data/charts/_index.csv``.
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

import numpy as np
import pymupdf
from PIL import Image
from scipy import ndimage as ndi

sys.path.insert(0, str(Path(__file__).resolve().parent))
from capture_charts import DECK_FILES, DECKS, FIELDS, OUT, _fmt


def native_image(deck: str, page: int, size: tuple[int, int]) -> np.ndarray:
    doc = pymupdf.open(DECKS / DECK_FILES[deck])
    for info in doc[page - 1].get_image_info(xrefs=True):
        if (info["width"], info["height"]) == size:
            pix = pymupdf.Pixmap(doc, info["xref"])
            if pix.n >= 4:
                pix = pymupdf.Pixmap(pymupdf.csRGB, pix)
            return np.array(Image.frombytes("RGB", (pix.width, pix.height), pix.samples))
    raise LookupError((deck, page, size))


def colour_mask(img: np.ndarray, rgb, tol=40) -> np.ndarray:
    return np.abs(img.astype(int) - np.array(rgb)).sum(axis=2) <= tol


def blob_centres(mask: np.ndarray, min_area=12, open_radius=2):
    """Centres of compact blobs (markers) after removing thin lines by erosion."""
    st = ndi.generate_binary_structure(2, 2)
    core = ndi.binary_erosion(mask, st, iterations=open_radius)
    lab, n = ndi.label(core)
    out = []
    for i in range(1, n + 1):
        ys, xs = np.nonzero(lab == i)
        if len(xs) >= min_area // 2:
            out.append((float(xs.mean()), float(ys.mean())))
    return sorted(out)


def disk_markers(mask: np.ndarray, radius=3, thresh=0.8):
    """Centres of filled round markers: a disk template responds strongly on a marker and weakly on a thin line."""
    r = radius
    yy, xx = np.mgrid[-r: r + 1, -r: r + 1]
    disk = (xx**2 + yy**2 <= r * r).astype(float)
    score = ndi.convolve(mask.astype(float), disk / disk.sum(), mode="constant")
    cand = score >= thresh
    lab, n = ndi.label(cand)
    out = []
    for i in range(1, n + 1):
        ys, xs = np.nonzero(lab == i)
        w = score[ys, xs]
        out.append((float((xs * w).sum() / w.sum()), float((ys * w).sum() / w.sum())))
    return sorted(out)


def label_rows(img: np.ndarray, x0: int, x1: int, dark=150, min_h=5):
    """Vertical centres of text lines (tick labels) in a band of columns."""
    band = img[:, x0:x1].min(axis=2) < dark
    rows = band.any(axis=1)
    centres, start = [], None
    for y, v in enumerate(list(rows) + [False]):
        if v and start is None:
            start = y
        if not v and start is not None:
            if y - start >= min_h:
                centres.append((start + y - 1) / 2)
            start = None
    return centres


def label_cols(img: np.ndarray, y0: int, y1: int, dark=150, gap=6):
    band = img[y0:y1, :].min(axis=2) < dark
    cols = band.any(axis=0)
    groups, start, last = [], None, None
    for x, v in enumerate(cols):
        if v:
            if start is None:
                start = x
            last = x
        elif start is not None and x - last > gap:
            groups.append((start + last) / 2)
            start = None
    if start is not None:
        groups.append((start + last) / 2)
    return groups


def fit(pix, vals):
    a, b = np.polyfit(pix, vals, 1)
    return lambda p: a * np.asarray(p, float) + b


def write(chart_id, meta, rows):
    with open(OUT / f"{chart_id}.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, FIELDS)
        w.writeheader()
        for r in rows:
            w.writerow(dict(chart_id=chart_id, y_source="raster", y_geometry="", flag="raster", **r))
    return meta


def row(series, x, y):
    return dict(series=series, x=_fmt(x), y=_fmt(y))


def s1_p20_viscosity():
    img = native_image("S1", 20, (509, 252))
    ys = label_rows(img, 30, 72)
    ys = [y for y in ys if y < 232]  # drop the rotated axis title (outside the band) and the x labels
    yv = fit(sorted(ys, reverse=True)[:8], [0, 500, 1000, 1500, 2000, 2500, 3000, 3500])
    xs = label_cols(img, 232, 252)
    xs = [x for x in xs if x > 60][:7]
    xv = fit(xs, [0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6])
    rows = []
    for name, rgb in (("With NINOL CAA (chassis 36% SLES, 10% CAPB, 1% NINOL CAA)", (245, 51, 106)),
                      ("With PEG-40 hydrogenated castor oil (chassis 40% SLES, 16.7% CAPB, 1% PEG-40 HCO)", (255, 153, 51)),
                      ("With cocamide MEA + PEG-40 HCO (chassis 40% SLES, 13.3% CAPB, 1% CMEA, 1% PEG-40 HCO)", (153, 51, 102))):
        mask = colour_mask(img, rgb, 60)
        pts = disk_markers(mask, radius=2, thresh=0.8)
        found = {}
        for px, py in pts:
            found[round(float(xv(px)), 1)] = float(yv(py))
        for xp, xvv in zip(xs, [0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6]):
            if xvv in found:
                rows.append(row(name, xvv, found[xvv]))
                continue
            win = np.nonzero(mask[:, int(xp) - 4: int(xp) + 5].sum(axis=1) >= 2)[0]
            win = win[win < 225]
            if len(win) >= 3 and not (name.startswith("With NINOL") and xvv == 0.6):
                rows.append(row(name, xvv, float(yv(float(np.median(win))))))
    meta = dict(chart_id="s1_p20_ninol_visc", deck="S1", page=20, title="Viscosity building with NINOL CAA against cocamide MEA / PEG-40 hydrogenated castor oil",
                kind="line", x_label="NaCl added (%)", y_label="Viscosity, Brookfield LV2 60 rpm (cP)", unit="cP",
                note="Picture on the slide; values read from marker centres. Target viscosity band 1,000 to 2,500 cP drawn on the slide.",
                rows=len(rows), resolution=f"{abs(yv(0)-yv(1)):.3g}", method="raster marker centroids")
    return write("s1_p20_ninol_visc", meta, rows)


def s1_p20_foam():
    img = native_image("S1", 20, (466, 342))
    left = label_rows(img, 25, 62)
    left = sorted([y for y in left if y < 335], reverse=True)[:10]
    yl = fit(left, [0, 100, 200, 300, 400, 500, 600, 700, 800, 900])
    right = label_rows(img, 405, 440)
    right = sorted([y for y in right if y < 335], reverse=True)[:7]
    yr = fit(right, [270, 275, 280, 285, 290, 295, 300])
    rows = []
    bars = {"PEG-40 HCO chassis": (255, 153, 51), "NINOL CAA chassis": (245, 51, 106), "CMEA + PEG-40 HCO chassis": (153, 51, 102)}
    centres = {}
    for name, rgb in bars.items():
        m = colour_mask(img, rgb, 40)
        cols = np.nonzero(m[: , :].sum(axis=0) > 60)[0]
        cx = int(np.median(cols))
        col = m[:, cx - 6: cx + 7].any(axis=1)
        top = int(np.nonzero(col)[0].min())
        centres[name] = cx
        rows.append(row("Foam volume (mL)", name, float(yl(top))))
    teal = colour_mask(img, (0, 184, 180), 70)
    for name, cx in centres.items():
        ys = np.nonzero(teal[:, cx - 2: cx + 3].any(axis=1))[0]
        rows.append(row("Half life (s)", name, float(yr(float(np.median(ys))))))
    meta = dict(chart_id="s1_p20_ninol_foam", deck="S1", page=20, title="Foaming power with NINOL CAA against cocamide MEA / PEG-40 hydrogenated castor oil",
                kind="bar+line", x_label="Chassis", y_label="Foam volume (mL); half life (s)", unit="mixed",
                note="Picture on the slide; bar tops and line vertices read from pixels. Right axis spans only 270 to 300 s.",
                rows=len(rows), resolution=f"{abs(yl(0)-yl(1)):.3g}", method="raster pixel positions")
    return write("s1_p20_ninol_foam", meta, rows)


def s7_p23():
    """Four-point curves in a low-quality picture: marker positions were read against the printed axis.

    On the 120 dpi render of the slide the y axis runs from 0 at row 799 to 100,000 cP at row 348
    (4.51 rows per 1,000 cP); the dashed band edges at 77,000 and 7,000 cP fall on rows 452 and 768,
    which confirms the scale.  Reading error is about +/-3 rows, i.e. +/-700 cP.
    """
    zero, top = 799.0, 348.0
    to_cp = lambda row_: (zero - row_) / (zero - top) * 100000.0
    rows_px = {
        "BTAC": {2: 797, 3: 792, 4: 511, 5: 348},
        "STEPANQUAT Soleil": {2: 688, 3: 645, 4: 611, 5: 517},
        "EQ B (dipalmitoylethyl hydroxyethylammonium methosulfate)": {2: 748, 3: 709, 4: 691, 5: 501},
        "1.5% BTAC + 0.5% CETAC": {2: 799, 3: 787, 4: 777, 5: 721},
    }
    rows = [row(n, x, to_cp(r)) for n, d in rows_px.items() for x, r in d.items()]
    meta = dict(chart_id="s7_p23_viscosity_cetearyl", deck="S7", page=23, title="Viscosity of 2% active cationics against cetearyl alcohol level",
                kind="line", x_label="Cetearyl alcohol (C16/18 30/70) (%)", y_label="Viscosity, Brookfield LV2/V3 (cP)", unit="cP",
                note="Picture on the slide; markers read by eye against the printed axis (about +/-700 cP). Dashed band on the slide, about 7,000 to 77,000 cP, marks the viscosity range of benchmark conditioners and masks.",
                rows=len(rows), resolution="about 700", method="raster, read by eye against the printed axis")
    return write("s7_p23_viscosity_cetearyl", meta, rows)


def s6_p09():
    """Radar drawn as a low-resolution picture: radii measured on the three spokes of the triangle."""
    cats = ["Wet detangling", "Wet combing", "Dry combing"]
    rows = [row("3719-58-A with STEPAN-MILD L3 (difference from B)", c, v) for c, v in zip(cats, (0.71, 1.95, 1.48))]
    rows += [row("3719-58-B without STEPAN-MILD L3 (reference)", c, 0.0) for c in cats]
    meta = dict(chart_id="s6_p09_l3_sensory", deck="S6", page=9, title="Salon half-head study, STEPAN-MILD L3 in a conditioner (6 panellists, average)",
                kind="radar", x_label="Attribute", y_label="Panel difference score (0 none, 1 slight, 2 very noticeable)", unit="score",
                note="Picture on the slide; radii measured on the 0 to 2 scale printed beside the top spoke (about +/-0.1).",
                rows=len(rows), resolution="about 0.1", method="raster, measured on the printed scale")
    return write("s6_p09_l3_sensory", meta, rows)


BUILDERS = [s1_p20_viscosity, s1_p20_foam, s7_p23, s6_p09]


def main():
    metas = []
    for b in BUILDERS:
        m = b()
        metas.append(m)
        print(m["chart_id"], m["rows"], "rows, resolution", m["resolution"])
    index = OUT / "_index.csv"
    with open(index, newline="", encoding="utf-8") as fh:
        have = list(csv.DictReader(fh))
    keep = [r for r in have if r["chart_id"] not in {m["chart_id"] for m in metas}]
    fields = list(have[0].keys())
    with open(index, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fields)
        w.writeheader()
        w.writerows(keep + [{k: m.get(k, "") for k in fields} for m in metas])


if __name__ == "__main__":
    main()
