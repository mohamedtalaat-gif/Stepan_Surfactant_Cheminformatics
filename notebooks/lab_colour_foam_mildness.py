# Created by Muhammad Talaat, Faculty of Pharmacy, Ain Shams University
# SPDX-FileCopyrightText: 2026 Muhammad Talaat
# SPDX-License-Identifier: MIT

import marimo

__generated_with = "0.25.2"
app = marimo.App(width="medium", app_title="Lab: colour, foam and mildness")


@app.cell(hide_code=True)
def _():
    import altair as alt
    import marimo as mo
    import numpy as np
    import pandas as pd

    from stepan_lab import charts, colour, data, mildness, physchem, ui

    return alt, charts, colour, data, mildness, mo, np, pd, physchem, ui


@app.cell(hide_code=True)
def _(mo, ui):
    mo.vstack([
        ui.nav("lab_colour_foam_mildness"),
        ui.header("Colour, foam and mildness", "Lab: the performance measurements of the seminar, side by side and put through simple physics"),
        ui.byline(),
        mo.md(
            """
            Three kinds of performance recur across the sessions: colour loss on dyed tresses, foam volume and stability, and mildness (Zein score and a patch test). Here every measurement is in one table per
            topic, so you can see them next to each other, test the error bars, and run a foam-decay and bubble-pressure calculation on the printed half-lives and bubble radii.
            """
        ),
        mo.accordion({"How the numbers are labelled": ui.legend()}),
    ])
    return


@app.cell(hide_code=True)
def _(mo):
    system = mo.ui.dropdown(["SLES/CAPB benchmark (S3 p9)", "STEPANBLEND ASF/MB (S3 p9)", "BIO-TERGE AS-40 HASB (S1 p12)", "ALPHA-STEP PC-48 (S1 p12)", "SLES-2 (S1 p12)",
                             "Stepan prototype (S4 p21)", "Market leader (S4 p21)"], value="STEPANBLEND ASF/MB (S3 p9)", label="Foam system")
    t = mo.ui.slider(0, 1500, value=300, step=10, label="Time (s)", show_value=True)
    gamma = mo.ui.slider(20, 45, value=30, step=1, label="Surface tension (mN/m), assumed", show_value=True)
    z = mo.ui.number(0.0, 120.0, value=16.0, step=1.0, label="Zein score")
    mc = mo.ui.number(0.0, 3.0, value=0.2, step=0.05, label="M.C.I.I.")
    return gamma, mc, system, t, z


@app.cell(hide_code=True)
def _(alt, charts, data, mo, pd, ui):
    _ids = {"s3_p23_fade": "S3 p23", "s4_p09_fade_primary": "S4 p9", "s4_p14_fade_secondary": "S4 p14", "s4_p17_fade_ammonyx": "S4 p17", "s4_p20_fade_prototype": "S4 p20", "s4_p25_fade_nextgen": "S4 p25"}
    _rows = []
    for _cid, _src in _ids.items():
        _d = data.chart(_cid)
        if _cid == "s3_p23_fade":
            for _r in _d[_d["x"] == "15 washes"].itertuples():
                _rows.append({"slide": _src, "system": _r.series + " (15 washes)", "dE": float(_r.y), "half error bar": None})
            continue
        _e = _d[_d["series"] == "dE error bar half-length"].set_index("x")["y"].astype(float)
        for _r in _d[_d["series"] == "dE"].itertuples():
            _rows.append({"slide": _src, "system": _r.x, "dE": float(_r.y), "half error bar": float(_e.get(_r.x))})
    _t = pd.DataFrame(_rows).sort_values("dE")
    _bars = alt.Chart(_t).mark_bar(color="#1b7f8c").encode(y=alt.Y("system:N", sort=None, title=None, axis=alt.Axis(labelLimit=300)), x=alt.X("dE:Q", title="Colour change dE (lower is better); the black bars are the printed error bars"),
                                                          tooltip=["slide", "system", "dE", "half error bar"])
    _e = _t.dropna(subset=["half error bar"]).assign(lo=lambda d: d["dE"] - d["half error bar"], hi=lambda d: d["dE"] + d["half error bar"])
    _err = alt.Chart(_e).mark_errorbar(color="#222", thickness=2).encode(y=alt.Y("system:N", sort=None), x=alt.X("lo:Q", title=None), x2="hi:Q")
    _rep = int((_t["system"].astype(str).str.startswith("SLES/CAPB") & (_t["dE"].round(2) == 7.5)).sum())
    colour_block = mo.vstack([
        mo.md("### Every colour-loss number of the seminar  " + ui.badge("reported") + " " + ui.badge("digitised")),
        mo.md("Six slides, one test family (red-dyed bleached tresses, dE by L*a*b*). The S4 charts were run in one method, the S3 chart in another (Hunter Lab UltraScan after repeated washing), so the dE "
              f"values from the two sessions should not be set against each other. In the table, systems repeat across charts (SLES/CAPB 7.50 appears {_rep} times) because each chart was a separate run."),
        mo.ui.altair_chart((_bars + _err).properties(width=560, height=max(300, 26 * len(_t)))),
        ui.table(_t, 12),
        ui.csv_button(_t, "colour_loss_all.csv", "Download all dE values"),
    ], gap=0.7)
    return (colour_block,)


