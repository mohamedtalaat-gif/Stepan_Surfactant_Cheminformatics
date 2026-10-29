# Created by Muhammad Talaat, Faculty of Pharmacy, Ain Shams University
# SPDX-FileCopyrightText: 2026 Muhammad Talaat
# SPDX-License-Identifier: MIT

import marimo

__generated_with = "0.25.2"
app = marimo.App(width="medium", app_title="S1 AOS in economical sulfate-free solutions")


@app.cell(hide_code=True)
def _():
    import altair as alt
    import marimo as mo
    import numpy as np
    import pandas as pd

    from stepan_lab import charts, data, formulation, molecules, rheology, ui

    return alt, charts, data, formulation, mo, molecules, np, pd, rheology, ui


@app.cell(hide_code=True)
def _(mo, ui):
    mo.vstack([
        ui.nav("s1_aos_economics"),
        ui.header("When sulfate free is the economical solution", "Session S1: alpha olefin sulfonate, six thickening hacks and six prototypes"),
        ui.byline(),
        mo.md(
            """
            Session S1 is the longest of the seminar: 39 slides that move from regulation and market data to the chemistry of an
            alpha olefin sulfonate (AOS) system, six ways of thickening it, and six finished prototypes on one base. Every chart was rebuilt
            from the drawing inside the slide. The **Dry lab** tab recomputes what the slides state, and sometimes finds that a printed
            figure means something slightly different from how it reads.
            """
        ),
        mo.accordion({"How the numbers are labelled": ui.legend()}),
    ])
    return


@app.cell(hide_code=True)
def _(mo):
    region = mo.ui.radio(["North America (S1 p7)", "Europe (S1 p8)"], value="North America (S1 p7)", label="Market")
    growth = mo.ui.slider(0.0, 8.0, value=4.0, step=0.5, label="AOS growth, percentage points per year", show_value=True)
    s_target = mo.ui.slider(1000, 10000, value=4000, step=250, label="Window starts at (cP)", show_value=True)
    s_top = mo.ui.slider(2000, 12000, value=8000, step=250, label="Window ends at (cP)", show_value=True)
    chart_pick = mo.ui.dropdown({"Hack 1: AMPHOSOL DM/MB (S1 p14)": "s1_p14_hack1_dm_mb", "Hack 2: NINOL CAA (S1 p18)": "s1_p18_hack2_ninol",
                                 "Additives compared (S1 p32)": "s1_p32_additives", "Betaines with AOS (S1 p16)": "s1_p16_betaine_visc"},
                                value="Hack 1: AMPHOSOL DM/MB (S1 p14)", label="Salt curves")
    proto = mo.ui.dropdown({"Economy hand soap": "s1_eco_handsoap", "Prestige hand soap": "s1_prestige_handsoap", "Economy body wash": "s1_eco_bodywash",
                            "Prestige body wash": "s1_prestige_bodywash", "Economy shampoo": "s1_eco_shampoo", "Prestige shampoo": "s1_prestige_shampoo"},
                           value="Economy shampoo", label="Prototype")
    batch = mo.ui.slider(100, 5000, value=1000, step=50, label="Batch size (g)", show_value=True)
    return batch, chart_pick, growth, proto, region, s_target, s_top


