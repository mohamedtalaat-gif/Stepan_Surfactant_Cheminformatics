# Created by Muhammad Talaat, Faculty of Pharmacy, Ain Shams University
# SPDX-FileCopyrightText: 2026 Muhammad Talaat
# SPDX-License-Identifier: MIT

import marimo

__generated_with = "0.25.2"
app = marimo.App(width="medium", app_title="S2 Mastering modern hair care")


@app.cell(hide_code=True)
def _():
    import altair as alt
    import marimo as mo
    import numpy as np
    import pandas as pd

    from stepan_lab import charts, data, formulation, molecules, physchem, rheology, ui

    return alt, charts, data, formulation, mo, molecules, np, pd, physchem, rheology, ui


@app.cell(hide_code=True)
def _(mo, ui):
    mo.vstack([
        ui.nav("s2_modern_hair_care"),
        ui.header("Mastering modern hair care", "Session S2: market, hard-water claims for ALPHA-STEP PC-48, lubricity and simplicity"),
        ui.byline(),
        mo.md(
            """
            Session S2 starts with the size and direction of the hair-care market and then substantiates four shampoo claims for ALPHA-STEP PC-48 (a methyl ester
            sulfonate): hard-water tolerance, hydration, anti-static and damage. It ends with the sulfoacetate family and seven finished formulas.
            Under **Dry lab** I put numbers on each comparison that the slides only show as bars.
            """
        ),
        mo.accordion({"How the numbers are labelled": ui.legend()}),
    ])
    return


@app.cell(hide_code=True)
def _(mo):
    hardness = mo.ui.slider(0, 4000, value=3000, step=100, label="Water hardness (ppm, taken as CaCO3)", show_value=True)
    f_pick = mo.ui.dropdown({"1443 AOS concentrate": "s2_1443", "1363 body wash": "s2_1363", "1487 Shower Caresse": "s2_1487", "1501 foaming hand soap": "s2_1501",
                             "1520 powder milk foam": "s2_1520", "1488 powder shampoo": "s2_1488", "1374 powder wash": "s2_1374"}, value="1501 foaming hand soap", label="Formula")
    batch = mo.ui.slider(100, 5000, value=1000, step=50, label="Batch size (g)", show_value=True)
    dil = mo.ui.slider(1.0, 8.0, value=4.0, step=0.5, label="Total parts after dilution (concentrate = 1 part)", show_value=True)
    s_lo = mo.ui.slider(500, 6000, value=2000, step=250, label="Window starts at (cP)", show_value=True)
    s_hi = mo.ui.slider(1500, 8000, value=5000, step=250, label="Window ends at (cP)", show_value=True)
    return batch, dil, f_pick, hardness, s_hi, s_lo


@app.cell(hide_code=True)
def _(charts, data, mo, pd, ui):
    _m = data.chart("s2_p05_market")
    _v = _m[_m["series"] == "Retail value (USD million)"].set_index("x")["y"].astype(float)
    _g = _m[_m["series"] == "Current-year growth (%)"].set_index("x")["y"].astype(float)
    _t = pd.DataFrame({"category": _v.index, "retail value (USD million)": _v.values, "current-year growth (%)": _g.round(2).values})
    _t["value added in a year (USD million)"] = (_t["retail value (USD million)"] * _t["current-year growth (%)"] / 100).round(0)
    _t["rank by size"] = range(1, len(_t) + 1)
    _t["rank by value added"] = _t["value added in a year (USD million)"].rank(ascending=False).astype(int)
    market = mo.vstack([
        mo.md("### Market  " + ui.badge("reported") + " " + ui.badge("derived")),
        mo.ui.altair_chart(charts.render("s2_p05_market")),
        mo.md("Hair care is the second largest category by value. Multiplying size by the current-year growth gives the value a category adds in a year, "
              "which is a different ranking from size alone: fragrances and dermo-cosmetics climb because they grow fastest."),
        ui.table(_t, 10),
    ], gap=0.7)
    return (market,)