@app.cell(hide_code=True)
def _(alt, data, mo, np, pd, physchem, system, t, ui):
    _f = {"s3_p09_foam": data.chart("s3_p09_foam"), "s1_p12_foam_anionics": data.chart("s1_p12_foam_anionics"), "s4_p21_foam_prototype": data.chart("s4_p21_foam_prototype")}
    def _val(df, series, x):
        return float(df[(df["series"] == series) & (df["x"] == x)]["y"].iloc[0])
    _book = {
        "SLES/CAPB benchmark (S3 p9)": (_val(_f["s3_p09_foam"], "Foam volume (mL)", "SLES/CAPB (Benchmark 2, sulfate-based shower gel)"), _val(_f["s3_p09_foam"], "Half life (s)", "SLES/CAPB (Benchmark 2, sulfate-based shower gel)"), 74.0),
        "STEPANBLEND ASF/MB (S3 p9)": (_val(_f["s3_p09_foam"], "Foam volume (mL)", "STEPANBLEND ASF/MB"), _val(_f["s3_p09_foam"], "Half life (s)", "STEPANBLEND ASF/MB"), 95.0),
        "BIO-TERGE AS-40 HASB (S1 p12)": (_val(_f["s1_p12_foam_anionics"], "Foam volume (mL)", "BIO-TERGE AS-40 HASB"), _val(_f["s1_p12_foam_anionics"], "Half life (s)", "BIO-TERGE AS-40 HASB"), None),
        "ALPHA-STEP PC-48 (S1 p12)": (_val(_f["s1_p12_foam_anionics"], "Foam volume (mL)", "ALPHA-STEP PC-48"), _val(_f["s1_p12_foam_anionics"], "Half life (s)", "ALPHA-STEP PC-48"), None),
        "SLES-2 (S1 p12)": (_val(_f["s1_p12_foam_anionics"], "Foam volume (mL)", "SLES-2"), _val(_f["s1_p12_foam_anionics"], "Half life (s)", "SLES-2"), None),
        "Stepan prototype (S4 p21)": (_val(_f["s4_p21_foam_prototype"], "Foam volume (mL)", "Stepan prototype"), _val(_f["s4_p21_foam_prototype"], "Half life (s)", "Stepan prototype"), None),
        "Market leader (S4 p21)": (_val(_f["s4_p21_foam_prototype"], "Foam volume (mL)", "Market leader"), _val(_f["s4_p21_foam_prototype"], "Half life (s)", "Market leader"), None),
    }
    _ts = np.linspace(0, 1500, 151)
    _curves = pd.concat([pd.DataFrame({"t": _ts, "volume (mL)": _vv * physchem.foam_remaining(_ts, _hh), "system": _n}) for _n, (_vv, _hh, _rr) in _book.items()])
    _hl = _curves[_curves["system"] == system.value]
    _lines = alt.Chart(_curves).mark_line(opacity=0.35).encode(x=alt.X("t:Q", title="Time (s)"), y="volume (mL):Q", color=alt.Color("system:N", legend=alt.Legend(orient="bottom", columns=1, title=None)))
    _sel = alt.Chart(_hl).mark_line(strokeWidth=3.5).encode(x="t:Q", y="volume (mL):Q", color="system:N")
    _rule = alt.Chart(pd.DataFrame({"t": [t.value]})).mark_rule(color="#d1495b").encode(x="t:Q")
    _tab = pd.DataFrame([{"system": n, "foam volume (mL)": round(vv), "half-life (s)": round(hh), "left after the chosen time (mL)": round(vv * float(physchem.foam_remaining(t.value, hh)))} for n, (vv, hh, rr) in _book.items()])
    foam = mo.vstack([
        mo.md("### Foam: volume, half-life and an exponential-decay reading  " + ui.badge("digitised") + " " + ui.badge("modelled")),
        mo.md("The slides give each foam as a volume and a half-life. If decay is exponential, the volume left after t seconds is V 2^(-t / half-life); a foam of long half-life is simply one that decays slowly. "
              "Real foam drains first and ripens later, so the model is only a way to compare half-lives at a time of interest."),
        mo.hstack([system, t], justify="start", gap=2),
        mo.ui.altair_chart((_lines + _sel + _rule).properties(width=620, height=300)),
        ui.table(_tab, 8),
        mo.md("A caution on S3 p9: the two half-lives read identical (about 509 s) from the drawing, so on that slide the difference between the two foams is in volume and bubble size, not in stability."),
    ], gap=0.7)
    return (foam,)


