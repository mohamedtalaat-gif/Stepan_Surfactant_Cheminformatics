# Created by Muhammad Talaat, Faculty of Pharmacy, Ain Shams University
# SPDX-FileCopyrightText: 2026 Muhammad Talaat
# SPDX-License-Identifier: MIT

import marimo

__generated_with = "0.25.2"
app = marimo.App(width="medium", app_title="Lab: formulation arithmetic")


@app.cell(hide_code=True)
def _():
    import marimo as mo
    import numpy as np
    import pandas as pd

    from stepan_lab import data, formulation, ui

    return data, formulation, mo, np, pd, ui


@app.cell(hide_code=True)
def _(mo, ui):
    mo.vstack([
        ui.nav("lab_formulation_math"),
        ui.header("Formulation arithmetic", "Lab: a batch sheet, actives and naturality for each of the 34 formulas transcribed from the seminar"),
        ui.byline(),
        mo.md(
            """
            Every formula printed in the six decks is in one table. This lab turns a percentage list into what you would weigh out, closes the water where the slide says
            *q.s. to 100*, reports the active matter where it can be known, recomputes chassis naturality and compares two formulas. It does arithmetic and nothing more: it does not predict
            viscosity, stability, mildness or sensory behaviour of a changed formula, and a modified formula must be tested at the bench.
            """
        ),
        mo.accordion({"How the numbers are labelled": ui.legend()}),
    ])
    return


@app.cell(hide_code=True)
def _(data, mo):
    _idx = data.formula_index()
    _opts = {f"{r.deck} p{r.page} · {r.name}": r.formula_id for r in _idx.itertuples()}
    f_a = mo.ui.dropdown(_opts, value=next(iter(_opts)), label="Formula A")
    f_b = mo.ui.dropdown(_opts, value=list(_opts)[1], label="Formula B")
    batch = mo.ui.slider(50, 10000, value=1000, step=50, label="Batch size (g)", show_value=True)
    unk = mo.ui.slider(0.0, 1.0, value=1.0, step=0.05, label="Natural-origin content assumed for unlisted ingredients", show_value=True)
    act = mo.ui.number(0.0, 100.0, value=4.5, step=0.1, label="Active matter wanted (%)")
    purity = mo.ui.number(1.0, 100.0, value=30.0, step=0.5, label="Raw material activity (%)")
    conc = mo.ui.slider(1.0, 10.0, value=4.0, step=0.5, label="Total parts after dilution", show_value=True)
    return act, batch, conc, f_a, f_b, purity, unk


@app.cell(hide_code=True)
def _(batch, data, f_a, formulation, mo, ui):
    _head, _lines = data.formula(f_a.value)
    _chk = formulation.check_sum(_lines)
    _sheet = formulation.scale_batch(_lines, batch.value)
    _out = ui.formula_table(f_a.value, batch.value)
    _tot = _sheet["grams"].sum(skipna=True)
    sheet = mo.vstack([
        mo.md("### Batch sheet  " + ui.badge("derived")),
        mo.hstack([f_a, batch], justify="start", gap=2),
        mo.md(f"**{_head['name']}**: {_chk['status']}. Weighed ingredients total {_tot:,.1f} g of a {batch.value:,.0f} g batch; "
              f"{_chk['trace_items']} trace item(s) (colour, pH adjuster, preservative marked q.s.) are left blank rather than guessed."),
        ui.table(_out, 20),
        ui.csv_button(_out, f"{f_a.value}_{batch.value}g.csv", "Download the batch sheet"),
    ], gap=0.7)
    return (sheet,)


