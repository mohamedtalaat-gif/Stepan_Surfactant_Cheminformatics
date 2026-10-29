# Created by Muhammad Talaat, Faculty of Pharmacy, Ain Shams University
# SPDX-FileCopyrightText: 2026 Muhammad Talaat
# SPDX-License-Identifier: MIT

import marimo

__generated_with = "0.25.2"
app = marimo.App(width="medium", app_title="S6 Ester quats in hair conditioners")


@app.cell(hide_code=True)
def _():
    import altair as alt
    import marimo as mo
    import numpy as np
    import pandas as pd

    from stepan_lab import charts, data, formulation, molecules, physchem, ui

    return alt, charts, data, formulation, mo, molecules, np, pd, physchem, ui


@app.cell(hide_code=True)
def _(mo, ui):
    mo.vstack([
        ui.nav("s6_hair_conditioning"),
        ui.header("Ester quats in hair conditioners", "Session S6: substitutes for BTAC and CTAC, and bio-based conditioning boosters"),
        ui.byline(),
        mo.md(
            """
            Session S6 is the shortest (12 slides) and the most chemical. It sets two conventional quaternary ammonium conditioners, BTAC and CTAC, against a Stepan ester
            quat, and then adds two bio-based emollients (STEPAN-MILD GCC and L3) that close the sensory gap. The slides draw the structures and show small panel studies.
            In **Dry lab** I compute what the structures say about charge and packing, which the slides leave implicit.
            """
        ),
        mo.accordion({"How the numbers are labelled": ui.legend()}),
    ])
    return


@app.cell(hide_code=True)
def _(mo):
    active = mo.ui.slider(0.5, 5.0, value=2.0, step=0.1, label="Conditioning active (% w/w, as active matter)", show_value=True)
    x_alc = mo.ui.slider(0.0, 0.9, value=0.5, step=0.05, label="Mole fraction of cetyl alcohol in the aggregate", show_value=True)
    batch = mo.ui.slider(100, 5000, value=1000, step=50, label="Batch size (g)", show_value=True)
    f_pick = mo.ui.dropdown({"Conditioner with GA 90 and boosters (p10)": "s6_conditioner", "Cleansing conditioner (p11)": "s4_cleansing_conditioner", "Half-head chassis (p5)": "s6_halfhead_chassis"},
                            value="Conditioner with GA 90 and boosters (p10)", label="Formula")
    return active, batch, f_pick, x_alc


@app.cell(hide_code=True)
def _(active, alt, mo, molecules, pd, ui):
    _specs = [("BTAC", "btac"), ("CTAC", "ctac"), ("Ester quat of GA 90 and PA 85-G", "eq_b"), ("Ester quat of STEPANQUAT Soleil", "soleil_eq")]
    _rows = []
    for _name, _k in _specs:
        _mw = molecules.descriptors(_k)["mw_formula_unit"]
        _rows.append({"cationic active": _name, "molar mass of the salt (g/mol)": _mw, "mmol of cationic head per 100 g formula": round(active.value / _mw * 1000, 2)})
    _t = pd.DataFrame(_rows)
    _btac = _t.loc[0, "mmol of cationic head per 100 g formula"]
    _t["% active needed to match BTAC at this level"] = [round(active.value * r["molar mass of the salt (g/mol)"] / _t.loc[0, "molar mass of the salt (g/mol)"], 2) for _, r in _t.iterrows()]
    _chart = alt.Chart(_t).mark_bar(color="#1b7f8c").encode(x=alt.X("cationic active:N", sort=None, axis=alt.Axis(labelAngle=-15, title=None)), y=alt.Y("mmol of cationic head per 100 g formula:Q"),
                                                          tooltip=list(_t.columns))
    charge = mo.vstack([
        mo.md("### Charge per gram of conditioning active  " + ui.badge("derived")),
        mo.md(
            "A cationic conditioner works by depositing positive charge on negatively charged damaged hair, so a first-order measure of a conditioning active is how many "
            "quaternary head groups a gram of it carries. As the salt the ester quat has a molar mass of "
            f"{molecules.descriptors('eq_b')['mw_formula_unit']:.0f} g/mol against {molecules.descriptors('btac')['mw_formula_unit']:.0f} for BTAC and {molecules.descriptors('ctac')['mw_formula_unit']:.0f} for CTAC, "
            "so at the same percentage of active matter it supplies fewer head groups. Move the slider to set the level."
        ),
        active,
        mo.ui.altair_chart(_chart.properties(width=520, height=260)),
        ui.table(_t, 4),
        mo.md(
            "The slides state that STEPANTEX PA 85-G is equivalent to BTAC in a half-head test and that GA 90 plus GCC gives a close match, both at 2% active. "
            "So equal performance was reported at fewer head groups per gram, which suggests that charge count alone is not what the panel perceives."
        ),
    ], gap=0.7)
    return (charge,)