@app.cell(hide_code=True)
def _(data, hardness, mo, pd, physchem, ui):
    _foam = data.chart("s2_p10_foam_sensory")
    _fh = _foam[~_foam["series"].str.startswith("Sensory")].set_index(["series", "x"])["y"].astype(float)
    _pc0, _pc5 = _fh[("0 min", "ALPHA-STEP PC-48")], _fh[("After 5 min", "ALPHA-STEP PC-48")]
    _sl0, _sl5 = _fh[("0 min", "Sodium Laureth Sulfate")], _fh[("After 5 min", "Sodium Laureth Sulfate")]
    _sens = _foam[_foam["series"].str.startswith("Sensory")].pivot(index="x", columns="series", values="y").astype(float)
    _sens.columns = ["PC-48", "SLES"]
    _sens["PC-48 minus SLES"] = (_sens["PC-48"] - _sens["SLES"]).round(2)
    _sens = _sens.reset_index().rename(columns={"x": "attribute"}).sort_values("PC-48 minus SLES", ascending=False)
    _mo = data.chart("s2_p12_moisture").pivot(index="x", columns="series", values="y").astype(float).rename(index=float)
    _br = data.chart("s2_p13_breakage_drying")
    _brk = _br[_br["series"] == "Hair breakage (%)"].set_index("x")["y"].astype(float)
    _dry = _br[_br["series"].str.startswith("Water loss")].pivot(index="x", columns="series", values="y").astype(float).rename(index=float)
    _rows = [
        {"measure": "Foam height at 0 min (cm), 3,000 ppm", "PC-48": _pc0, "SLES": _sl0, "difference": f"{100 * (_pc0 / _sl0 - 1):+.0f}%"},
        {"measure": "Foam height after 5 min (cm)", "PC-48": _pc5, "SLES": _sl5, "difference": f"{100 * (_pc5 / _sl5 - 1):+.0f}%"},
        {"measure": "Foam kept after 5 min (%)", "PC-48": round(100 * _pc5 / _pc0, 1), "SLES": round(100 * _sl5 / _sl0, 1), "difference": f"{100 * (_pc5 / _pc0 - _sl5 / _sl0):+.1f} points"},
        {"measure": "Moisture loss at 28 min (g), lower is better", "PC-48": round(_mo.loc[28.0, "ALPHA-STEP PC-48"], 3), "SLES": round(_mo.loc[28.0, "Sodium Laureth Sulfate"], 3),
         "difference": f"{100 * (_mo.loc[28.0, 'ALPHA-STEP PC-48'] / _mo.loc[28.0, 'Sodium Laureth Sulfate'] - 1):+.0f}%"},
        {"measure": "Hair breakage (%), lower is better", "PC-48": round(_brk["ALPHA-STEP PC-48"], 3), "SLES": round(_brk["Sodium Laureth Sulfate"], 3),
         "difference": f"{100 * (_brk['ALPHA-STEP PC-48'] / _brk['Sodium Laureth Sulfate'] - 1):+.0f}%"},
        {"measure": "Water loss after 10 min of blow drying (%)", "PC-48": round(_dry.loc[10.0, "Water loss: ALPHA-STEP PC-48"], 1), "SLES": round(_dry.loc[10.0, "Water loss: Sodium Laureth Sulfate"], 1),
         "difference": f"{100 * (_dry.loc[10.0, 'Water loss: ALPHA-STEP PC-48'] / _dry.loc[10.0, 'Water loss: Sodium Laureth Sulfate'] - 1):+.0f}%"},
    ]
    _ca = hardness.value / 100.09  # mmol/L if the ppm are expressed as CaCO3 (assumption)
    _I = 3 * _ca / 1000.0  # CaCl2: ionic strength = 0.5 * (4c + 2*2c) = 3c
    _lam = physchem.debye_length_nm(_I) if _I > 0 else float("nan")
    claims = mo.vstack([
        mo.md("### Putting numbers on the PC-48 claims  " + ui.badge("digitised") + " " + ui.badge("derived")),
        mo.md(
            "The claim slides S2 p10, p12 and p13 each show PC-48 against sodium laureth sulfate under the same shampoo formula (10% active anionic, 5% CAPB). "
            "Reading the bars gives one comparison table. Everything in the 'difference' column is mine."
        ),
        ui.table(pd.DataFrame(_rows), 6),
        mo.md("**Sensory panel (10 panellists, scale 0 to 5; 0.5 mL of shampoo on hair tresses)**"),
        ui.table(_sens, 8),
        mo.md(
            f"PC-48 scores higher than SLES on {int((_sens['PC-48 minus SLES'] > 0).sum())} of the {len(_sens)} attributes. The largest gaps are "
            f"{_sens['attribute'].iloc[0].lower()} ({_sens['PC-48 minus SLES'].iloc[0]:.2f}) and {_sens['attribute'].iloc[1].lower()} ({_sens['PC-48 minus SLES'].iloc[1]:.2f}); "
            f"the smallest is {_sens['attribute'].iloc[-1].lower()} ({_sens['PC-48 minus SLES'].iloc[-1]:.2f}). "
            "The slide gives no scatter across the ten panellists, so I do not claim significance."
        ),
        mo.md("#### Why hard water matters  " + ui.badge("modelled")),
        hardness,
        mo.md(
            f"If the slides' ppm figures are hardness as CaCO3 (they do not say), {hardness.value:.0f} ppm is **{_ca:.1f} mmol/L** of calcium. As calcium chloride that gives an ionic "
            f"strength of {_I:.3f} mol/L and a Debye screening length of **{_lam:.2f} nm** (for comparison, 0.96 nm at 0.1 mol/L). Divalent ions screen anionic head groups "
            "and bind to them, which is why sulfate surfactants lose foam in hard water. The slide attributes PC-48's tolerance to the steric hindrance of "
            "the sulfonic group by the neighbouring ester (S2 p9); the structures below show that arrangement."
        ),
    ], gap=0.7)
    return (claims,)


