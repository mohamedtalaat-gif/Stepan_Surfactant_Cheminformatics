# Created by Muhammad Talaat, Faculty of Pharmacy, Ain Shams University
# SPDX-FileCopyrightText: 2026 Muhammad Talaat
# SPDX-License-Identifier: MIT

import marimo

__generated_with = "0.25.2"
app = marimo.App(width="medium", app_title="S7 Sustainably sourced ingredients for haircare")


@app.cell(hide_code=True)
def _():
    import altair as alt
    import marimo as mo
    import numpy as np
    import pandas as pd

    from stepan_lab import charts, data, formulation, molecules, ui

    return alt, charts, data, formulation, mo, molecules, np, pd, ui


@app.cell(hide_code=True)
def _(mo, ui):
    mo.vstack([
        ui.nav("s7_sustainable_conditioning"),
        ui.header("Sustainably sourced ingredients for haircare", "Session S7: STEPANQUAT Soleil, six claims on four hair types, and five formulation guidelines"),
        ui.byline(),
        mo.md(
            """
            Session S7 makes the case for one ingredient. It opens with market research on sustainability, introduces STEPANQUAT Soleil (an ester quat blended with sunflower
            oil glycerides), proves six claims on hair tresses with named instruments, and ends with formulas for a conditioner, a mask, a 2-in-1 shampoo, a beard serum and a solid bar.
            **Dry lab** lets you pick a hair type, test the renewable-carbon arithmetic behind the 0.88 score, and scale each guideline formula.
            """
        ),
        mo.accordion({"How the numbers are labelled": ui.legend()}),
    ])
    return


@app.cell(hide_code=True)
def _(mo):
    hair = mo.ui.dropdown(["3A", "3B1", "3B2", "4A"], value="3B2", label="Hair type")
    cet = mo.ui.slider(2.0, 5.0, value=3.0, step=0.1, label="Cetearyl alcohol (%)", show_value=True)
    f_pick = mo.ui.dropdown({"Conditioner (p24)": "s7_conditioner", "Hair mask (p25)": "s7_mask", "2-in-1 shampoo (p26)": "s7_2in1", "Bear to Beard serum (p27)": "s7_serum",
                             "Abracada'Bar solid conditioner (p28)": "s7_solidbar", "Claims chassis (p14)": "s7_chassis_claims", "Curl-control chassis (p17)": "s7_chassis_smooth"},
                            value="Conditioner (p24)", label="Formula")
    batch = mo.ui.slider(100, 5000, value=500, step=50, label="Batch size (g)", show_value=True)
    return batch, cet, f_pick, hair


@app.cell(hide_code=True)
def _(alt, charts, data, mo, pd, ui):
    _s = data.survey_tables()
    _b = _s[_s["table_id"] == "s7_p06_brand_needs"].copy()
    _b["value"] = pd.to_numeric(_b["value"], errors="coerce")
    _stack = alt.Chart(_b.dropna(subset=["value"])).mark_bar().encode(
        y=alt.Y("row:N", title=None, sort=None, axis=alt.Axis(labelLimit=260)), x=alt.X("value:Q", title="Respondents (%)", stack="zero"),
        color=alt.Color("column:N", scale=alt.Scale(range=charts.PALETTE[:4]), legend=alt.Legend(orient="bottom", title=None)), tooltip=["row", "column", "value"])
    _r = _s[_s["table_id"] == "s7_p07_formulator_needs"].rename(columns={"row": "x", "value": "y"}).assign(series="Respondents (%)")
    _r["y"] = pd.to_numeric(_r["y"])
    _c = data.chart("s7_p10_hair_concerns")
    _c2 = _c.copy()
    _c2["y"] = _c2["y"].astype(float)
    _gap = _c2.pivot(index="x", columns="series", values="y")
    _gap.columns = ["overall", "Black or African descent"]
    _gap["difference (points)"] = (_gap["Black or African descent"] - _gap["overall"]).round(1)
    _gap = _gap.reset_index().rename(columns={"x": "concern"}).sort_values("difference (points)", ascending=False)
    market = mo.vstack([
        mo.md("### What the market research says  " + ui.badge("reported")),
        mo.md("Four surveys frame the case (Euromonitor 2019 and 2022, Mintel 2022, Stepan Market Research Study 2021): over half of consumers trust sustainable-sourcing labels, "
              "58% of companies plan sustainable-sourcing claims and 70% environmentally friendly claims."),
        mo.md("**Where respondents place each need** (S7 p6)"),
        mo.ui.altair_chart(_stack.properties(width=560, height=180)),
        mo.md("**Critical needs of formulators** (S7 p7)"),
        mo.ui.altair_chart(charts.radar(_r, rmax=100, rings=5, size=420)),
        mo.md("**Top ten reported hair concerns** (S7 p10) and the gap between all respondents and those identifying as Black or African descent  " + ui.badge("digitised") + " " + ui.badge("derived")),
        mo.ui.altair_chart(charts.render("s7_p10_hair_concerns")),
        ui.table(_gap, 10),
        mo.md("The two groups rank the concerns differently: greying hair leads overall but is below average among the second group, where itchy scalp, dryness and trouble combing rise. "
              "That is why the claim slides test textured hair types separately."),
    ], gap=0.7)
    return (market,)