@app.cell(hide_code=True)
def _(alt, gamma, mo, np, pd, physchem, ui):
    _radii = {"SLES/CAPB benchmark (S3 p9)": 74.0, "STEPANBLEND ASF/MB (S3 p9)": 95.0}  # median bubble radii printed on S3 p9
    _r = np.linspace(20, 200, 91)
    _ref = pd.concat([pd.DataFrame({"bubble radius (um)": _r, "excess pressure (kPa)": [physchem.laplace_pressure_Pa(g, x) / 1000 for x in _r], "curve": f"{g} mN/m"}) for g in (20, 45)])
    _now = pd.DataFrame({"bubble radius (um)": _r, "excess pressure (kPa)": [physchem.laplace_pressure_Pa(gamma.value, x) / 1000 for x in _r]})
    _pts = pd.DataFrame({"system": list(_radii), "bubble radius (um)": list(_radii.values())})
    _pts["excess pressure (kPa)"] = [physchem.laplace_pressure_Pa(gamma.value, x) / 1000 for x in _pts["bubble radius (um)"]]
    _chart = (alt.Chart(_ref).mark_line(opacity=0.3, strokeDash=[4, 3], color="#667").encode(x=alt.X("bubble radius (um):Q"), y=alt.Y("excess pressure (kPa):Q"), detail="curve:N", tooltip=["curve", "bubble radius (um)"])
              + alt.Chart(_now).mark_line(strokeWidth=3, color="#1b7f8c").encode(x="bubble radius (um):Q", y="excess pressure (kPa):Q")
              + alt.Chart(_pts).mark_point(size=140, filled=True, color="#d1495b").encode(x="bubble radius (um):Q", y="excess pressure (kPa):Q", tooltip=["system", "bubble radius (um)", alt.Tooltip("excess pressure (kPa):Q", format=".2f")]))
    _p1, _p2 = (physchem.laplace_pressure_Pa(gamma.value, x) for x in _radii.values())
    bubbles = mo.vstack([
        mo.md("### Pressure inside a bubble: surface tension and bubble size  " + ui.badge("modelled")),
        mo.md("The excess pressure inside a spherical bubble is 2 gamma / R (Young and Laplace). The slides print a median bubble radius only for the two foams of S3 p9; they print no surface tension, so the "
              "slider is an assumption that you can move. The dashed lines are the limits of the slider (20 and 45 mN/m), the full line is the value you chose and the points are the two S3 foams."),
        gamma,
        mo.ui.altair_chart(_chart.properties(width=620, height=280)),
        mo.md(f"At **{gamma.value} mN/m** the excess pressure is **{_p1:,.0f} Pa** inside a 74 um bubble (SLES/CAPB) and **{_p2:,.0f} Pa** inside a 95 um bubble (STEPANBLEND ASF/MB). The gap of "
              f"**{_p1 - _p2:,.0f} Pa** is the pressure that pushes gas from the small bubbles into the large ones (Ostwald ripening) when the foam ages. It is proportional to the surface tension, which the slides do not give."),
    ], gap=0.7)
    return (bubbles,)


@app.cell(hide_code=True)
def _(data, mc, mildness, mo, pd, ui, z):
    _a = data.chart("s1_p17_zein_betaines")
    _b = data.chart("s3_p21_zein")
    _rows = [{"slide": "S1 p17", "system": r.x, "Zein": float(r.y), "milder than SLS (%)": round(mildness.percent_milder(float(r.y), 100), 0)} for r in _a.itertuples()]
    _rows += [{"slide": "S3 p21", "system": r.x, "Zein": round(float(r.y), 1), "milder than SLS (%)": round(mildness.percent_milder(float(r.y), 100), 0)} for r in _b.itertuples()]
    _t = pd.DataFrame(_rows).sort_values("Zein")
    mild = mo.vstack([
        mo.md("### Mildness: the Zein score and the patch test  " + ui.badge("reported") + " " + ui.badge("digitised")),
        mo.md("The Zein test measures how much protein a 1% surfactant solution dissolves; the score is normalised to sodium lauryl sulfate = 100, so lower is milder. S1 and S3 each report "
              "their own measurement for sodium laureth sulfate (58 and about 54); the table keeps them as printed."),
        ui.table(_t, 12),
        mo.hstack([z, mo.md(f"A Zein score of {z.value:g} is {mildness.percent_milder(z.value, 100):.0f}% lower than sodium lauryl sulfate.")], justify="start", gap=2),
        mo.hstack([mc, mo.md(f"M.C.I.I. {mc.value:g}: **{mildness.mcii_class(mc.value)}**")], justify="start", gap=2),
        mo.md("M.C.I.I. classes (S3 p21): below 0.25 non irritating, 0.25 to 0.5 very slightly, 0.5 to 1 slightly, 1 to 2 moderately, 2 and above irritating."),
    ], gap=0.7)
    return (mild,)


@app.cell(hide_code=True)
def _(bubbles, colour_block, foam, mild, mo):
    mo.vstack([colour_block, foam, bubbles, mild], gap=2)
    return


@app.cell(hide_code=True)
def _(ui):
    ui.footer()
    return


if __name__ == "__main__":
    app.run()
