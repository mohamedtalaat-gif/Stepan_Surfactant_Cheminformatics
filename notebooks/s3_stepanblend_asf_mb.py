# Created by Muhammad Talaat, Faculty of Pharmacy, Ain Shams University
# SPDX-FileCopyrightText: 2026 Muhammad Talaat
# SPDX-License-Identifier: MIT

import marimo

__generated_with = "0.25.2"
app = marimo.App(width="medium", app_title="S3 STEPANBLEND ASF/MB")


@app.cell(hide_code=True)
def _():
    import marimo as mo
    import numpy as np
    import pandas as pd

    from stepan_lab import charts, colour, data, formulation, mildness, molecules, rheology, ui

    return charts, colour, data, formulation, mildness, mo, molecules, np, pd, rheology, ui


@app.cell(hide_code=True)
def _(mo, ui):
    mo.vstack([
        ui.nav("s3_stepanblend_asf_mb"),
        ui.header("STEPANBLEND ASF/MB", "Session S3: one ready-to-dilute sulfate-free blend, three starting formulas"),
        ui.byline(),
        mo.md(
            """
            This is the whole session as I would walk a colleague through it. The slides are replayed in order under
            **Every slide**; each chart was rebuilt from the drawing inside the slide, so every point can be read and
            downloaded. Under **Dry lab** I take the numbers apart: how much blend a target actives level needs, where the
            salt curves cross a target viscosity, whether the printed naturality can be recomputed, and what the colour,
            combing and skin-mildness figures do and do not show. Everything is marked as *reported*, *digitised*,
            *derived* or *modelled*, so a calculation is never mistaken for a measurement.
            """
        ),
        mo.accordion({"How the numbers are labelled": ui.legend()}),
    ])
    return


@app.cell(hide_code=True)
def _(mo):
    batch = mo.ui.slider(100, 5000, value=1000, step=50, label="Batch size (g)", show_value=True)
    formula_pick = mo.ui.dropdown({"Hand wash (5% actives)": "s3_handwash", "Shower gel (10% actives)": "s3_showergel",
                                   "Shampoo (14% actives)": "s3_shampoo"}, value="Hand wash (5% actives)", label="Starting formula")
    target_actives = mo.ui.slider(3.0, 16.0, value=10.0, step=0.5, label="Target surfactant actives (%)", show_value=True)
    return batch, formula_pick, target_actives


@app.cell(hide_code=True)
def _(mo):
    target_cp = mo.ui.slider(500, 12000, value=5000, step=250, label="Target viscosity (cP)", show_value=True)
    curve_pick = mo.ui.multiselect(["5% STEPANBLEND ASF", "10% STEPANBLEND ASF", "12% STEPANBLEND ASF", "14% STEPANBLEND ASF", "SLES/CAPB 10% active"],
                                   value=["5% STEPANBLEND ASF", "10% STEPANBLEND ASF", "14% STEPANBLEND ASF", "SLES/CAPB 10% active"], label="Curves")
    mcii = mo.ui.number(0.0, 3.0, value=0.2, step=0.05, label="M.C.I.I. value")
    de = mo.ui.number(0.0, 10.0, value=3.98, step=0.1, label="dE value")
    return curve_pick, de, mcii, target_cp