@app.cell(hide_code=True)
def _(alt, mo, molecules, np, pd, physchem, ui, x_alc):
    _bt = molecules.REGISTRY["btac"]
    _eq = molecules.REGISTRY["eq_b"]
    _ca = molecules.REGISTRY["cetylalcohol"]
    _rows = [
        {"aggregate": "BTAC alone", "P": physchem.packing_parameter(_bt.chain_n, _bt.head_a0)},
        {"aggregate": "CTAC alone", "P": physchem.packing_parameter(molecules.REGISTRY["ctac"].chain_n, molecules.REGISTRY["ctac"].head_a0)},
        {"aggregate": "Ester quat alone (two C16 chains)", "P": physchem.packing_parameter(_eq.chain_n, _eq.head_a0, n_chains=2)},
    ]
    for _x in (0.25, 0.5, 0.75):
        _rows.append({"aggregate": f"BTAC with {int(_x * 100)}% cetyl alcohol (mole fraction)", "P": physchem.mixed_packing_parameter([(1 - _x, _bt.chain_n, _bt.head_a0), (_x, _ca.chain_n, _ca.head_a0)])})
        _rows.append({"aggregate": f"Ester quat with {int(_x * 100)}% cetyl alcohol", "P": physchem.mixed_packing_parameter([(1 - _x, _eq.chain_n, _eq.head_a0, 2), (_x, _ca.chain_n, _ca.head_a0)])})
    _t = pd.DataFrame(_rows)
    _t["P"] = _t["P"].round(2)
    _t["expected aggregate"] = [physchem.aggregate_shape(p) for p in _t["P"]]
    _grid = np.linspace(0, 0.95, 60)
    _curve = pd.DataFrame({"fraction of cetyl alcohol": np.tile(_grid, 2),
                           "system": ["BTAC + cetyl alcohol"] * 60 + ["Ester quat + cetyl alcohol"] * 60,
                           "P": [physchem.mixed_packing_parameter([(1 - x, _bt.chain_n, _bt.head_a0), (x, _ca.chain_n, _ca.head_a0)]) for x in _grid]
                                + [physchem.mixed_packing_parameter([(1 - x, _eq.chain_n, _eq.head_a0, 2), (x, _ca.chain_n, _ca.head_a0)]) for x in _grid]})
    _lines = alt.Chart(_curve).mark_line(strokeWidth=2.4).encode(x="fraction of cetyl alcohol:Q", y=alt.Y("P:Q", scale=alt.Scale(domain=[0, 1.4])), color=alt.Color("system:N", legend=alt.Legend(orient="bottom", title=None)))
    _marks = alt.Chart(pd.DataFrame({"y": [1 / 3, 0.5, 1.0]})).mark_rule(strokeDash=[4, 4], color="#999").encode(y="y:Q")
    _sel = alt.Chart(pd.DataFrame({"x": [x_alc.value]})).mark_rule(color="#d1495b").encode(x="x:Q")
    _pb = physchem.mixed_packing_parameter([(1 - x_alc.value, _bt.chain_n, _bt.head_a0), (x_alc.value, _ca.chain_n, _ca.head_a0)])
    _pe = physchem.mixed_packing_parameter([(1 - x_alc.value, _eq.chain_n, _eq.head_a0, 2), (x_alc.value, _ca.chain_n, _ca.head_a0)])
    packing = mo.vstack([
        mo.md("### Why conditioners are lamellar gels  " + ui.badge("modelled")),
        mo.md(
            "The slide draws BTAC with one chain and the ester quat with two. In the packing picture of Israelachvili, a surfactant of volume v, head-group area a0 and chain length l "
            "forms spheres below P = v/(a0 l) = 1/3, rods up to 1/2 and bilayers from 1/2 to 1. A single-chain quat of C22 has P near 1/3; a double-chain ester quat sits "
            "near 0.65 and builds bilayers by itself. Add a fatty alcohol, which has almost no head group, and P rises for both: the conditioner becomes a lamellar gel network, "
            "which is why the formula has 4% of cetyl and stearyl alcohol. The head-group areas are my assumptions (BTAC 60, ester quat 65 square angstrom), so read the "
            "numbers for their direction, not their size."
        ),
        x_alc,
        mo.md(f"At {x_alc.value:.0%} cetyl alcohol, P is **{_pb:.2f}** for BTAC ({physchem.aggregate_shape(_pb)}) and **{_pe:.2f}** for the ester quat ({physchem.aggregate_shape(_pe)})."),
        mo.ui.altair_chart((_lines + _marks + _sel).properties(width=540, height=300)),
        ui.table(_t, 9),
        mo.md("Structures, with renewable carbon shaded:"),
        ui.structure_gallery(["btac", "ctac", "eq_b", "gcc_c8", "l3", "cetylalcohol", "steareth20"], size=(400, 230)),
    ], gap=0.7)
    return (packing,)