@app.cell(hide_code=True)
def _(mo, molecules, ui):
    _r_eq, _t_eq = molecules.carbon_counts(molecules.mol("soleil_eq"))
    _share = _r_eq / _t_eq
    _implied = (0.88 - _share) / (1 - _share)
    rows = [("BTAC", "btac"), ("CTAC", "ctac"), ("Ester quat of GA 90 / PA 85-G", "eq_b"), ("Ester quat of Soleil (dioleoyl)", "soleil_eq")]
    import pandas as _pd
    _t = _pd.DataFrame([{"structure": n, "renewable carbons": molecules.carbon_counts(molecules.mol(k))[0], "all carbons": molecules.carbon_counts(molecules.mol(k))[1],
                         "renewable share": round(molecules.renewable_fraction(k), 3)} for n, k in rows])
    carbon = mo.vstack([
        mo.md("### Where could a score of 0.88 come from?  " + ui.badge("derived")),
        mo.md(
            "S7 p12 prints an ISO 16128 score of 0.88 for STEPANQUAT Soleil, computed on biorenewable carbon and excluding water and impurities. Counting carbon in the structure "
            "I drew (two oleoyl chains, an ethylene-bridged head group and a methosulfate), 36 of 44 carbons come from fatty acid, a share of "
            f"**{_share:.3f}**. The product is not the quat alone, though: it is blended with sunflower seed oil glycerides, which are entirely renewable carbon. "
            f"If the 0.88 is a carbon-weighted average of the two, the blend must be about **{100 * _implied:.0f}% glyceride carbon**. The slide gives no composition, so this is a consistency check, not a finding."
        ),
        ui.table(_t, 4),
        ui.structure_gallery(["soleil_eq", "eq_b", "btac", "ctac"], size=(430, 240)),
    ], gap=0.7)
    return (carbon,)