@app.cell(hide_code=True)
def _(data, mo, molecules, ui):
    product = data.products().set_index("product_id").loc["asfmb"]
    tiles = mo.hstack([
        mo.stat(label="Solids", value="39%"), mo.stat(label="pH (10% aqueous)", value="11.2"),
        mo.stat(label="Viscosity at 20 C", value="17,000 cps"), mo.stat(label="Density at 20 C", value="1.05"),
        mo.stat(label="Freeze point", value="< 5 C"), mo.stat(label="ISO 16128 NOC of the blend", value="0.81"),
    ], justify="start", gap=1.2)
    parts = mo.vstack([
        mo.md("### The product, as the slides present it"),
        tiles,
        mo.md(
            "STEPANBLEND ASF/MB is an RSPO mass-balance certified blend of four surfactants in water. It is cold-processable and is "
            "diluted directly in water at 14 to 39%, which gives 5 to 14% surfactant actives. The slides list what it is free from: "
            "sulfated surfactants, diethanolamine, ethylene oxide and preservatives."
        ),
        mo.md("**The four surfactants** (representative structures that I drew from the INCI names; green marks carbon of renewable origin where it can be counted)"),
        ui.structure_gallery(["aos_ene", "aos_hydroxy", "cocobetaine", "decylglucoside", "ninol"], size=(390, 215)),
        mo.md(
            "| Surfactant | Role named on S3 p06 |\n|---|---|\n"
            "| BIO-TERGE AS-40 HASB (sodium C14-16 olefin sulfonate) | flash foam; improved mildness over lauryl sulfates; more stable than alcohol sulfates over a broad pH range |\n"
            "| AMPHOSOL DM/MB (coco-betaine) | mild amphoteric; boosts foam and builds viscosity |\n"
            "| Decyl glucoside | mild, vegetable-based non-ionic with high active matter |\n"
            "| NINOL CAA (dimethyl lauramide/myristamide) | foam stabiliser, powerful viscosity builder, helps dilution |"
        ),
        mo.md("The slides give the four names but not their proportions in the blend, so I do not guess a composition. "
              "Where a composition would be needed, the Dry lab works from what the three formulas themselves imply."),
    ], gap=0.8)
    return parts, product, tiles


@app.cell(hide_code=True)
def _(batch, data, formula_pick, formulation, mo, pd, target_actives, ui):
    _fid = formula_pick.value
    _head, _lines = data.formula(_fid)
    _asf = float(_lines[_lines["ingredient"].str.contains("ASF/MB")]["pct_ww"].iloc[0])
    _printed = {"s3_handwash": 5.0, "s3_showergel": 10.0, "s3_shampoo": 14.0}[_fid]
    _frac = formulation.implied_blend_actives(_asf, _printed)
    _all = pd.DataFrame({
        "formula": ["Hand wash", "Shower gel", "Shampoo"], "blend in formula (% w/w)": [14.1, 28.2, 39.4],
        "stated actives (%)": [5, 10, 14],
        "implied actives in the blend (%)": [round(formulation.implied_blend_actives(b, a), 2) for b, a in ((14.1, 5), (28.2, 10), (39.4, 14))],
    })
    _need = target_actives.value / (_frac / 100.0)
    _grams = batch.value * _need / 100.0
    calc = mo.vstack([
        mo.md("### How much blend does a target actives level need?  " + ui.badge("derived")),
        mo.md(
            "The technical-data tile says 39% solids, but the three formulas say something sharper. Each states its blend level and its actives, "
            "so the share of the blend that is surfactant follows by division. Hand wash, shower gel and shampoo all give the same answer, "
            "about 35.5%, which is a few points below the 39% solids. The slides do not say what the remaining 3.5 points of solids are."
        ),
        ui.table(_all, 3),
        mo.hstack([target_actives, batch], justify="start", gap=2),
        mo.md(
            f"For **{target_actives.value:g}% actives** the blend level is **{_need:.1f}% w/w**, which is **{_grams:,.0f} g of blend and "
            f"{batch.value - _grams:,.0f} g of the other ingredients** in a {batch.value:,.0f} g batch. "
            "This is arithmetic on the printed percentages: it says nothing about how the viscosity or stability of the result will behave."
        ),
    ], gap=0.7)
    return (calc,)