@app.cell(hide_code=True)
def _(charts, data, mo, pd, ui):
    _t = data.survey_tables()
    _t = _t[_t["table_id"] == "s6_p05_halfhead_pa85g"][["row", "value"]].rename(columns={"row": "attribute", "value": "difference from BTAC (0 to 2)"})
    _r8 = data.chart("s6_p08_gcc_sensory").pivot(index="x", columns="series", values="y").astype(float).round(2).reset_index().rename(columns={"x": "attribute"})
    panel = mo.vstack([
        mo.md("### The panel studies  " + ui.badge("reported") + " " + ui.badge("digitised")),
        mo.md(
            "Three small panels carry the whole evidence of the session: three panellists in a half-head test (PA 85-G against BTAC, S6 p5), five in a preliminary test of GA 90 with GCC "
            "(p8) and six in a salon half-head study of L3 (p9). The first is scored 0 (no difference) to 2 (very noticeable difference); only four of ten attributes show any difference."
        ),
        ui.table(_t, 10),
        mo.md("**GA 90 with GCC against BTAC** (radar, radii as a fraction of the outer ring because the slide prints no scale):"),
        mo.ui.altair_chart(charts.radar(data.chart("s6_p08_gcc_sensory"), rmax=1.0, rings=5)),
        ui.table(_r8, 9),
        mo.md(
            "Read the radar as relative: BTAC and BTAC with GCC are close to a regular ring of about 0.4, while GA 90 with GCC reaches out on rinsability, hair feel on dry hair, "
            "wet and dry combing and manageability. With three to six panellists these are preliminary results and the slide calls them so."
        ),
    ], gap=0.7)
    return (panel,)


@app.cell(hide_code=True)
def _(batch, data, f_pick, formulation, mo, pd, ui):
    _h, _l = data.formula("s6_conditioner")
    _w = {r.ingredient: float(r.pct_ww) for r in _l.itertuples() if str(r.pct_ww) not in ("", "nan")}
    _fa = _w["Cetyl alcohol"] + _w["Stearyl alcohol"]
    _ratio = pd.DataFrame([{"cetyl : stearyl : Steareth-20": f"{_w['Cetyl alcohol']:g} : {_w['Stearyl alcohol']:g} : {_w['Steareth-20']:g}",
                            "fatty alcohol total (%)": _fa, "fatty alcohol to ester quat (w/w, as supplied)": round(_fa / _w["STEPANQUAT GA90"], 2)}])
    formulas = mo.vstack([
        mo.md("### The formulas  " + ui.badge("reported")),
        mo.md("The conditioner (p10) combines 2% active GA 90 with up to 1% each of L3 and GCC and 4.5% of fatty alcohols and Steareth-20. The cleansing conditioner (p11, the same formula as S4 p24) "
              "replaces the lamellar network by an amine oxide and decyl glucoside system with sunflower and jojoba oils."),
        ui.table(_ratio, 1),
        mo.hstack([f_pick, batch], justify="start", gap=2),
        ui.formula_card(f_pick.value, batch.value),
    ], gap=0.7)
    return (formulas,)