@app.cell(hide_code=True)
def _(charts, data, growth, mo, np, pd, region, ui):
    _id = "s1_p07_launches_na" if region.value.startswith("North") else "s1_p08_launches_eu"
    _d = data.chart(_id)
    _d["x"] = _d["x"].astype(float)
    _obs = _d[_d["flag"] == ""]
    _aos = _obs[_obs["series"] == "AOS"].set_index("x")["y"]
    _sles = _obs[_obs["series"] == "SLES"].set_index("x")["y"]
    _last = int(_aos.index.max())
    _proj = pd.DataFrame({"series": "AOS at the chosen growth", "x": np.arange(_last, _last + 5), "y": _aos[_last] + growth.value * np.arange(0, 5), "flag": "projection"})
    _show = pd.concat([_obs[_obs["series"].isin(["AOS", "SLES", "APG", "SLS"])], _proj])
    _n = data.chart("s1_p07_launches_na")
    _n["x"] = _n["x"].astype(float)
    _na = _n[(_n["series"] == "AOS") & (_n["x"].isin([2018, 2024]))].set_index("x")["y"]
    _pts = (_na[2024] - _na[2018]) / 6
    _rel = ((_na[2024] / _na[2018]) ** (1 / 6) - 1) * 100
    _gap = (_sles - _aos).dropna()
    _cross = None
    for _a, _b in zip(_gap.index[:-1], _gap.index[1:]):
        if _gap[_a] > 0 >= _gap[_b]:
            _cross = _a + _gap[_a] / (_gap[_a] - _gap[_b])
    market = mo.vstack([
        mo.md("### Market: where AOS stands  " + ui.badge("digitised") + " " + ui.badge("derived")),
        region,
        mo.ui.altair_chart(charts.line(_show, "Year of launch", "% of new launches containing the ingredient", points=False)),
        mo.md(
            f"The slide prints **'AOS 4% annual growth'** for North America, 2018 to 2024. Reading the drawn line, AOS goes from {_na[2018]:.1f}% to "
            f"{_na[2024]:.1f}% of launches, which is **{_pts:.1f} percentage points a year**. As a relative growth rate the same change would be "
            f"{_rel:.0f}% a year. So the printed 4% matches percentage points of launch share, not relative growth. "
            + (f"On these curves AOS passes SLES at about **{_cross:.1f}**." if _cross else "In this market AOS does not pass SLES within the plotted years.")
        ),
        growth,
        mo.md(
            f"The Europe slide projects AOS to 2028 at 4%, 2% and 1% a year. With your slider set to {growth.value:g} points a year, AOS in "
            f"{_last + 4} would be {_aos[_last] + 4 * growth.value:.1f}% of launches. The dashed scenario lines on the Europe slide, which I read from "
            "the dashed strokes, are only approximate."
        ),
        mo.md("The regulatory timeline and the cost-premium table that frame this section are under **Every slide** (p5 and p6)."),
    ], gap=0.7)
    return (market,)


@app.cell(hide_code=True)
def _(alt, chart_pick, charts, data, mo, pd, rheology, s_target, s_top, ui):
    _d = data.chart(chart_pick.value)
    _d = _d[pd.to_numeric(_d["x"], errors="coerce").notna()]
    _rows = []
    for _name, _g in _d.groupby("series", sort=False):
        _x, _y = _g["x"].astype(float).to_numpy(), _g["y"].astype(float).to_numpy()
        _lo, _hi = rheology.window(_x, _y, float(s_target.value), float(s_top.value))
        _m = rheology.curve_metrics(_x, _y, float(s_target.value))
        _rows.append({"system": _name, "peak (cP)": round(_m["peak_cP"]), "salt at peak (%)": round(_m["salt_at_peak_pct"], 2),
                      "first salt in window (%)": None if _lo != _lo else round(_lo, 2), "last salt in window (%)": None if _hi != _hi else round(_hi, 2)})
    _t = pd.DataFrame(_rows)
    _band = pd.DataFrame({"lo": [s_target.value], "hi": [s_top.value]})
    _shade = alt.Chart(_band).mark_rect(opacity=0.12, color="#e1a22c").encode(y="lo:Q", y2="hi:Q")
    hacks = mo.vstack([
        mo.md("### The thickening hacks: how much salt does each system need?  " + ui.badge("digitised") + " " + ui.badge("derived")),
        mo.md(
            "Each hack is a salt curve of a sulfate-free base against the SLES-2/CAPB benchmark. Choose a curve set and a viscosity window "
            "(the 'cost-effective workability range' of the slides is a window like this one). The table lists the salt levels at which each system "
            "enters and leaves the window. A system that reaches the window with less salt leaves less residual salt in the product, which is the "
            "point of the slide."
        ),
        chart_pick,
        mo.hstack([s_target, s_top], justify="start", gap=2),
        mo.ui.altair_chart(charts.line(_d, "Salt added (% NaCl)", "Viscosity (cP), LV2 V30, pH 5", x_domain=[0, float(_d["x"].astype(float).max())]) + _shade),
        ui.table(_t, 6),
        mo.md(
            "Two cautions. The slides compare systems at different actives levels (8 to 10.8%), so a curve that sits lower may simply be a more dilute "
            "system. And the curves run under the foam photographs on S1 p14 and p18; the parts that are hidden there are read from the drawing "
            "and drawn here."
        ),
    ], gap=0.7)
    return (hacks,)