@app.cell(hide_code=True)
def _(alt, charts, data, hair, mo, pd, ui):
    _fr = data.chart("s7_p21_frizz")
    _vo = data.chart("s7_p22_volume")
    _tr = data.chart("s7_p18_wet_combing")
    _tr = _tr[~_tr["series"].str.contains("Inset|error", regex=True)]
    _h = hair.value
    _t = pd.DataFrame({
        "treatment": ["BTAC", "CETAC", "STEPANQUAT Soleil"],
        f"frizz reduction on {_h} (%)": [float(_fr[(_fr["series"] == s) & (_fr["x"] == _h)]["y"].iloc[0]) for s in ("BTAC", "CETAC", "STEPANQUAT Soleil")],
        f"volume change on {_h} (%)": [float(_vo[(_vo["series"] == s) & (_vo["x"] == _h)]["y"].iloc[0]) for s in ("BTAC", "CETAC", "STEPANQUAT Soleil")],
    }).round(1)
    _comb = _tr.pivot_table(index="x", columns="series", values="y", sort=False).round(0)
    _red = pd.DataFrame({"hair type": _comb.columns, "no conditioning active (gmf)": _comb.loc["Chassis without conditioning active"].values,
                         "with BTAC (gmf)": _comb.loc["Chassis with BTAC"].values, "with Soleil (gmf)": _comb.loc["Chassis with STEPANQUAT Soleil"].values})
    _red["Soleil: reduction vs no active (%)"] = (100 * (1 - _red["with Soleil (gmf)"] / _red["no conditioning active (gmf)"])).round(0)
    _red["BTAC: reduction vs no active (%)"] = (100 * (1 - _red["with BTAC (gmf)"] / _red["no conditioning active (gmf)"])).round(0)
    claims = mo.vstack([
        mo.md("### Six claims, four hair types  " + ui.badge("digitised") + " " + ui.badge("derived")),
        mo.md(
            "Each claim has its instrument: scanning electron microscopy (smoothness), the rubine dye test (no build-up), the Dia-Stron MTT690 (tangles), "
            "BossaNova SAMBA (shine) and BossaNova BOLERO (flyaways, frizz, volume). Pick a hair type to see the three conditioning actives side by side on frizz and volume."
        ),
        hair,
        ui.table(_t, 3),
        mo.md("**Wet combing peak load** by hair type, with the drawn error bars:"),
        mo.ui.altair_chart(charts.bars(_tr_all := data.chart("s7_p18_wet_combing").query("not series.str.contains('Inset')", engine="python"), "Treatment", "Maximum peak load (gmf), lower means fewer tangles", width=760, label_fmt=".0f")),
        ui.table(_red, 3),
        mo.md(
            f"On types 1C and 2A, Soleil and BTAC are indistinguishable ({_red.loc[0, 'with Soleil (gmf)']:.0f} against {_red.loc[0, 'with BTAC (gmf)']:.0f} gmf, and "
            f"{_red.loc[1, 'with Soleil (gmf)']:.0f} against {_red.loc[1, 'with BTAC (gmf)']:.0f} gmf). On the coarser type 3A, Soleil is lower "
            f"({_red.loc[2, 'with Soleil (gmf)']:.0f} against {_red.loc[2, 'with BTAC (gmf)']:.0f} gmf) and the drawn error bars only just separate, so the slide's headline "
            "'equal to or outperforms BTAC' is a fair summary. The volume chart shows that Soleil flattens volume on textured hair (negative values, 'tamer curls'), "
            "which suits a curl-control claim but is the opposite of what a volumising claim would need."
        ),
        mo.md("**Shine, frizz and volume at a glance**"),
        mo.hstack([mo.ui.altair_chart(charts.render("s7_p20_shine")), mo.ui.altair_chart(charts.render("s7_p21_frizz")[0] if isinstance(charts.render("s7_p21_frizz"), list) else charts.render("s7_p21_frizz"))], wrap=True),
    ], gap=0.7)
    return (claims,)


@app.cell(hide_code=True)
def _(alt, cet, data, mo, np, pd, ui):
    _v = data.chart("s7_p23_viscosity_cetearyl")
    _v["x"] = _v["x"].astype(float)
    _v["y"] = _v["y"].astype(float)
    _rows = []
    for _s, _g in _v.groupby("series", sort=False):
        _g = _g.sort_values("x")
        _rows.append({"cationic (2% active)": _s, f"viscosity at {cet.value:.1f}% cetearyl alcohol (cP)": round(float(np.interp(cet.value, _g["x"], _g["y"])), -2)})
    _band = pd.DataFrame({"lo": [7000], "hi": [77000]})
    _bd = alt.Chart(_band).mark_rect(opacity=0.12, color="#e1a22c").encode(y="lo:Q", y2="hi:Q")
    _ln = alt.Chart(_v).mark_line(point=True, strokeWidth=2.2).encode(x=alt.X("x:Q", title="Cetearyl alcohol (%)", scale=alt.Scale(domain=[2, 5])), y=alt.Y("y:Q", title="Viscosity (cP)"),
                                                                       color=alt.Color("series:N", legend=alt.Legend(orient="bottom", columns=1, title=None, labelLimit=500)))
    _rule = alt.Chart(pd.DataFrame({"x": [cet.value]})).mark_rule(color="#d1495b").encode(x="x:Q")
    rheo = mo.vstack([
        mo.md("### Viscosity with fatty alcohol  " + ui.badge("digitised")),
        mo.md(
            "The slide (S7 p23) is a picture, so the four curves are read by eye against its axis (about +/-700 cP). The shaded band is the viscosity range of benchmark conditioners and "
            "masks that the slide marks with dashed lines (about 7,000 to 77,000 cP). BTAC jumps from near nothing at 3% cetearyl alcohol to 64,000 cP at 4%; Soleil builds steadily "
            "from 25,000 cP at 2%, which is what the slide means by a gradual thickening pattern."
        ),
        cet,
        mo.ui.altair_chart((_bd + _ln + _rule).properties(width=560, height=320)),
        ui.table(pd.DataFrame(_rows), 4),
    ], gap=0.7)
    return (rheo,)