@app.cell(hide_code=True)
def _(mo, ui):
    _qs = [
        {"id": "q1", "q": "Which restriction applies to BTAC and CTAC according to S6 p3?", "options": ["Restricted since 08/2014 in rinse-off hair products and leave-on hair and face products", "No restriction", "Banned in leave-on products only"],
         "answer": "Restricted since 08/2014 in rinse-off hair products and leave-on hair and face products", "why": "Ester quats are described as having no use restriction.", "source": "S6 p3"},
        {"id": "q2", "q": "What is the difference in solvent between STEPANQUAT GA 90 and STEPANTEX PA 85-G?", "options": ["IPA against DPG", "Water against IPA", "No solvent"], "answer": "IPA against DPG",
         "why": "GA 90 uses IPA (and is therefore flammable); PA 85-G uses DPG.", "source": "S6 p4"},
        {"id": "q3", "q": "How many panellists were in the half-head test of PA 85-G against BTAC?", "options": ["3", "5", "6"], "answer": "3", "why": "Five took part in the GA 90 + GCC test and six in the L3 study.", "source": "S6 p5, p8, p9"},
        {"id": "q4", "q": "At equal % active matter, which gives more cationic head groups per gram?", "options": ["BTAC, because its molar mass is lower", "The ester quat", "They are equal"], "answer": "BTAC, because its molar mass is lower",
         "why": "BTAC chloride is about 404 g/mol, the ester quat about 641 g/mol.", "source": "derived from the structures"},
    ]
    answers = ui.quiz_elements(_qs)
    quiz_questions = _qs
    return answers, quiz_questions


@app.cell(hide_code=True)
def _(answers, data, mo, quiz_questions, ui):
    quiz = mo.vstack([mo.md("### Check yourself"), answers, ui.quiz_feedback(quiz_questions, answers.value)], gap=0.6)
    _c = data.chart_index()
    _c = _c[_c["deck"] == "S6"]
    data_tab = mo.vstack([mo.md("### Data behind this session"), ui.table(_c[["chart_id", "page", "title", "kind", "resolution"]], 8),
                          ui.csv_button(data.slides()[data.slides()["deck"] == "S6"], "s6_slide_ledger.csv", "Download the S6 slide ledger")], gap=0.6)
    return data_tab, quiz


@app.cell(hide_code=True)
def _(charge, data_tab, formulas, mo, packing, panel, quiz, ui):
    walk = ui.slide_walkthrough("S6")
    brief = mo.md(
        """
        ### What the session argued

        BTAC and CTAC are cost-effective conditioning actives but carry restrictions and a hazard classification. An ester quat (dipalmitoylethyl hydroxyethylammonium methosulfate)
        has no use restriction and is offered as STEPANQUAT GA 90 (in IPA) and STEPANTEX PA 85-G (in DPG). Panels found PA 85-G equivalent to BTAC, and found that
        the bio-based emollients GCC and L3 add the missing slip, combing and feel.

        ### What I would keep in mind

        * Panel sizes are three, five and six; the studies are preliminary and show no scatter.
        * Slides p8 and p9 use different scales (a radar without printed scale and a 0 to 2 scale), so they cannot be combined.
        * The two ester-quat names GA 90 and PA 85-G share an INCI and differ in solvent and activity (about 90 and 85%).
        """
    )
    mo.ui.tabs({"The session": brief, "Dry lab": mo.vstack([charge, packing, panel, formulas], gap=1.6), "Every slide": walk, "Check yourself": quiz, "Data": data_tab})
    return


@app.cell(hide_code=True)
def _(ui):
    ui.footer()
    return


if __name__ == "__main__":
    app.run()