@app.cell(hide_code=True)
def _(alt, data, mo, ui):
    _r = data.additive_ratings()
    _r = _r.assign(stars=_r["stars"].astype(float))
    _order = list(dict.fromkeys(_r["attribute"]))
    _h = alt.Chart(_r).mark_rect(stroke="white").encode(
        x=alt.X("product:N", title=None, axis=alt.Axis(labelAngle=-15)), y=alt.Y("attribute:N", sort=_order, title=None),
        color=alt.Color("stars:Q", scale=alt.Scale(domain=[1, 3], range=["#dfe7ec", "#1b7f8c"]), legend=alt.Legend(title="stars")),
        tooltip=["attribute", "product", "stars", "note"])
    _t = alt.Chart(_r).mark_text(fontSize=12, color="#111").encode(x="product:N", y=alt.Y("attribute:N", sort=_order), text=alt.Text("stars:Q", format=".0f"))
    additives = mo.vstack([
        mo.md("### The additives table as a heat map  " + ui.badge("reported")),
        mo.md("The four STEPAN additives of S1 p34, rated from 1 (marginal) to 3 (excellent); a blank means not applicable. Hover for the notes printed under some ratings."),
        mo.ui.altair_chart((_h + _t).properties(width=560, height=330)),
    ], gap=0.7)
    return (additives,)


@app.cell(hide_code=True)
def _(batch, data, formulation, mo, pd, proto, ui):
    _head, _lines = data.formula(proto.value)
    _base = float(_lines[_lines["ingredient"].str.contains("Boundless")]["pct_ww"].iloc[0])
    _t = float(_head["total_actives_pct"])
    # economy prototypes add only NINOL CAA (100% active) next to the base
    _ninol = _lines[_lines["ingredient"].str.contains("NINOL")]["pct_ww"]
    _extra = float(_ninol.iloc[0]) if len(_ninol) else 0.0
    _rows = []
    for _fid, _n in (("s1_eco_handsoap", "Economy hand soap"), ("s1_eco_bodywash", "Economy body wash"), ("s1_eco_shampoo", "Economy shampoo")):
        _h, _l = data.formula(_fid)
        _b = float(_l[_l["ingredient"].str.contains("Boundless")]["pct_ww"].iloc[0])
        _e = float(_l[_l["ingredient"].str.contains("NINOL")]["pct_ww"].iloc[0])
        _rows.append({"prototype": _n, "base in formula (%)": _b, "NINOL CAA (%)": _e, "total actives (printed %)": float(_h["total_actives_pct"]),
                      "implied actives in the base (%)": round((float(_h["total_actives_pct"]) - _e) / _b * 100, 1)})
    protos = mo.vstack([
        mo.md("### The six prototypes on the Boundless base"),
        mo.md(
            "All six prototypes are built on base 1610 (BIO-TERGE AS-40 HP 53.3% with AMPHOSOL HCG-HP 41.0%), diluted and completed with additives. "
            "The base's active content is not printed. The three economy prototypes add only NINOL CAA next to the base, so their printed total actives "
            "let me solve for it  " + ui.badge("derived") + "."
        ),
        ui.table(pd.DataFrame(_rows), 3),
        mo.md("The three values agree at about 31%, so I would take the base as roughly 31% active matter (the printed total actives are rounded to 0.1, which allows about a point either way)."),
        mo.hstack([proto, batch], justify="start", gap=2),
        ui.formula_card(proto.value, batch.value),
    ], gap=0.7)
    return (protos,)


