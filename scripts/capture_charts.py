# Created by Muhammad Talaat, Faculty of Pharmacy, Ain Shams University
# SPDX-FileCopyrightText: 2026 Muhammad Talaat
# SPDX-License-Identifier: MIT

"""Read chart values from the vector drawings of the seminar slides.

Run from the repository root with the six decks in ``references/source_decks``:

    python scripts/capture_charts.py            # rewrite data/charts/*.csv
    python scripts/capture_charts.py --check    # compare with the committed files

Every chart is calibrated against its own axis tick labels, so a value is the
position of the drawn mark converted back to axis units.  The fit residual of
each axis is reported in ``data/charts/_index.csv``.  Where the slide prints a
value beside a mark, the printed value is kept and the geometry is stored next
to it so that the two can be compared.

Charts that were pasted as pictures are not handled here; see
``scripts/capture_raster.py``.
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pdfgeom as pg

ROOT = Path(__file__).resolve().parents[1]
DECKS = ROOT / "references" / "source_decks"
OUT = ROOT / "data" / "charts"

DECK_FILES = {
    "S1": "1._AOS_in_economical_sulfate_free_solutions_hbqpuz.pdf",
    "S2": "2GOSUL_1_nxm8rl.pdf",
    "S3": "3._Super_Easy_solution_for_Sulfate_Free_STEPANBLEND_ASF-MB_mc5wnv.pdf",
    "S4": "4._Sulfate_Free_for_Color_Care_bve5ff.pdf",
    "S6": "6._Hair_Conditioning_tehdkl.pdf",
    "S7": "7._Sustainably_Sourced_Ingredients_for_Hair_Conditionning_gd8kwq.pdf",
}

FIELDS = ["chart_id", "series", "x", "y", "y_source", "y_geometry", "flag"]


class Chart:
    """One chart: its metadata, its axes and the rows read from it."""

    def __init__(self, chart_id, deck, page, title, kind, x_label, y_label, unit, note=""):
        self.meta = dict(chart_id=chart_id, deck=deck, page=page, title=title, kind=kind,
                         x_label=x_label, y_label=y_label, unit=unit, note=note)
        self.page = pg.open_page(DECKS / DECK_FILES[deck], page)
        self.drawings = {d["index"]: d for d in pg.drawings(self.page)}
        self.cols, self.rows = pg.find_axes(self.page)
        self.out: list[dict] = []
        self.resolution: list[float] = []

    # -- axes ---------------------------------------------------------------
    def ycol(self, i):
        c = self.cols[i]
        self.resolution.append(abs(c["axis"].slope))
        return c["axis"]

    def xrow(self, i=0):
        r = self.rows[i]
        return r["axis"]

    # -- row helpers --------------------------------------------------------
    def add(self, series, x, y, y_source="geometry", y_geometry=None, flag=""):
        if self.meta["unit"] in ("cP", "g", "gf") and isinstance(y, (int, float, np.floating)) and -0.01 * 1e4 < float(y) < 0:
            y = 0.0  # drawing offset below the axis origin, not a negative measurement
        self.out.append(dict(chart_id=self.meta["chart_id"], series=series,
                             x=_fmt(x), y=_fmt(y), y_source=y_source,
                             y_geometry="" if y_geometry is None else _fmt(y_geometry), flag=flag))

    def line_vertices(self, idx, name, xax, yax, xround=None, xmax=None, xmin=None, flag_after=None, flag=""):
        poly = pg.path_polyline(self.drawings[idx], n=2)
        xs, ys = xax(poly[:, 0]), yax(poly[:, 1])
        for x, y in zip(xs, ys):
            if xround is not None:
                x = round(float(x) / xround) * xround
            if (xmax is not None and x > xmax + 1e-9) or (xmin is not None and x < xmin - 1e-9):
                continue
            f = flag
            if flag_after is not None and x > flag_after:
                f = "projection"
            self.add(name, x, y, flag=f)

    def line_smooth(self, idx, name, xax, yax, xmin=None, xmax=None, step=None, n=10):
        poly = pg.path_polyline(self.drawings[idx], n=n)
        xs, ys = xax(poly[:, 0]), yax(poly[:, 1])
        order = np.argsort(xs, kind="stable")
        xs, ys = xs[order], ys[order]
        # never extend a curve beyond the stretch that was actually drawn
        lo = max(xmin, float(xs.min())) if xmin is not None else float(xs.min())
        hi = min(xmax, float(xs.max())) if xmax is not None else float(xs.max())
        if step:
            grid = np.arange(np.ceil(lo / step - 1e-9) * step, hi + 1e-9, step)
            # collapse repeated x before interpolating
            ux, ui = np.unique(np.round(xs, 6), return_index=True)
            vals = np.interp(grid, ux, ys[ui])
            for x, y in zip(grid, vals):
                self.add(name, x, y)
        else:
            for x, y in zip(xs, ys):
                if lo - 1e-9 <= x <= hi + 1e-9:
                    self.add(name, x, y)

    def line_dashed_fill(self, idx, name, xax, yax, step, xmin=None, xmax=None):
        pts = pg.centreline_of_outline(self.drawings[idx], xax, step)
        for x, ypix in pts:
            if (xmin is not None and x < xmin - 1e-9) or (xmax is not None and x > xmax + 1e-9):
                continue
            self.add(name, x, float(yax(ypix)))

    def bars(self, idx, labels, yax, base_pix=None, series="", printed=None, flag=""):
        """Bars from the sub-rectangles of one drawing (left to right)."""
        boxes = pg.subrects(self.drawings[idx])
        assert len(boxes) == len(labels), (self.meta["chart_id"], idx, len(boxes), labels)
        for k, (b, lab) in enumerate(zip(boxes, labels)):
            top, bottom = b[1], b[3]
            geom = float(yax(top)) - (float(yax(bottom)) if base_pix is None else float(yax(base_pix)))
            if printed is not None and printed[k] is not None:
                self.add(series or lab, lab, printed[k], "printed", geom, flag)
            else:
                self.add(series or lab, lab, geom, "geometry", None, flag)

    def markers(self, idx, labels, yax, series, flag=""):
        boxes = pg.subrects(self.drawings[idx])
        assert len(boxes) == len(labels), (self.meta["chart_id"], idx, len(boxes))
        for b, lab in zip(boxes, labels):
            self.add(series, lab, float(yax((b[1] + b[3]) / 2)))


    def marker_centres(self, fill_hex, x_range=None, y_range=None, max_size=9.0):
        """Centres of small filled marker shapes of one colour, sorted by x."""
        pts = []
        for d in self.drawings.values():
            r = d["rect"]
            if d["fill_hex"] != fill_hex or d["type"] not in ("f", "fs"):
                continue
            if r.width > max_size or r.height > max_size:
                continue
            cx, cy = (r.x0 + r.x1) / 2, (r.y0 + r.y1) / 2
            if x_range and not (x_range[0] <= cx <= x_range[1]):
                continue
            if y_range and not (y_range[0] <= cy <= y_range[1]):
                continue
            pts.append((cx, cy))
        return sorted(pts)

    def radar(self, idx, categories, centre, units_per_pt, series):
        """Values on the spokes of an equiangular radar chart, clockwise from the top."""
        poly = pg.path_polyline(self.drawings[idx], n=2)
        cx, cy = centre
        verts = [tuple(p) for p in poly[: len(categories)]]
        k = len(categories)
        got = {}
        for x, y in verts:
            ang = (np.degrees(np.arctan2(x - cx, cy - y))) % 360  # 0 = up, clockwise
            j = int(round(ang / (360 / k))) % k
            got[j] = float(np.hypot(x - cx, y - cy)) * units_per_pt
        for j, cat in enumerate(categories):
            self.add(series, cat, got[j])


    def error_halves(self, bar_x_centres, tol=6.0, stroke_hex="#595959"):
        """Half-length (points) of the error bar drawn over each bar, or None."""
        out = []
        cands = [d for d in self.drawings.values()
                 if d["type"] == "s" and d["stroke_hex"] == stroke_hex
                 and len(d["items"]) == 4 and d["rect"].width < 4 and d["rect"].height > 2]
        for xc in bar_x_centres:
            hit = [d for d in cands if abs((d["rect"].x0 + d["rect"].x1) / 2 - xc) <= tol]
            out.append((hit[0]["rect"].y1 - hit[0]["rect"].y0) / 2 if hit else None)
        return out

    def bars_err(self, entries, yax, base_pix, errors=True, unit_name="value"):
        """Bars (with printed values and error bars when present).

        ``entries`` is a list of dicts with ``idx`` (drawing index), ``labels``
        (category per sub-rectangle), ``series`` and optional ``printed`` values.
        """
        for e in entries:
            boxes = pg.subrects(self.drawings[e["idx"]])
            assert len(boxes) == len(e["labels"]), (self.meta["chart_id"], e["idx"], len(boxes))
            halves = self.error_halves([(b[0] + b[2]) / 2 for b in boxes]) if errors else [None] * len(boxes)
            printed = e.get("printed") or [None] * len(boxes)
            for b, lab, pv, hv in zip(boxes, e["labels"], printed, halves):
                if abs(b[1] - base_pix) < 0.8 and b[3] > base_pix + 0.8:  # bar hangs below the zero line
                    geom = float(yax(b[3])) - float(yax(base_pix))
                else:
                    geom = float(yax(b[1])) - float(yax(base_pix))
                if pv is not None:
                    self.add(e["series"], lab, pv, "printed", geom)
                else:
                    self.add(e["series"], lab, geom)
                if hv is not None:
                    self.add(e["series"] + " (error bar half-length)", lab, hv * abs(float(yax(0) - yax(1))))

    def finish(self):
        m = dict(self.meta)
        m["rows"] = len(self.out)
        m["resolution"] = f"{min(self.resolution):.4g}" if self.resolution else ""
        m["method"] = "vector geometry calibrated on axis tick labels"
        return m, self.out


def _fmt(v):
    if isinstance(v, str):
        return v
    v = float(v) + 0.0
    if abs(v) < 5e-5:
        return "0"
    return f"{v:.4f}".rstrip("0").rstrip(".") if abs(v) < 1e5 else f"{v:.1f}"


# ---------------------------------------------------------------------------
# Chart definitions
# ---------------------------------------------------------------------------

def s3_p09():
    c = Chart("s3_p09_foam", "S3", 9, "Foaming properties, SLES/CAPB shower gel versus STEPANBLEND ASF/MB",
              "bar", "Product", "Foam volume (mL), half life (s), median bubble radius (um)", "mixed",
              "10% actives, Foam Scan analyser. Bubble radius values are printed on the slide.")
    left, right = c.ycol(0), c.ycol(1)
    cats = ["SLES/CAPB (Benchmark 2, sulfate-based shower gel)", "STEPANBLEND ASF/MB"]
    for idx, cat in ((3, cats[0]), (4, cats[1])):
        r = c.drawings[idx]["rect"]
        c.add("Foam volume (mL)", cat, float(left(r.y0)))
    for idx, cat in ((6, cats[0]), (7, cats[1])):
        r = c.drawings[idx]["rect"]
        c.add("Half life (s)", cat, float(right((r.y0 + r.y1) / 2)))
    c.add("Median bubble radius (um)", cats[0], 74, "printed")
    c.add("Median bubble radius (um)", cats[1], 95, "printed")
    return c


def s3_p10():
    c = Chart("s3_p10_salt_curves", "S3", 10, "Viscosity against added sodium chloride, STEPANBLEND ASF/MB at 5 to 14% actives",
              "line", "Salt added (% w/w)", "Viscosity (cP), LV3 V30, pH 5", "cP",
              "The red SLES/CAPB curve is partly hidden behind the legend box on the slide; its hidden stretch is read from the drawing.")
    ax, ay = c.xrow(0), c.ycol(0)
    c.line_smooth(5, "14% STEPANBLEND ASF", ax, ay, xmin=0, xmax=5, step=0.05)
    c.line_dashed_fill(6, "12% STEPANBLEND ASF", ax, ay, step=0.05, xmin=0, xmax=5)
    c.line_smooth(7, "10% STEPANBLEND ASF", ax, ay, xmin=0, xmax=5, step=0.05)
    c.line_smooth(8, "5% STEPANBLEND ASF", ax, ay, xmin=0, xmax=5, step=0.05)
    c.line_smooth(9, "SLES/CAPB 10% active", ax, ay, xmin=0, xmax=5, step=0.05)
    # typical viscosity bands drawn as dashed horizontals
    for idx, name in ((20, "Shampoo band lower edge"), (28, "Shower gel band lower edge")):
        r = c.drawings[idx]["rect"]
        c.add(name, "level", float(ay((r.y0 + r.y1) / 2)))
    return c


def s3_p19():
    c = Chart("s3_p19_combing", "S3", 19, "Dry combing force after 15 washes", "bar",
              "Shampoo", "Combing force, maximum (gf); lower is better", "gf",
              "6 tresses per prototype, 10 assessments per tress, 60 data points per prototype.")
    ay = c.ycol(0)
    names = {7: "SLES/CAPB 14% (active ratio 2:1)", 8: "STEPANBLEND ASF/MB",
             9: "Commercial sulfated shampoo", 10: "Commercial sulfate-free shampoo"}
    base = c.drawings[11]["rect"].y0
    for idx, name in names.items():
        r = c.drawings[idx]["rect"]
        c.add("Combing force (gf)", name, float(ay(r.y0)) - float(ay(base)))
    return c


def s3_p21():
    c = Chart("s3_p21_zein", "S3", 21, "Zein score of cleansing systems (1% active)", "bar",
              "Surfactant system", "Zein score, normalised to sodium lauryl sulfate = 100", "score",
              "Lower is milder. SLS is the normalisation reference.")
    ay = c.ycol(0)
    labels = ["Sodium lauryl sulfate (SLS)", "Sodium laureth sulfate (SLES)", "SLES/CAPB (2:1)", "STEPANBLEND ASF/MB"]
    boxes = pg.subrects(c.drawings[11])
    base = c.drawings[10]["rect"].y1
    for b, lab in zip(boxes, labels):
        geom = float(ay(b[1])) - float(ay(base))
        c.add("Zein score", lab, 100.0 if lab.startswith("Sodium lauryl") else geom,
              "reference" if lab.startswith("Sodium lauryl") else "geometry", geom)
    return c


def s3_p23():
    c = Chart("s3_p23_fade", "S3", 23, "Colour change after repeated washing, red-dyed bleached tresses", "bar",
              "Number of washes", "Colour change, dE (lower is better)", "dE",
              "Type 2A bleached hair, red shade, 6 tresses per treatment, 0.1 g shampoo per g of hair, 1 min shampooing; Hunter Lab UltraScan VIS.")
    ay = c.ycol(0)
    washes = ["5 washes", "10 washes", "15 washes"]
    base = c.drawings[14]["rect"].y0
    c.bars(11, washes, ay, base_pix=base, series="Commercial sulfated shampoo")
    c.bars(12, washes, ay, base_pix=base, series="Commercial sulfate-free shampoo")
    c.bars(13, washes, ay, base_pix=base, series="STEPANBLEND ASF (14% solids)")
    return c


def _launch_chart(chart_id, page, region, idx_names, last_obs_year=2024):
    c = Chart(chart_id, "S1", page, f"Share of new soap, bath and hair product launches containing the ingredient, {region}",
              "line", "Year of launch", "% of new launches containing the ingredient", "%",
              "Source of the plotted market data as printed on the slide: Mintel GNPD.")
    ax, ay = c.xrow(0), c.ycol(0)
    for idx, name in idx_names.items():
        c.line_vertices(idx, name, ax, ay, xround=1, flag_after=last_obs_year if page == 8 and name in ("SLES", "AOS") else None)
    return c


def s1_p07():
    return _launch_chart("s1_p07_launches_na", 7, "North America", {
        4: "SLES", 5: "AOS", 6: "APG", 7: "SLS", 8: "Sodium Coco-Sulfate", 9: "Glutamate", 10: "Sarcosinate", 11: "Taurate"})


def s1_p08():
    c = _launch_chart("s1_p08_launches_eu", 8, "Europe", {
        4: "SLES", 5: "APG", 6: "Sodium Coco-Sulfate", 7: "Glutamate", 8: "AOS", 9: "SLS", 10: "Sarcosinate", 11: "Taurate"})
    ax, ay = c.xrow(0), c.ycol(0)
    c.line_dashed_fill(26, "AOS projection, 2% scenario", ax, ay, step=1.0, xmin=2024, xmax=2028)
    c.line_dashed_fill(25, "AOS projection, 1% scenario", ax, ay, step=1.0, xmin=2024, xmax=2028)
    for r in c.out:
        if r["series"].startswith("AOS projection"):
            r["flag"] = "projection"
    return c


def s1_p12():
    c = Chart("s1_p12_foam_anionics", "S1", 12, "Foaming properties of anionics at 0.1% actives in deionised water",
              "bar", "Anionic surfactant", "Foam volume (mL); half life (s)", "mixed",
              "Blender method for foam volume; Foam Scan for bubble structure.")
    left, right = c.ycol(0), c.ycol(1)
    order = {2: "SLES-2", 4: "BIO-TERGE AS-40 HASB", 3: "ALPHA-STEP PC-48"}
    base = 389.6
    for idx, name in order.items():
        r = c.drawings[idx]["rect"]
        c.add("Foam volume (mL)", name, float(left(r.y0)) - float(left(base)))
    sq = pg.subrects(c.drawings[5])
    for b, name in zip(sq, ["SLES-2", "BIO-TERGE AS-40 HASB", "ALPHA-STEP PC-48"]):
        c.add("Half life (s)", name, float(right((b[1] + b[3]) / 2)))
    return c


def _salt_chart(chart_id, page, title, y_label, series, xmax, step=0.05, ycol=0, deck="S1"):
    c = Chart(chart_id, deck, page, title, "line", "Salt added (% NaCl)", y_label, "cP",
              "Curves can extend beneath photographs on the slide; those hidden stretches are read from the drawings.")
    ax, ay = c.xrow(0), c.ycol(ycol)
    for idx, name, how in series:
        if how == "dashed":
            c.line_dashed_fill(idx, name, ax, ay, step=step, xmin=0, xmax=xmax)
        else:
            c.line_smooth(idx, name, ax, ay, xmin=0, xmax=xmax, step=step)
    return c


def s1_p14():
    return _salt_chart("s1_p14_hack1_dm_mb", 14, "Sulfonate thickening hack 1: AMPHOSOL DM/MB as secondary surfactant",
                       "Viscosity (cP), LV2 V30, pH 5", [
        (4, "SLES-2:CAPB 2:1, 10% actives", "smooth"),
        (5, "BIO-TERGE AS-40 HASB:CAPB 2:1, 10% actives", "smooth"),
        (6, "BIO-TERGE AS-40 HASB:AMPHOSOL DM/MB 2:1, 9% actives", "smooth"),
        (7, "BIO-TERGE AS-40 HASB:AMPHOSOL DM/MB 2:1, 8% actives", "dashed")], xmax=10)


def s1_p18():
    return _salt_chart("s1_p18_hack2_ninol", 18, "Sulfonate thickening hack 2: NINOL CAA as viscosity builder",
                       "Viscosity (cP), LV2 V30, pH 5", [
        (4, "SLES-2:CAPB 2:1, 10% actives", "smooth"),
        (5, "BIO-TERGE AS-40 HASB:CAPB 2:1, 10% actives", "smooth"),
        (6, "BIO-TERGE AS-40 HASB:CAPB:NINOL CAA 2:1:0.25, 10.8% actives", "smooth"),
        (7, "BIO-TERGE AS-40 HASB:CAPB:NINOL CAA 2:1:0.25, 9% actives", "dashed")], xmax=10)


def s1_p32():
    return _salt_chart("s1_p32_additives", 32, "Thickening additives compared with NINOL CAA (cosmos-approved emollients)",
                       "Viscosity (cP), LV2 V30, pH 5", [
        (4, "SLES-2:CAPB 2:1, 10% actives", "smooth"),
        (5, "BIO-TERGE AS-40 HASB:CAPB 2:1, 10% actives", "smooth"),
        (6, "BIO-TERGE AS-40 HASB:CAPB:NINOL CAA 2:1:0.25, 10% actives", "smooth"),
        (7, "BIO-TERGE AS-40 HASB:CAPB:STEPAN-MILD L3-G/MB 2:1:0.25, 10% actives", "smooth"),
        (8, "BIO-TERGE AS-40 HASB:CAPB:STEPAN-MILD GCC-FL/MB 2:1:0.25, 10% actives", "smooth")], xmax=10)


def s1_p16():
    c = Chart("s1_p16_betaine_foam", "S1", 16, "Foam profiles of secondary betaines with BIO-TERGE AS-40 HASB",
              "bar", "Surfactant", "Foam volume (mL); half life (s)", "mixed", "10% surfactant actives.")
    left, right = c.ycol(0), c.ycol(1)
    base = c.drawings[4]["rect"].y0
    names = ["SLES-2", "AMPHOSOL DM/MB", "AMPHOSOL CG-UN", "AMPHOSOL CDB-HP-E"]
    r = c.drawings[2]["rect"]
    c.add("Foam volume (mL)", names[0], float(left(r.y0)) - float(left(base)))
    for b, n in zip(pg.subrects(c.drawings[3]), names[1:]):
        c.add("Foam volume (mL)", n, float(left(b[1])) - float(left(base)))
    for b, n in zip(pg.subrects(c.drawings[6]), names):
        c.add("Half life (s)", n, float(right((b[1] + b[3]) / 2)))
    return c


def s1_p16_visc():
    c = Chart("s1_p16_betaine_visc", "S1", 16, "Viscosity building with betaines at 2:1 actives with BIO-TERGE AS-40 HASB",
              "line", "Sodium chloride added (%)", "Viscosity (cP), 10% surfactant actives", "cP", "")
    ax, ay = c.xrow(0), c.ycol(2)
    for idx, name in ((15, "BIO-TERGE AS-40 HASB:CAPB"), (16, "BIO-TERGE AS-40 HASB:AMPHOSOL DM/MB"),
                      (17, "BIO-TERGE AS-40 HASB:AMPHOSOL CDB-HP-E")):
        c.line_smooth(idx, name, ax, ay, xmin=0, xmax=3, step=0.05)
    return c


def s1_p17():
    c = Chart("s1_p17_zein_betaines", "S1", 17, "Zein score of betaines, and of primary/secondary combinations", "bar",
              "System", "Zein score (SLS = 100); lower is milder", "score", "1% active; combinations at 2:1 primary to secondary actives.")
    a, b = c.ycol(0), c.ycol(1)
    base_a = c.drawings[12]["rect"].y0
    base_b = c.drawings[5]["rect"].y0
    r = c.drawings[10]["rect"]
    c.add("Single surfactants", "SLES-2", 58, "printed", float(a(r.y0)) - float(a(base_a)))
    names = ["STEPANOL WA-EXTRA-HA (SLS)", "AMPHOSOL CG-UN", "AMPHOSOL DM/MB", "AMPHOSOL CDB-HP-E"]
    vals = [100, 31, 6, 3]
    for bx, n, v in zip(pg.subrects(c.drawings[11]), names, vals):
        c.add("Single surfactants", n, v, "printed", float(a(bx[1])) - float(a(base_a)))
    r = c.drawings[3]["rect"]
    c.add("Combinations at 2:1", "SLES-2 & CAPB", 35, "printed", float(b(r.y0)) - float(b(base_b)))
    names = ["STEPANOL WA-EXTRA-HA & AMPHOSOL DM/MB", "BIO-TERGE AS-40 HASB & AMPHOSOL DM/MB", "STEPAN-MILD LSB/MB & AMPHOSOL DM/MB"]
    for bx, n, v in zip(pg.subrects(c.drawings[4]), names, [47, 37, 33]):
        c.add("Combinations at 2:1", n, v, "printed", float(b(bx[1])) - float(b(base_b)))
    return c



def s2_p05():
    c = Chart("s2_p05_market", "S2", 5, "Global retail sales of beauty and personal care by category, 2025",
              "bar+line", "Category", "Retail value (USD million); current-year growth (%)", "mixed",
              "Euromonitor 2025, as printed on the slide. Bar values are printed; growth is read from the drawing.")
    right = c.ycol(0)
    cats = ["Skin Care", "Hair Care", "Colour Cosmetics", "Fragrances", "Men's Grooming", "Bath and Shower",
            "Oral Care", "Dermo-Cosmetics", "Baby Products", "Sun Care"]
    values = [162463, 92753, 76896, 72612, 60378, 50793, 48697, 33027, 21956, 16271]
    for cat, v in zip(cats, values):
        c.add("Retail value (USD million)", cat, v, "printed")
    poly = pg.path_polyline(c.drawings[9], n=2)
    for cat, (x, y) in zip(cats, poly):
        c.add("Current-year growth (%)", cat, float(right(y)))
    return c


def s2_p10():
    c = Chart("s2_p10_foam_sensory", "S2", 10, "Foam height in 3,000 ppm hard water and sensory profile in 1,000 ppm hard water",
              "bar+radar", "Measure", "Foam height (cm); panel score (0-5)", "mixed",
              "Ross-Miles foam, 0.2% active at 25 C. Sensory: 10 panellists, 0.5 mL on hair tresses; 10% anionic, 5% CAPB.")
    ay = c.ycol(0)
    base = c.drawings[2]["rect"].y1 - 0  # lower gridline of the bar chart
    base = 387.6
    bars = {3: "0 min", 4: "After 5 min"}
    printed = {3: [14.3, 8.55], 4: [13.5, 7.35]}
    for idx, lab in bars.items():
        boxes = pg.subrects(c.drawings[idx])
        for b, name, v in zip(boxes, ["ALPHA-STEP PC-48", "Sodium Laureth Sulfate"], printed[idx]):
            c.add(lab, name, v, "printed", float(ay(b[1])) - float(ay(base)))
    # sensory radar: scale from the 0..5 labels on the top spoke
    scale = c.cols[1]["axis"]
    cy = float(scale.inverse(0))
    cats = ["Speed of foam", "Amount of foam", "Creaminess", "Foam size", "Rinseability",
            "Wet hair feel", "Overall", "Dry hair feel"]
    top = pg.path_polyline(c.drawings[8], n=2)
    cx = float(top[np.argmin(top[:, 1]), 0])
    c.radar(8, cats, (cx, cy), abs(scale.slope), "Sensory: Sodium Laureth Sulfate")
    c.radar(17, cats, (cx, cy), abs(scale.slope), "Sensory: ALPHA-STEP PC-48")
    return c


def s2_p12():
    c = Chart("s2_p12_moisture", "S2", 12, "Moisture loss of treated tresses in a 45 C oven", "line",
              "Time interval (min)", "Moisture loss (g); lower is better", "g",
              "Tresses washed in 1,000 ppm hard water, 10 cycles; 10% surfactant, 5% CAPB, 1% conditioning agent.")
    ax, ay = c.xrow(0), c.ycol(0)
    for fill, name in (("#707190", "Sodium Laureth Sulfate"), ("#e95c7b", "ALPHA-STEP PC-48")):
        for x, y in c.marker_centres(fill, y_range=(260, 400)):
            c.add(name, round(round(float(ax(x)) * 2) / 2, 1), float(ay(y)))
    return c


def s2_p13():
    c = Chart("s2_p13_breakage_drying", "S2", 13, "Hair breakage after flat ironing; water loss while blow drying",
              "bar+line", "Treatment / time (min)", "Breakage (%) or water loss (%)", "%",
              "10 wash cycles in 1,000 ppm hard water; flat iron 230 C x20 then combed x50; wet tress 15 cm from dryer, weighed every 2 min.")
    ay = c.ycol(0)
    base = 423.4
    for idx, name in ((12, "Sodium Laureth Sulfate"), (11, "ALPHA-STEP PC-48")):
        r = c.drawings[idx]["rect"]
        c.add("Hair breakage (%)", name, float(ay(r.y0)) - float(ay(base)))
    xa = pg.Axis.fit([524.2, 779.6], [0, 10])
    ya = pg.Axis.fit([386.4, 263.8], [0, 100])
    for fill, name in (("#f1667a", "ALPHA-STEP PC-48"), ("#8586a3", "Sodium Laureth Sulfate")):
        for x, y in c.marker_centres(fill, x_range=(520, 790), y_range=(250, 390)):
            c.add(f"Water loss: {name}", round(round(float(xa(x)) * 2) / 2, 1), float(ya(y)))
    return c


def s2_p14():
    return _salt_chart("s2_p14_hack_pc48", 14, "Sulfonate thickening hack with ALPHA-STEP PC-48", "Viscosity (cP), LV2 V30, pH 5", [
        (4, "SLES-2:CAPB 2:1, 10% actives", "smooth"),
        (5, "ALPHA-STEP PC-48:CAPB 2:1, 10% actives", "smooth"),
        (6, "ALPHA-STEP PC-48:CAPB 1:2, 10% actives", "smooth"),
        (7, "ALPHA-STEP PC-48:AMPHOSOL DM/MB 2:1, 11% actives", "smooth")], xmax=10, deck="S2")


def s2_p21():
    return _salt_chart("s2_p21_primary_foamers", 21, "Viscosity building of specialty primary foamers with CAPB and AMPHOSOL DM",
                       "Viscosity (cP), 10% surfactant actives", [
        (7, "SLES-2:CAPB 2:1 (reference)", "smooth"),
        (8, "ALPHA-STEP PC-48:CAPB 2:1", "dashed"),
        (9, "ALPHA-STEP PC-48:AMPHOSOL DM 2:1", "smooth"),
        (10, "STEPAN-MILD LSB/MB:CAPB 2:1", "dashed"),
        (11, "STEPAN-MILD LSB/MB:AMPHOSOL DM 2:1", "smooth"),
        (12, "STEPAN-MILD PCL-BA:AMPHOSOL DM 2:1", "smooth"),
        (13, "STEPAN-MILD PCL-BA:CAPB 3.5:1", "dashed")], xmax=3, deck="S2")


def _delta_e(chart_id, page, title, names, printed, note=""):
    c = Chart(chart_id, "S4", page, title, "bar", "Shampoo base", "Colour change dE (L*a*b*); lower is better", "dE",
              "European bleached hair wefts dyed red (Garnier Ultra Color 665 Ultra Rouge); 2 ultrasound cycles of 10 min at 30 C; "
              "3% actives; 500 mL per 3 wefts. Error bars as drawn (statistic not named on the slide). " + note)
    ay = c.ycol(0)
    rects = sorted([d for d in c.drawings.values() if d["type"] in ("f", "fs") and len(d["items"]) == 1
                    and d["items"][0][0] == "re" and 30 < d["rect"].width < 120 and d["rect"].height > 3
                    and d["fill_hex"] not in ("#ffffff", None)],
                   key=lambda d: d["rect"].x0)
    # keep only bars sharing the lowest baseline
    base = max(d["rect"].y1 for d in rects)
    rects = [d for d in rects if abs(d["rect"].y1 - base) < 1.5]
    assert len(rects) == len(names), (chart_id, len(rects), names)
    halves = c.error_halves([(d["rect"].x0 + d["rect"].x1) / 2 for d in rects])
    for d, n, v, h in zip(rects, names, printed, halves):
        geom = float(ay(d["rect"].y0)) - float(ay(base))
        c.add("dE", n, v, "printed", geom)
        if h is not None:
            c.add("dE error bar half-length", n, h * abs(float(ay(0) - ay(1))))
    return c


def s4_p09():
    return _delta_e("s4_p09_fade_primary", 9, "Colour fading, primary surfactants",
                    ["SLES (reference)", "SLES/CAPB 2:1", "STEPAN-MILD LSB", "BIO-TERGE AS-40 HASB (AOS)"], [8.71, 7.50, 6.40, 6.09])


def s4_p14():
    return _delta_e("s4_p14_fade_secondary", 14, "Colour fading, secondary surfactants",
                    ["SLES/CAPB 2:1", "CAPB", "AMPHOSOL DM", "AMPHOSOL CDB HP-E"], [7.50, 5.67, 5.80, 6.73])


def s4_p17():
    return _delta_e("s4_p17_fade_ammonyx", 17, "Colour fading, AMMONYX LO",
                    ["SLES", "SLES/CAPB 2:1", "CAPB", "AMMONYX LO"], [8.71, 7.50, 5.67, 3.61])


def s4_p20():
    return _delta_e("s4_p20_fade_prototype", 20, "Colour fading, Stepan prototype against a market leader",
                    ["Market leader", "Stepan prototype", "DI water"], [6.63, 6.12, 3.41])


def s4_p25():
    return _delta_e("s4_p25_fade_nextgen", 25, "Colour fading, next-generation systems",
                    ["SLES/CAPB 2:1", "Market leader", "Anionic-free", "Cleansing conditioner", "DI water"],
                    [7.50, 6.63, 5.45, 3.06, 3.41], "Stepan shampoo prototype: dE = 6.12 (slide footnote).")


def s4_p08():
    c = Chart("s4_p08_foam_aos", "S4", 8, "Shaker foam: BIO-TERGE AS-40 HASB against SLES", "bar+line", "Surfactant",
              "Foam volume (mL); half life (s)", "mixed", "0.4% surfactant active matter in DI water, shaker method.")
    ay = c.ycol(0)
    base = 463.6
    for idx, name in ((5, "SLES"), (6, "BIO-TERGE AS-40 HASB (AOS)")):
        c.add("Foam volume (mL)", name, float(ay(c.drawings[idx]["rect"].y0)) - float(ay(base)))
    c.add("Half life (s)", "SLES", float(ay(368.4)))
    c.add("Half life (s)", "BIO-TERGE AS-40 HASB (AOS)", float(ay(386.2)))
    return c


def s4_p21():
    c = Chart("s4_p21_foam_prototype", "S4", 21, "Shaker foam: Stepan colour-care prototype against a market leader", "bar+line",
              "Shampoo", "Foam volume (mL); half life (s)", "mixed", "Shaker method. Half-life values are printed on the slide.")
    ay = c.ycol(0)
    base = 473.2
    for idx, name in ((5, "Market leader"), (6, "Stepan prototype")):
        c.add("Foam volume (mL)", name, float(ay(c.drawings[idx]["rect"].y0)) - float(ay(base)))
    c.add("Half life (s)", "Market leader", 441, "printed", float(ay(356.4)))
    c.add("Half life (s)", "Stepan prototype", 308, "printed", float(ay(391.6)))
    return c


def s4_p12():
    c = Chart("s4_p12_betaine_visc", "S4", 12, "Secondary surfactant effect on BIO-TERGE AS-40 HASB thickening", "line",
              "Sodium chloride added (%)", "Viscosity (cP), 10% actives at 2:1, pH 5", "cP", "")
    ax, ay = c.xrow(0), c.ycol(0)
    for idx, name in ((6, "BIO-TERGE AS-40 HASB:CAPB"), (7, "BIO-TERGE AS-40 HASB:AMPHOSOL DM/MB"),
                      (8, "BIO-TERGE AS-40 HASB:AMPHOSOL CDB-HP-E")):
        c.line_smooth(idx, name, ax, ay, xmin=0, xmax=3, step=0.05)
    return c


def s7_p10():
    c = Chart("s7_p10_hair_concerns", "S7", 10, "Top 10 reported hair concerns", "bar", "Hair concern",
              "% of respondents", "%", "Source printed on the slide: Euromonitor International Beauty Survey 2021; Stepan Market Survey 2022.")
    ay = c.ycol(0)
    base = 407.4
    cats = ["Greying hair", "Dandruff-prone", "Itchy scalp", "Split ends", "Frizzy", "Easily tangled hair",
            "Temporary hair loss", "Dry or rough hair", "Hard to comb through", "Too much hair volume"]
    c.bars_err([dict(idx=3, labels=cats, series="% of respondents"),
                dict(idx=4, labels=cats, series="% of respondents identifying as Black or African descent")],
               ay, base, errors=False)
    return c


def s7_p18():
    c = Chart("s7_p18_wet_combing", "S7", 18, "Wet combing, maximum peak load (Dia-Stron)", "bar", "Treatment",
              "Maximum peak load (gmf); lower means fewer tangles", "gmf",
              "Three tresses, 10 comb-throughs each; error bars as drawn. Inset compares ester quats on 1A/1B hair (printed values).")
    ay = c.ycol(0)
    base = 422.4
    cats = ["Shampoo", "Chassis without conditioning active", "Chassis with CETAC", "Chassis with BTAC", "Chassis with STEPANQUAT Soleil"]
    c.bars_err([dict(idx=2, labels=cats, series="Type 1C"), dict(idx=3, labels=cats, series="Type 2A"),
                dict(idx=4, labels=cats, series="Type 3A")], ay, base)
    for name, v in (("EQ A (distearoylethyl dimonium chloride)", 55.1), ("EQ B (dipalmitoylethyl hydroxyethylammonium methosulfate)", 44.3),
                    ("BTAC", 10.5), ("STEPANQUAT Soleil", 10.1)):
        c.add("Inset: ester quats, type 1A/1B, wet combing", name, v, "printed")
    return c


def s7_p20():
    c = Chart("s7_p20_shine", "S7", 20, "Shine (luster) measured with the SAMBA imager", "bar", "Treatment",
              "Luster (BNT units); higher is shinier", "BNT",
              "2% active conditioning agent on Caucasian hair; six tresses, ten measurements each.")
    ay = c.ycol(0)
    base = 402.4
    c.bars_err([dict(idx=5, labels=["Untreated"], series="Luster"), dict(idx=6, labels=["STEPANQUAT Soleil"], series="Luster"),
                dict(idx=7, labels=["BTAC"], series="Luster"), dict(idx=8, labels=["CETAC"], series="Luster")], ay, base)
    return c


CHART_BUILDERS_EXTRA = []

def _by_colour_16(c, colours):
    out = {}
    for d in c.drawings.values():
        if d["fill_hex"] in colours and d["type"] == "f" and len(d["items"]) == 16 and d["rect"].width > 100:
            out[d["fill_hex"]] = d["index"]
    return out


def s7_p21():
    c = Chart("s7_p21_frizz", "S7", 21, "Frizz reduction by hair type (BOLERO imager)", "bar", "Hair type",
              "Frizz change (%); higher means more frizz control", "%", "2% active conditioning agent; six tresses, ten measurements each.")
    ay = c.ycol(0)
    base = float(ay.inverse(0))
    idx = _by_colour_16(c, ("#f1667a", "#8586a3", "#c6e2e4"))
    cats = ["3A", "3B1", "3B2", "4A"]
    c.bars_err([dict(idx=idx["#f1667a"], labels=cats, series="BTAC"), dict(idx=idx["#8586a3"], labels=cats, series="CETAC"),
                dict(idx=idx["#c6e2e4"], labels=cats, series="STEPANQUAT Soleil")], ay, base, errors=False)
    return c


def s7_p22():
    c = Chart("s7_p22_volume", "S7", 22, "Hair volume change by hair type (BOLERO imager)", "bar", "Hair type",
              "Volume change (%); positive means more volume", "%", "2% active conditioning agent; six tresses, ten measurements each.")
    ay = c.ycol(0)
    base = float(ay.inverse(0))
    idx = _by_colour_16(c, ("#f1667a", "#8586a3", "#c6e2e4"))
    cats = ["3A", "3B1", "3B2", "4A"]
    c.bars_err([dict(idx=idx["#f1667a"], labels=cats, series="BTAC"), dict(idx=idx["#8586a3"], labels=cats, series="CETAC"),
                dict(idx=idx["#c6e2e4"], labels=cats, series="STEPANQUAT Soleil")], ay, base, errors=False)
    return c


def s7_p30():
    c = Chart("s7_p30_gcc_tangles_shine", "S7", 30, "STEPAN-MILD GCC series in a guar-conditioned shampoo: dry combing and shine on 2A hair",
              "bar", "Shampoo", "Dry combing peak load (gmf); shine change (%)", "mixed",
              "1% active GCC series added to a shampoo with a cationic hydroxypropyl guar derivative.")
    comb, shine = c.cols[0]["axis"], c.cols[1]["axis"]
    base_c, base_s = 290.0, 544.1
    for idx, name in ((10, "Shampoo"), (8, "Shampoo with STEPAN-MILD GCC/MB"), (9, "Shampoo with STEPAN-MILD GCC-FL/MB")):
        c.add("Dry combing peak load (gmf)", name, float(comb(c.drawings[idx]["rect"].y0)) - float(comb(base_c)))
    for idx, name in ((4, "Shampoo with STEPAN-MILD GCC/MB"), (5, "Shampoo with STEPAN-MILD GCC-FL/MB")):
        c.add("Shine change (%)", name, float(shine(c.drawings[idx]["rect"].y0)) - float(shine(base_s)))
    return c


def s7_p31():
    c = Chart("s7_p31_gcc_frizz_volume", "S7", 31, "STEPAN-MILD GCC series: frizz and volume on 2A hair (BOLERO imager)", "bar",
              "Shampoo", "Change against control (%)", "%", "1% active GCC series; axes fitted on the gridlines (labels are not text objects).")
    fa = pg.Axis.fit([323.5, 175.4], [0, 25])
    va = pg.Axis.fit([549.6, 417.1], [-30, 30])
    for idx, name in ((4, "Shampoo with STEPAN-MILD GCC/MB"), (5, "Shampoo with STEPAN-MILD GCC-FL/MB")):
        c.add("Frizz reduction (%)", name, float(fa(c.drawings[idx]["rect"].y0)))
    zero = float(va.inverse(0))
    for idx, name in ((8, "Shampoo with STEPAN-MILD GCC/MB"), (9, "Shampoo with STEPAN-MILD GCC-FL/MB")):
        r = c.drawings[idx]["rect"]
        val = float(va(r.y0)) if r.y1 > zero + 0.5 and r.y0 < zero - 0.5 else (float(va(r.y0)) if abs(r.y1 - zero) < 1.0 else float(va(r.y1)))
        c.add("Volume change (%)", name, val)
    return c


def s6_p08():
    c = Chart("s6_p08_gcc_sensory", "S6", 8, "Preliminary sensory test: STEPANQUAT GA 90 with STEPAN-MILD GCC against BTAC", "radar",
              "Attribute", "Relative radius on the radar (0 = centre, 1 = outer ring)", "fraction",
              "Technical hairdresser, 5 panellists. The slide prints no numeric scale, so radii are reported as fractions of the outer ring.")
    cats = ["Rinsability", "Detangling on wet hair", "Wet combing", "Dry combing", "Absence of static",
            "Hair feel on dry hair", "Shine", "Manageability", "Body"]
    ring = c.drawings[1]["rect"]
    cx, cy = (ring.x0 + ring.x1) / 2, (ring.y0 + ring.y1) / 2
    # outer ring radius from the first (outermost) ring: farthest spoke end
    spokes = pg.path_polyline(c.drawings[2], n=2)
    R = float(np.max(np.hypot(spokes[:, 0] - cx, spokes[:, 1] - cy)))
    c.radar(3, cats, (cx, cy), 1.0 / R, "BTAC")
    c.radar(4, cats, (cx, cy), 1.0 / R, "STEPANQUAT GA 90 + STEPAN-MILD GCC")
    # dashed series: take vertices nearest each spoke direction
    poly = pg.path_polyline(c.drawings[5], n=2)
    k = len(cats)
    best = {}
    for x, y in poly:
        ang = (np.degrees(np.arctan2(x - cx, cy - y))) % 360
        j = int(round(ang / (360 / k))) % k
        if abs(((ang + 180 / k) % (360 / k)) - 180 / k) < 4.0:  # close to a spoke
            r = float(np.hypot(x - cx, y - cy)) / R
            best.setdefault(j, []).append(r)
    for j, cat in enumerate(cats):
        if j in best:
            c.add("BTAC + STEPAN-MILD GCC", cat, float(np.median(best[j])))
    return c



CHART_BUILDERS = [s3_p09, s3_p10, s3_p19, s3_p21, s3_p23,
                  s1_p07, s1_p08, s1_p12, s1_p14, s1_p16, s1_p16_visc, s1_p17, s1_p18, s1_p32,
                  s2_p05, s2_p10, s2_p12, s2_p13, s2_p14, s2_p21,
                  s4_p08, s4_p09, s4_p12, s4_p14, s4_p17, s4_p20, s4_p21, s4_p25, s7_p10, s7_p18, s7_p20, s7_p21, s7_p22, s7_p30, s7_p31, s6_p08]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--only", nargs="*")
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    index = []
    for build in CHART_BUILDERS:
        if args.only and build.__name__ not in args.only:
            continue
        chart = build()
        meta, rows = chart.finish()
        path = OUT / f"{meta['chart_id']}.csv"
        if args.check:
            with open(path, newline="", encoding="utf-8") as fh:
                old = list(csv.DictReader(fh))
            assert [dict(r) for r in rows] == old, f"{path.name} changed"
        else:
            with open(path, "w", newline="", encoding="utf-8") as fh:
                w = csv.DictWriter(fh, FIELDS)
                w.writeheader()
                w.writerows(rows)
        index.append(meta)
        print(f"{meta['chart_id']:28s} rows={meta['rows']:4d} resolution={meta['resolution']}")
    if not args.only and not args.check:
        with open(OUT / "_index.csv", "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, list(index[0].keys()))
            w.writeheader()
            w.writerows(index)


if __name__ == "__main__":
    main()
