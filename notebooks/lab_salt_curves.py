# Created by Muhammad Talaat, Faculty of Pharmacy, Ain Shams University
# SPDX-FileCopyrightText: 2026 Muhammad Talaat
# SPDX-License-Identifier: MIT

import marimo

__generated_with = "0.25.2"
app = marimo.App(width="medium", app_title="Lab: salt curves")


@app.cell(hide_code=True)
def _():
    import altair as alt
    import marimo as mo
    import numpy as np
    import pandas as pd

    from stepan_lab import charts, data, rheology, ui

    return alt, charts, data, mo, np, pd, rheology, ui


@app.cell(hide_code=True)
def _(mo, ui):
    mo.vstack([
        ui.nav("lab_salt_curves"),
        ui.header("Salt curves", "Lab: every viscosity-against-salt curve of the seminar in one place"),
        ui.byline(),
        mo.md(
            """
            Thirty-odd curves in six charts of four sessions describe one phenomenon: how the viscosity of an anionic/amphoteric surfactant system rises and falls as sodium chloride is added.
            I read each curve from the drawing of its slide (the parts that run under photographs or legends included). This lab puts them on one axis and summarises each by what a formulator
            reads off a salt curve: the peak, the salt needed to reach a target, and the width of the useful window. The conditions differ from chart to chart (actives level, ratio,
            spindle, pH), so the curves are comparable as shapes, not as a league table.
            """
        ),
        mo.accordion({"How the numbers are labelled": ui.legend()}),
    ])
    return


@app.cell(hide_code=True)
def _(data, mo):
    _salt_ids = ["s3_p10_salt_curves", "s1_p14_hack1_dm_mb", "s1_p16_betaine_visc", "s1_p18_hack2_ninol", "s1_p32_additives", "s2_p14_hack_pc48", "s2_p21_primary_foamers", "s4_p12_betaine_visc", "s1_p20_ninol_visc"]
    _idx = data.chart_index().set_index("chart_id")
    opts = {f"{_idx.loc[i, 'deck']} p{int(_idx.loc[i, 'page'])} · {_idx.loc[i, 'title']}": i for i in _salt_ids}
    pick = mo.ui.multiselect(opts, value=["S3 p10 · Viscosity against added sodium chloride, STEPANBLEND ASF/MB at 5 to 14% actives"], label="Charts to overlay")
    target = mo.ui.slider(250, 12000, value=4000, step=250, label="Target viscosity (cP)", show_value=True)
    hi = mo.ui.slider(500, 14000, value=9000, step=250, label="Upper edge of the window (cP)", show_value=True)
    norm = mo.ui.switch(label="Divide each curve by its own peak")
    return hi, norm, opts, pick, target


@app.cell(hide_code=True)
def _(data, hi, mo, norm, np, opts, pd, pick, rheology, target):
    _frames = []
    for _label, _cid in opts.items():
        if _cid not in pick.value:
            continue
        _d = data.chart(_cid)
        _d = _d[pd.to_numeric(_d["x"], errors="coerce").notna()].copy()
        _d["x"] = _d["x"].astype(float)
        _d["y"] = _d["y"].astype(float)
        _d["source"] = _label.split(" · ")[0]
        _d["curve"] = _d["source"] + " | " + _d["series"]
        _frames.append(_d)
    all_curves = pd.concat(_frames) if _frames else pd.DataFrame(columns=["curve", "x", "y", "source", "series"])
    rows = []
    for _c, _g in all_curves.groupby("curve", sort=False):
        _x, _y = _g["x"].to_numpy(), _g["y"].to_numpy()
        _m = rheology.curve_metrics(_x, _y, float(target.value))
        _a, _b = rheology.window(_x, _y, float(target.value), float(hi.value))
        rows.append({"curve": _c, "peak (cP)": round(_m["peak_cP"]), "salt at peak (%)": round(_m["salt_at_peak_pct"], 2),
                     "salt to reach target (%)": None if _m["salt_for_target_pct"] != _m["salt_for_target_pct"] else round(_m["salt_for_target_pct"], 2),
                     "window from (%)": None if _a != _a else round(_a, 2), "window to (%)": None if _b != _b else round(_b, 2),
                     "drawn up to (% salt)": round(_m["x_max_in_data"], 2), "peak at the edge of the data": _m["peak_at_edge"]})
    metrics = pd.DataFrame(rows)
    return all_curves, metrics, rows


@app.cell(hide_code=True)
def _(all_curves, charts, hi, metrics, mo, norm, pick, target, ui):
    if all_curves.empty:
        out = mo.md("Pick at least one chart.")
    else:
        _d = all_curves.copy()
        if norm.value:
            _d["y"] = _d["y"] / _d.groupby("curve")["y"].transform("max")
        _ytitle = "Viscosity / own peak" if norm.value else "Viscosity (cP)"
        import altair as _alt
        _ch = charts.line(_d.assign(series=_d["curve"]), "Salt added (% NaCl)", _ytitle, height=380, width=720)
        if not norm.value:
            _band = _alt.Chart(_d.head(1).assign(lo=target.value, hi=hi.value)).mark_rect(opacity=0.10, color="#e1a22c").encode(y="lo:Q", y2="hi:Q")
            _ch = _ch + _band
        out = mo.vstack([
            mo.hstack([pick], justify="start"),
            mo.hstack([target, hi, norm], justify="start", gap=2),
            mo.ui.altair_chart(_ch),
            ui.table(metrics, 14),
            ui.csv_button(metrics, "salt_curve_metrics.csv", "Download the metrics"),
        ], gap=0.7)
    return (out,)


@app.cell(hide_code=True)
def _(mo):
    how = mo.md(
        "### How to read a salt curve\n\n"
        "* **Salt to reach the target.** A system that reaches the viscosity you need with less salt leaves less residual salt in the product and is less sensitive to the last "
        "bit of salt added. A value of 0 means the curve is above the target before any salt is added; an empty cell means it never gets there within the drawn range.\n"
        "* **Peak and its position.** The peak of a salt curve is where the micelle network is best developed. Past it, viscosity falls. A curve whose peak sits at the edge of the "
        "drawn data may rise further: the flag in the table marks those.\n"
        "* **Window.** Between your two viscosities, the window gives the first and last salt level that stay inside. A wide window means a forgiving formula; a narrow, steep one needs "
        "tighter control of the salt dose.\n"
        "* **What the slides do not say.** Each chart uses its own spindle, speed and pH (they are in the chart note), and the systems differ in actives level. The curves cannot be ranked "
        "by peak height alone."
    )
    return (how,)


@app.cell(hide_code=True)
def _(how, mo, out):
    mo.vstack([out, how], gap=1.5)
    return


@app.cell(hide_code=True)
def _(ui):
    ui.footer()
    return


if __name__ == "__main__":
    app.run()