@app.cell(hide_code=True)
def _(charts, data, mo, pd, rheology, s_hi, s_lo, ui):
    _rows = []
    _figs = []
    for _cid in ("s2_p14_hack_pc48", "s2_p21_primary_foamers"):
        _d = data.chart(_cid)
        for _n, _g in _d.groupby("series", sort=False):
            _x, _y = _g["x"].astype(float).to_numpy(), _g["y"].astype(float).to_numpy()
            _a, _b = rheology.window(_x, _y, float(s_lo.value), float(s_hi.value))
            _rows.append({"chart": _cid[:6], "system": _n, "peak (cP)": round(float(_y.max())), "salt at peak (%)": round(float(_x[_y.argmax()]), 2),
                          "salt in window from (%)": None if _a != _a else round(_a, 2), "to (%)": None if _b != _b else round(_b, 2)})
        _figs.append(mo.ui.altair_chart(charts.line(_d, "Salt added (%)", "Viscosity (cP)")))
    salt = mo.vstack([
        mo.md("### Thickening ALPHA-STEP PC-48  " + ui.badge("digitised") + " " + ui.badge("derived")),
        mo.md("S2 p14 gives the hack (PC-48 with CAPB at two ratios, or with AMPHOSOL DM/MB), S2 p21 compares three primary foamers with CAPB and AMPHOSOL DM. "
              "Pick a viscosity window to see the salt range in which each system sits inside it."),
        mo.hstack([s_lo, s_hi], justify="start", gap=2),
        *_figs,
        ui.table(pd.DataFrame(_rows), 14),
        mo.md("The text on S2 p21 says STEPAN-MILD LSB/MB and PC-48 build little viscosity with CAPB, and that the best secondary surfactant for PCL-BA is CAPB at 3.5:1. The curves show the same."),
    ], gap=0.7)
    return (salt,)


@app.cell(hide_code=True)
def _(batch, data, dil, f_pick, formulation, mo, ui):
    _noc = data.claims()
    formulas = mo.vstack([
        mo.md("### The seven formulas of the session"),
        mo.hstack([f_pick, batch], justify="start", gap=2),
        ui.formula_card(f_pick.value, batch.value),
        mo.md("#### Naturality of the concentrate after dilution  " + ui.badge("derived")),
        mo.md("Formula 1443 is a concentrate: 100 mL are diluted with 300 mL of tap water. The slide prints NOC 0.86 for the concentrate and 0.96 after dilution. "
              "Water counts as 1, so the diluted value is the weighted average."),
        dil,
        mo.md(f"Diluted to **{dil.value:g} parts in total** ({100 / dil.value:.0f}% concentrate) the naturality is **{formulation.dilute_naturality(0.86, 1 / dil.value):.3f}**"
              f" (printed at 1:3, that is 4 parts in total: {formulation.dilute_naturality(0.86, 0.25):.3f} against 0.96)."),
    ], gap=0.7)
    return (formulas,)