@app.cell(hide_code=True)
def _(mo, ui):
    _qs = [
        {"id": "q1", "q": "What does the 'AOS 4% annual growth' on S1 p7 correspond to?", "options": ["Relative growth of 4% a year", "About 4 percentage points of launch share a year", "A 4% price increase"],
         "answer": "About 4 percentage points of launch share a year", "why": "AOS rises from about 9% to about 33% of North American launches over six years, which is 3.9 points a year.", "source": "S1 p7"},
        {"id": "q2", "q": "Which regulations make palm-based SLES and SLS more expensive according to S1 p6?", "options": ["EUDR and the 1,4-dioxane limit", "Only the 1,4-dioxane limit", "Neither"],
         "answer": "EUDR and the 1,4-dioxane limit", "why": "Palm-based SLES/SLS carry a premium under both; coconut and petrochemical routes are marked as exempt.", "source": "S1 p6"},
        {"id": "q3", "q": "What does NINOL CAA replace on S1 p20?", "options": ["Cocamide MEA and PEG-40 hydrogenated castor oil", "CAPB", "Salt"],
         "answer": "Cocamide MEA and PEG-40 hydrogenated castor oil", "why": "The NINOL CAA chassis drops both and runs at 13% surfactant actives instead of 15%.", "source": "S1 p20"},
        {"id": "q4", "q": "Single-surfactant Zein score of AMPHOSOL DM/MB against SLES-2 on S1 p17?", "options": ["6 against 58", "58 against 6", "31 against 58"],
         "answer": "6 against 58", "why": "Lower is milder; DM/MB scores 6 and SLES-2 scores 58.", "source": "S1 p17"},
    ]
    answers = ui.quiz_elements(_qs)
    quiz_questions = _qs
    return answers, quiz_questions


@app.cell(hide_code=True)
def _(answers, data, mo, quiz_questions, ui):
    quiz = mo.vstack([mo.md("### Check yourself"), answers, ui.quiz_feedback(quiz_questions, answers.value)], gap=0.6)
    _charts = data.chart_index()
    _charts = _charts[_charts["deck"] == "S1"]
    data_tab = mo.vstack([mo.md("### Data behind this session"), ui.table(_charts[["chart_id", "page", "title", "kind", "resolution"]], 8),
                          ui.csv_button(data.slides()[data.slides()["deck"] == "S1"], "s1_slide_ledger.csv", "Download the S1 slide ledger")], gap=0.6)
    return data_tab, quiz


@app.cell(hide_code=True)
def _(additives, data_tab, hacks, market, mo, molecules, protos, quiz, ui):
    walk = ui.slide_walkthrough("S1")
    chem = mo.vstack([
        mo.md("### The molecules of the session"),
        mo.md("Representative structures that I drew from the INCI names (the slides draw none of them for this session). Green marks renewable-origin carbon where it can be counted."),
        ui.structure_gallery(["aos_ene", "aos_hydroxy", "capb", "cocobetaine", "cetylbetaine", "ninol", "gcc_c8", "l3", "cocamidemea", "sles2"], size=(380, 210)),
    ], gap=0.6)
    brief = mo.md(
        """
        ### What the session argued

        Palm- and ether-sulfate-based cleansers face a cost premium from two EU measures (EUDR and a planned 1,4-dioxane limit), while AOS has been gaining
        share of new launches. The remaining problem is formulating with it: AOS systems need salt or special thickeners, and may foam differently.
        The session answers with six 'hacks': AMPHOSOL DM/MB as secondary surfactant, NINOL CAA, other secondary surfactants, a non-ionic
        chassis, process shortcuts and additives. It closes with six prototypes built on one base.

        ### What I would keep in mind

        * Foam and viscosity numbers are for the systems and test conditions named under each chart; the slides do not give statistics for them.
        * The market charts count launches containing an ingredient (Mintel GNPD), not volume sold.
        * Prices are not given anywhere in the session; the economy of the title is argued through regulation, salt use and actives level.
        """
    )
    mo.ui.tabs({"The session": brief, "Dry lab": mo.vstack([market, hacks, additives, protos, chem], gap=1.6), "Every slide": walk, "Check yourself": quiz, "Data": data_tab})
    return


@app.cell(hide_code=True)
def _(ui):
    ui.footer()
    return


if __name__ == "__main__":
    app.run()