@app.cell(hide_code=True)
def _(charts, curve_pick, data, mo, rheology, target_cp, ui):
    _df = data.chart("s3_p10_salt_curves")
    _df = _df[_df["x"].astype(str).str.match(r"^[0-9.]+$")]
    _sel = _df[_df["series"].isin(curve_pick.value)]
    _m = rheology.metrics_table(_sel, float(target_cp.value))
    _m = _m.assign(**{"salt needed for target (%)": _m["salt_for_target_pct"].round(2).astype(object).where(_m["salt_for_target_pct"].notna(), "not reached"),
                      "peak (cP)": _m["peak_cP"].round(0), "salt at peak (%)": _m["salt_at_peak_pct"].round(2)})[["series", "salt needed for target (%)", "peak (cP)", "salt at peak (%)"]]
    _fig = mo.ui.altair_chart(charts.line(_sel, "Salt added (% w/w)", "Viscosity (cP), LV3 V30, pH 5", x_domain=[0, 5])) if len(_sel) else mo.md("Pick at least one curve.")
    salt = mo.vstack([
        mo.md("### Viscosity against salt, and how much salt a target needs  " + ui.badge("digitised") + " " + ui.badge("derived")),
        mo.md(
            "The slide shows that the blend builds viscosity without added salt, whereas a sulfated SLES/CAPB system sits at almost zero "
            "until about one percent of salt is added. Pick curves and a target viscosity to see how much salt each one needs. "
            "A value of 0 means the curve is already above the target with no salt."
        ),
        mo.hstack([curve_pick, target_cp], justify="start", gap=2, align="start"),
        _fig,
        ui.table(_m, 6),
        mo.md(
            "Two things on this slide deserve a careful reading. First, the red SLES/CAPB curve runs behind the legend box; I read the hidden "
            "part from the drawing, and it keeps falling after its maximum. Second, the dashed horizontal lines mark where shampoo, shower "
            "gel and hand wash viscosities sit (about 5,050 and 1,220 cP by their position), but the viscosity method is a different one "
            "(LV3 spindle at 30 rpm, pH 5) from those quoted under the three formulas on S3 p12 to p14."
        ),
    ], gap=0.7)
    return (salt,)


@app.cell(hide_code=True)
def _(batch, data, formula_pick, formulation, mo, pd, ui):
    _head, _lines = data.formula(formula_pick.value)
    _noc = {"asfmb": 0.81}
    _rows = []
    for _fid, _printed, _name in (("s3_handwash", 0.97, "Hand wash"), ("s3_showergel", 0.95, "Shower gel"), ("s3_shampoo", 0.92, "Shampoo")):
        _l = data.formula(_fid)[1]
        _rows.append({"formula": _name, "printed NOC (S3 p07)": _printed, "recomputed": round(formulation.chassis_naturality(_l, _noc), 3)})
    formulas = mo.vstack([
        mo.md("### The three starting formulas"),
        mo.hstack([formula_pick, batch], justify="start", gap=2),
        ui.formula_card(formula_pick.value, batch.value),
        mo.md("#### Can the printed naturality be reproduced?  " + ui.badge("derived")),
        mo.md(
            "The footnote on S3 p06 defines chassis naturality as the sum, over the ingredients, of each percentage times its natural-origin "
            "content. The blend itself is 0.81 and water counts as 1. If every other ingredient is given 1 as well (my assumption: "
            "glycerin, citric acid, salt and the sorbate/benzoate pair are all treated as natural-origin in that sum), the printed "
            "indices come out to within half a hundredth. The shampoo gives 0.925 against a printed 0.92."
        ),
        ui.table(pd.DataFrame(_rows), 3),
    ], gap=0.7)
    return (formulas,)