@app.cell(hide_code=True)
def _(mo, ui):
    _qs = [
        {"id": "q1", "q": "Which of these is the hardness at which the Ross-Miles foam test on S2 p10 was run?", "options": ["1,000 ppm", "3,000 ppm", "0 ppm"], "answer": "3,000 ppm",
         "why": "The foam test used 3,000 ppm hard water; the sensory panel used 1,000 ppm.", "source": "S2 p10"},
        {"id": "q2", "q": "After 5 minutes ALPHA-STEP PC-48 foam has kept about what share of its initial height?", "options": ["About 94%", "About 86%", "About 50%"], "answer": "About 94%",
         "why": "13.5 cm of 14.3 cm is 94%; sodium laureth sulfate keeps 7.35 of 8.55 cm, 86%.", "source": "S2 p10"},
        {"id": "q3", "q": "Which three claims does S2 p8 link to PC-48?", "options": ["Hair breakage, moisture retention, static reduction", "Colour fade, combability, mildness", "Smoothness, shine, volume"],
         "answer": "Hair breakage, moisture retention, static reduction", "why": "Damaged hair, moisturising and anti-static needs are matched with these three claims.", "source": "S2 p8"},
        {"id": "q4", "q": "The concentrate of formula 1443 has NOC 0.86. After a 1:3 dilution with water (NOC 1) it is closest to:", "options": ["0.96", "0.86", "1.00"], "answer": "0.96",
         "why": "0.25 x 0.86 + 0.75 x 1 = 0.965.", "source": "S2 p22"},
    ]
    answers = ui.quiz_elements(_qs)
    quiz_questions = _qs
    return answers, quiz_questions


@app.cell(hide_code=True)
def _(answers, data, mo, quiz_questions, ui):
    quiz = mo.vstack([mo.md("### Check yourself"), answers, ui.quiz_feedback(quiz_questions, answers.value)], gap=0.6)
    _c = data.chart_index()
    _c = _c[_c["deck"] == "S2"]
    data_tab = mo.vstack([mo.md("### Data behind this session"), ui.table(_c[["chart_id", "page", "title", "kind", "resolution"]], 8),
                          ui.csv_button(data.slides()[data.slides()["deck"] == "S2"], "s2_slide_ledger.csv", "Download the S2 slide ledger")], gap=0.6)
    return data_tab, quiz


@app.cell(hide_code=True)
def _(claims, data_tab, formulas, market, mo, quiz, salt, ui):
    walk = ui.slide_walkthrough("S2")
    chem = mo.vstack([
        mo.md("### The molecules of the session"),
        mo.md("Representative structures that I drew from the INCI names. The slide draws the ester group of PC-48 (S2 p9); the methyl ester and its di-sodium by-product are both shown."),
        ui.structure_gallery(["mes", "mes_di", "slsa", "sles2", "cocobetaine", "gcc_c8", "l3", "sci"], size=(380, 210)),
    ], gap=0.6)
    brief = mo.md(
        """
        ### What the session argued

        Hair care is growing and the trends point to skin-care-like claims backed by data. PC-48 is presented as a sulfate-free primary surfactant that
        wins on four measurable claims, each shown against sodium laureth sulfate under one shampoo formula. The second half widens the toolbox to sulfoacetates
        (LATHANOL LAL, STEPAN-MILD PCL-BA) and ends with seven finished formulas, including three waterless powders.

        ### What I would keep in mind

        * All claim studies compare PC-48 with SLES inside the same chassis; none compare PC-48 with another sulfate-free primary surfactant.
        * The bars of the claim studies carry no error bars, so the size of a difference is shown but not its reliability.
        * Three slides (S2 p11, p17 and p18) hold only pictures or a video placeholder; their data cannot be recovered from the deck.
        """
    )
    mo.ui.tabs({"The session": brief, "Dry lab": mo.vstack([market, claims, salt, formulas, chem], gap=1.6), "Every slide": walk, "Check yourself": quiz, "Data": data_tab})
    return


@app.cell(hide_code=True)
def _(ui):
    ui.footer()
    return


if __name__ == "__main__":
    app.run()