@app.cell(hide_code=True)
def _(data, f_a, formulation, mo, pd, ui, unk):
    _head, _lines = data.formula(f_a.value)
    _t = formulation.actives_table(_lines)
    _known = _t[_t["active_pct_in_formula"].notna()]
    _split = formulation.charge_split(_lines)
    _p = data.products().set_index("product_id")
    _noc = {"asfmb": 0.81, "as40hasb": 0.59, "ninol": 0.86, "gcc": 1.0, "gccfl": 1.0, "l3": 1.0, "soleil": 0.88}
    _matched = {formulation.match_product(i) for i in _lines["ingredient"]} - {None}
    _rep = formulation.naturality_report(_lines, _noc, unk.value)
    _score, _unk = _rep["score"], _rep["assumed"]
    _rows = [{"ingredient": r.ingredient, "% in formula": round(r.pct, 3), "active matter (%)": round(r.active_pct_in_formula, 3), "source": r.active_source, "charge": r.charge}
             for r in _known.itertuples()]
    actives = mo.vstack([
        mo.md("### Active matter and naturality  " + ui.badge("derived")),
        mo.md("Active matter comes from the '% active' column where the slide prints one, and otherwise from the product's printed active content. Ingredients whose activity is not printed "
              "are left out, so the total is a lower bound."),
        ui.table(pd.DataFrame(_rows), 8) if _rows else mo.md("No ingredient of this formula has a known active content."),
        mo.md(f"Known active matter in this formula: **{_known['active_pct_in_formula'].sum():.2f}%**" + (f", of which by charge class: " + ", ".join(f"{k} {v:.2f}%" for k, v in _split.items()) if len(_split) else "") + "."),
        mo.md("**Chassis naturality** (S1 p14 and S3 p6 footnote: sum of weight fraction times natural-origin content, water = 1)"),
        unk,
        mo.md(f"Result: **{_score:.3f}**, using printed indices for the products I could match (blend 0.81, AS-40 HASB 0.59, NINOL CAA 0.86, GCC, GCC-FL and L3 1.0, Soleil 0.88) and "
              f"{unk.value:g} for everything else. {len(_unk)} ingredient(s) rest on that assumption. For the three S3 formulas the printed values (0.97, 0.95, 0.92) are reproduced with the assumption set to 1."),
    ], gap=0.7)
    return (actives,)


@app.cell(hide_code=True)
def _(data, f_a, f_b, formulation, mo, ui):
    _a = data.formula(f_a.value)[1]
    _b = data.formula(f_b.value)[1]
    _both = formulation.compare(_a, _b)
    compare = mo.vstack([
        mo.md("### Compare two formulas"),
        mo.md("Ingredients are matched by the name as printed, so the same raw material written two ways appears as two rows."),
        f_b,
        ui.table(_both, 14),
    ], gap=0.7)
    return (compare,)


@app.cell(hide_code=True)
def _(act, conc, mo, purity, ui):
    _ww = act.value / (purity.value / 100.0)
    _ratio = 1.0 / conc.value
    tools = mo.vstack([
        mo.md("### Two small converters  " + ui.badge("derived")),
        mo.md("**Active matter to as-supplied weight.** A formula that needs the stated active matter of a raw material of known activity uses:"),
        mo.hstack([act, purity], justify="start", gap=2),
        mo.md(f"{act.value:g}% active of a {purity.value:g}% active raw material is **{_ww:.2f}% w/w** as supplied. (S4: 4.5% active of AMPHOSOL DM/MB at 30% is 15% w/w.)"),
        mo.md("**Dilution of a concentrate.** One part concentrate in several parts of total mixture:"),
        conc,
        mo.md(f"Concentrate fraction **{_ratio:.1%}**; every ingredient of the concentrate is multiplied by {_ratio:.3f}. (S2 p22: 100 mL concentrate and 300 mL water is 4 parts.)"),
    ], gap=0.6)
    return (tools,)


@app.cell(hide_code=True)
def _(actives, compare, mo, sheet, tools):
    mo.vstack([sheet, actives, compare, tools], gap=2)
    return


@app.cell(hide_code=True)
def _(ui):
    ui.footer()
    return


if __name__ == "__main__":
    app.run()