@app.cell(hide_code=True)
def _(charts, colour, data, de, mcii, mildness, mo, pd, ui):
    _f = data.chart("s3_p23_fade").set_index(["series", "x"])["y"].astype(float)
    _c = data.chart("s3_p19_combing").set_index("x")["y"].astype(float)
    _rows = []
    for _n in ("5 washes", "10 washes", "15 washes"):
        _s, _fr, _a = (_f[("Commercial sulfated shampoo", _n)], _f[("Commercial sulfate-free shampoo", _n)], _f[("STEPANBLEND ASF (14% solids)", _n)])
        _rows.append({"washes": _n, "sulfated (dE)": round(_s, 2), "sulfate-free (dE)": round(_fr, 2), "ASF/MB (dE)": round(_a, 2),
                      "lower than sulfated (%)": round(100 * (_s - _a) / _s, 1), "lower than sulfate-free (%)": round(100 * (_fr - _a) / _fr, 1)})
    _z = data.chart("s3_p21_zein").set_index("x")["y"].astype(float)
    _zrows = [{"system": k, "Zein": round(v, 1), "lower than SLS (%)": round(mildness.percent_milder(v, 100), 0)} for k, v in _z.items()]
    tresses = mo.vstack([
        mo.md("### Colour fade, combing and mildness"),
        mo.md("**Colour change after repeated washing**  " + ui.badge("digitised") + " " + ui.badge("derived")),
        mo.ui.altair_chart(charts.bars(data.chart("s3_p23_fade"), "Number of washes", "Colour change dE (lower is better)", label_fmt=".2f")),
        mo.md(
            "The slide prints +32% and +8% at 15 washes. Recomputing from the bars I read gives 31.7% and 8.1%, so the printed figures are "
            "simply the relative reduction of dE against each commercial shampoo. After five and ten washes the margin over the "
            "sulfate-free commercial shampoo is smaller (3% and 7%), so the headline claim concerns multiple washes."
        ),
        ui.table(pd.DataFrame(_rows), 3),
        mo.md("**Reading a dE value** (the rule printed on the slide: below 1 typically imperceptible, above 3 clearly visible)"),
        mo.hstack([de, mo.md(f"dE = {de.value:g}: {colour.perceptibility(de.value)}")], justify="start", gap=2),
        mo.md("**Dry combing force after 15 washes**  " + ui.badge("digitised")),
        mo.ui.altair_chart(charts.bars(data.chart("s3_p19_combing"), "Shampoo", "Maximum combing force (gf), lower is better", label_fmt=".0f", width=620)),
        mo.md(
            f"ASF/MB needs {_c['STEPANBLEND ASF/MB']:.0f} gf against {_c['SLES/CAPB 14% (active ratio 2:1)']:.0f} gf for SLES/CAPB, a reduction of "
            f"{100 * (1 - _c['STEPANBLEND ASF/MB'] / _c['SLES/CAPB 14% (active ratio 2:1)']):.0f}% (printed: 65%). The two commercial shampoos on the right of the "
            "chart contain a conditioning polymer (and a silicone in one case); the blend alone sits between them and SLES/CAPB. Each bar rests on 60 data points "
            "(6 tresses, 10 assessments each)."
        ),
        mo.md("**Mildness: Zein score and the patch test**  " + ui.badge("digitised")),
        mo.ui.altair_chart(charts.bars(data.chart("s3_p21_zein"), "System (1% active)", "Zein score, SLS = 100", label_fmt=".0f")),
        ui.table(pd.DataFrame(_zrows), 4),
        mo.hstack([mcii, mo.md(f"**{mildness.mcii_class(mcii.value)}** on the S3 p21 scale")], justify="start", gap=2),
        mo.md(
            "The patch test behind the 'non-irritating' statement is a 48-hour occlusive test with a single application on 21 subjects, using the 27% blend "
            "(10% actives) further diluted to 5% in water. The slide credits two choices for the result: a low level of coco-betaine and decyl glucoside, and a "
            "deliberate inversion of the usual primary-to-secondary ratio of AS-40 HASB and AMPHOSOL DM/MB."
        ),
    ], gap=0.7)
    return (tresses,)


