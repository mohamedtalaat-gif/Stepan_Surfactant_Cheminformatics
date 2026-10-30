# Created by Muhammad Talaat, Faculty of Pharmacy, Ain Shams University
# SPDX-FileCopyrightText: 2026 Muhammad Talaat
# SPDX-License-Identifier: MIT

import marimo

__generated_with = "0.25.2"
app = marimo.App(width="medium", app_title="Stepan Surfactant Cheminformatics")


@app.cell(hide_code=True)
def _():
    import marimo as mo
    import pandas as pd

    from stepan_lab import data, molecules, ui
    from stepan_lab.provenance import CITATION, CREDIT_LINE

    return CITATION, CREDIT_LINE, data, mo, molecules, pd, ui


@app.cell(hide_code=True)
def _(CREDIT_LINE, mo, ui):
    mo.vstack([
        ui.header("Stepan Surfactant Cheminformatics", "The surfactants and conditioning actives of the personal care seminar as structures, physical chemistry, formulation arithmetic and molecular dynamics"),
        ui.byline(),
        mo.md(
            """
            I attended the Stepan personal-care seminar as a consultant, and this is the seminar rebuilt so that a colleague who could not attend can work through the same material. It
            has six session notebooks, one for each deck I was given, and six labs. Every chart of the slides is redrawn from the geometry inside the slide, every formula is transcribed
            with its page, every surfactant has a drawn structure, and every claim that can be recomputed has been. The notebooks are not slide copies: each one has a **Dry lab** where the numbers
            can be moved and checked.
            """
        ),
    ])
    return


@app.cell(hide_code=True)
def _(data, mo, molecules, pd, ui):
    _s = data.slides()
    _c = data.chart_index()
    _f = data.formula_index()
    _rows = []
    for deck, (nb, title, sub) in ui.SESSIONS.items():
        _rows.append({"session": deck, "title": title, "slides": int((_s["deck"] == deck).sum()), "charts rebuilt": int((_c["deck"] == deck).sum()),
                      "formulas": int(_f["deck"].str.contains(deck).sum()), "notebook": f"/{nb}"})
    _t = pd.DataFrame(_rows)
    _cards = mo.hstack([
        mo.stat(label="Slides recorded", value=str(len(_s))), mo.stat(label="Charts rebuilt", value=str(len(_c))), mo.stat(label="Formulas transcribed", value=str(len(_f))),
        mo.stat(label="Products registered", value=str(len(data.products()))), mo.stat(label="Structures drawn", value=str(len(molecules.REGISTRY))),
    ], justify="start", gap=1.5)
    links = "".join(f'<li><a href="/{nb}"><b>{k}</b> &middot; {t}</a> <span style="color:#667">({sub})</span></li>' for k, (nb, t, sub) in ui.SESSIONS.items())
    labs = "".join(f'<li><a href="/{k}"><b>{t}</b></a> <span style="color:#667">({sub})</span></li>' for k, (t, sub) in ui.LABS.items())
    program = mo.vstack([
        _cards,
        mo.md("### Where to go"),
        mo.md("**The seminar, session by session**"),
        mo.Html(f"<ul style='line-height:1.8'>{links}</ul>"),
        mo.md("**The labs**"),
        mo.Html(f"<ul style='line-height:1.8'>{labs}</ul>"),
        mo.md("Each session notebook has the same five tabs: *The session* (what it argued and what to keep in mind), *Dry lab*, *Every slide* (all slides in order, with their data), *Check yourself* and *Data*."),
        mo.accordion({"Counts by session": ui.table(_t.drop(columns="notebook"), 8)}),
    ], gap=0.8)
    return (program,)


@app.cell(hide_code=True)
def _(data, mo, ui):
    _src = data.sources()[["deck", "title", "pages", "sha256"]]
    _pd = data.printed_vs_drawn()
    _within = int((_pd["rel_gap"] < 0.01).sum())
    _pictures = int((~data.chart_index()["method"].astype(str).str.startswith("vector")).sum())
    method = mo.vstack([
        mo.md("### How the numbers were obtained"),
        mo.md(
            "The decks were exported from presentation software, so most charts are stored as drawing instructions inside the PDF. I read those instructions and the axis tick labels "
            "(`scripts/capture_charts.py`), which gives values at the resolution of the drawing, far finer than reading a bar by eye. "
            f"{_pictures} charts were pasted into the slides as pictures; "
            "for those I measured marker positions in the bitmap (`scripts/capture_raster.py`) or read them against the printed axis, and the chart note says which. "
            f"Where a slide prints a value beside a mark, the printed value is kept and the drawn value sits next to it as a check. That happens {len(_pd)} times; the two agree within 1% in {_within} of them "
            f"and the largest gap is {_pd['abs_gap'].max():.1f} units (on a value of {_pd.loc[_pd['abs_gap'].idxmax(), 'printed']:g}). "
            "Formulas, product cards and statements were transcribed by hand from the text layer or, for pictures, from the picture, and each row carries its deck and page."
        ),
        mo.md("### Four kinds of number"),
        ui.legend(),
        mo.md("### What this is not"),
        mo.md(
            "It is not a prediction tool. A modified formula has to be tested for viscosity, stability, mildness, colour retention and regulatory status in the laboratory; the calculators do "
            "arithmetic on printed percentages and nothing else. It is also not a Stepan publication: the models, notebooks and texts are mine, and statements about Stepan products are limited "
            "to what the slides print."
        ),
        mo.accordion({"The six decks (SHA-256 recorded for verification)": ui.table(_src, 8)}),
    ], gap=0.8)
    return (method,)


@app.cell(hide_code=True)
def _(CITATION, CREDIT_LINE, mo):
    credit = mo.vstack([
        mo.md("### Credit and use"),
        mo.md(
            f"**{CREDIT_LINE}.** To cite: {CITATION}  \nThe code is under the MIT licence. The seminar content (names, marks, formulas, charts, test results) remains subject to the terms "
            "under which Stepan supplied it; see `CONTENT_NOTICE.md` and `references/source_register.md`."
        ),
    ], gap=0.6)
    return (credit,)


@app.cell(hide_code=True)
def _(credit, method, mo, program, ui):
    mo.vstack([ui.nav("start_here"), mo.ui.tabs({"Start": program, "Method and limits": method, "Credit": credit})], gap=0.8)
    return


@app.cell(hide_code=True)
def _(ui):
    ui.footer()
    return


if __name__ == "__main__":
    app.run()