@app.cell(hide_code=True)
def _(batch, data, f_pick, mo, pd, ui):
    _scale = pd.DataFrame({"hair type": ["1A, 1B, 1C", "2A, 2B, 2C", "3A, 3B, 3C", "4A, 4B, 4C"], "family": ["Straight", "Wavy", "Curly", "Kinky"],
                           "description (S7 p15)": ["fine and fragile to coarse and thin", "fine and thin to coarse and frizzy", "loose to corkscrew curls", "tight to Z-angled coils"]})
    guide = mo.vstack([
        mo.md("### Formulation guidelines  " + ui.badge("reported")),
        mo.md("Five formulas show how Soleil is processed: it is melted with the fatty alcohol at 65 C, emulsified into hot water and cooled to 40 C before the cold-added ingredients. "
              "Pick a formula and a batch size; trace items stay blank."),
        mo.hstack([f_pick, batch], justify="start", gap=2),
        ui.formula_card(f_pick.value, batch.value),
        mo.md("The hair-type scale used throughout the claim slides is Andre Walker's (S7 p15):"),
        ui.table(_scale, 4),
    ], gap=0.7)
    return (guide,)


@app.cell(hide_code=True)
def _(mo, ui):
    _qs = [
        {"id": "q1", "q": "What does S7 p12 say STEPANQUAT Soleil is free from?", "options": ["Silicones, preservatives, glycols and ethanol", "Only silicones", "Nothing is stated"], "answer": "Silicones, preservatives, glycols and ethanol",
         "why": "It also lists 100% actives, readily biodegradable and non-GMO EU-grown sunflower oil.", "source": "S7 p12"},
        {"id": "q2", "q": "Which instrument measured shine?", "options": ["BossaNova SAMBA", "Dia-Stron MTT690", "Scanning electron microscopy"], "answer": "BossaNova SAMBA", "why": "BOLERO measured frizz and volume, Dia-Stron measured combing.", "source": "S7 p14, p20"},
        {"id": "q3", "q": "Why is sodium benzoate with potassium sorbate not recommended for the hair mask?", "options": ["They strongly reduce its viscosity", "They are not permitted in masks", "They colour the mask"], "answer": "They strongly reduce its viscosity",
         "why": "S7 p25 says so and uses Euxyl K900 instead.", "source": "S7 p25"},
        {"id": "q4", "q": "In the digitised S7 p22 chart, which treatment reduces volume most on type 3A hair?", "options": ["STEPANQUAT Soleil", "BTAC", "CETAC"], "answer": "STEPANQUAT Soleil", "why": "About -55% for Soleil against -24% for BTAC and -21% for CETAC.", "source": "S7 p22"},
    ]
    answers = ui.quiz_elements(_qs)
    quiz_questions = _qs
    return answers, quiz_questions


@app.cell(hide_code=True)
def _(answers, data, mo, quiz_questions, ui):
    quiz = mo.vstack([mo.md("### Check yourself"), answers, ui.quiz_feedback(quiz_questions, answers.value)], gap=0.6)
    _c = data.chart_index()
    _c = _c[_c["deck"] == "S7"]
    data_tab = mo.vstack([mo.md("### Data behind this session"), ui.table(_c[["chart_id", "page", "title", "kind", "resolution"]], 10),
                          ui.csv_button(data.slides()[data.slides()["deck"] == "S7"], "s7_slide_ledger.csv", "Download the S7 slide ledger")], gap=0.6)
    return data_tab, quiz


@app.cell(hide_code=True)
def _(carbon, claims, data_tab, guide, market, mo, quiz, rheo, ui):
    walk = ui.slide_walkthrough("S7")
    brief = mo.md(
        """
        ### What the session argued

        Formulators want biorenewable sources but complain that sustainable conditioners feel less smooth and soft, need higher use levels and are hard to formulate. STEPANQUAT
        Soleil is offered as the answer: renewable-source, 100% active, no special handling, and equal to or better than BTAC on six tests carried out on four textured
        hair types in one standardised chassis.

        ### What I would keep in mind

        * The ISO 16128 score of 0.88 is Stepan's own calculation on biorenewable carbon, excluding water and impurities; it is not a certification and says nothing about performance.
        * Some figures are market-research percentages (Stepan Market Research Study 2021, Euromonitor, Mintel), others are instrument readings on tresses; the two kinds should not be mixed.
        * Two pages of the supplied file hold internal reviewer comments (S7 p2, p3). They carry no content and are not reproduced.
        """
    )
    mo.ui.tabs({"The session": brief, "Dry lab": mo.vstack([market, carbon, claims, rheo, guide], gap=1.6), "Every slide": walk, "Check yourself": quiz, "Data": data_tab})
    return


@app.cell(hide_code=True)
def _(ui):
    ui.footer()
    return


if __name__ == "__main__":
    app.run()