@app.cell(hide_code=True)
def _(mo, ui):
    _qs = [
        {"id": "q1", "q": "Which statement about the 14% STEPANBLEND ASF/MB curve on S3 p10 is supported?", "options": ["It needs about 1% salt to reach shampoo viscosity", "It is already above 10,000 cP with no added salt", "It peaks at 5% salt"],
         "answer": "It is already above 10,000 cP with no added salt", "why": "The curve starts near 10,600 cP at zero salt and peaks near 13,300 cP below 1% salt.", "source": "S3 p10"},
        {"id": "q2", "q": "The three starter formulas state their blend and actives levels. What share of the blend do they imply is surfactant?", "options": ["About 14%", "About 35.5%", "About 39%"],
         "answer": "About 35.5%", "why": "5 / 14.1, 10 / 28.2 and 14 / 39.4 all give 35.5%; the 39% on the technical-data tile is solids, not actives.", "source": "S3 p04, p07, p12 to p14"},
        {"id": "q3", "q": "What does the +65% on the combing slide compare?", "options": ["ASF/MB against SLES/CAPB after 15 washes", "ASF/MB against a commercial sulfate-free shampoo", "The first wash against the fifteenth"],
         "answer": "ASF/MB against SLES/CAPB after 15 washes", "why": "Combing force was measured at the end of the 15-wash cycle; the blend needs about 65% less force than SLES/CAPB.", "source": "S3 p19"},
        {"id": "q4", "q": "On S3 p23 a dE of 4 or more means:", "options": ["Imperceptible", "A clearly visible difference by the slide's own rule", "Not measurable"],
         "answer": "A clearly visible difference by the slide's own rule", "why": "The slide states that dE below 1 is typically imperceptible and above 3 clearly visible.", "source": "S3 p23"},
        {"id": "q5", "q": "A M.C.I.I. of 0.2 falls in which class of the S3 p21 scale?", "options": ["Non irritating", "Slightly irritating", "Moderately irritating"],
         "answer": "Non irritating", "why": "Below 0.25 is non irritating (NI).", "source": "S3 p21"},
    ]
    answers = ui.quiz_elements(_qs)
    quiz_questions = _qs
    return answers, quiz_questions


@app.cell(hide_code=True)
def _(answers, mo, quiz_questions, ui):
    quiz = mo.vstack([mo.md("### Check yourself"), answers, ui.quiz_feedback(quiz_questions, answers.value)], gap=0.6)
    return (quiz,)


@app.cell(hide_code=True)
def _(data, mo, ui):
    _p = data.products()
    _prod = _p[_p["source_refs"].str.contains("S3")]
    _forms = data.formula_index()
    _forms = _forms[_forms["deck"].str.contains("S3")]
    _charts = data.chart_index()
    _charts = _charts[_charts["deck"] == "S3"]
    data_tab = mo.vstack([
        mo.md("### Data behind this session"),
        mo.md("**Products**"), ui.table(_prod[["trade_name", "inci", "family", "charge", "active_pct", "source_refs"]], 6),
        mo.md("**Formulas**"), ui.table(_forms[["name", "page", "ph", "viscosity_cp", "viscosity_method"]], 6),
        mo.md("**Charts**"), ui.table(_charts[["chart_id", "page", "title", "kind", "resolution"]], 6),
        ui.csv_button(data.slides()[data.slides()["deck"] == "S3"], "s3_slide_ledger.csv", "Download the S3 slide ledger"),
    ], gap=0.6)
    return (data_tab,)


@app.cell(hide_code=True)
def _(calc, data_tab, formulas, mo, quiz, salt, tresses, ui):
    walk = ui.slide_walkthrough("S3")
    brief = mo.md(
        """
        ### What the session argued

        The session sells one idea: a single blend that replaces four separate surfactant purchases. The slides support it with four
        kinds of evidence, in this order: process (cold, no heating, no salt), foam and viscosity against a sulfated benchmark, three
        worked formulas, and claim substantiation (colour fade, dry combing, skin mildness).

        ### What I would keep in mind when using it

        * Every performance figure belongs to the formula and test it was measured on. The salt curves, the combing study and the
          colour study use different dilutions, so they should not be set against one another.
        * The bars carry no statistics on S3 apart from the number of tresses and data points. A difference of a few percent between
          the blend and the commercial sulfate-free shampoo (the 8% at 15 washes, 3% at 5 washes) is within what two tresses could differ by.
        * The calculator, the naturality recomputation and the percentage checks in the Dry lab are arithmetic on printed numbers.
        """
    )
    mo.ui.tabs({"The session": brief, "Dry lab": mo.vstack([calc, salt, formulas, tresses], gap=1.6), "Every slide": walk,
                "Check yourself": quiz, "Data": data_tab})
    return (walk, brief)


@app.cell(hide_code=True)
def _(ui):
    ui.footer()
    return


if __name__ == "__main__":
    app.run()
