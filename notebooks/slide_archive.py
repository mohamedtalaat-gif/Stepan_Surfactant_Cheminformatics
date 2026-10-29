# Created by Muhammad Talaat, Faculty of Pharmacy, Ain Shams University
# SPDX-FileCopyrightText: 2026 Muhammad Talaat
# SPDX-License-Identifier: MIT

import marimo

__generated_with = "0.25.2"
app = marimo.App(width="medium", app_title="Slide archive")


@app.cell(hide_code=True)
def _():
    import marimo as mo
    import pandas as pd

    from stepan_lab import data, molecules, ui

    return data, mo, molecules, pd, ui


@app.cell(hide_code=True)
def _(mo, ui):
    mo.vstack([
        ui.nav("slide_archive"),
        ui.header("Slide archive", "All 164 slides, 40 charts, 34 formulas and 33 products of the six decks"),
        ui.byline(),
        mo.md(
            """
            The archive is the index to everything else. Each slide of every deck has a line in the ledger with its title, its kind, what it shows and what I extracted from it. Pick a slide and its
            charts, formulas and products open below it, rebuilt as live objects. Slides that carry no seminar content (polls, section dividers, contact pages) are listed so that the numbering
            of the originals can be followed; six pages that held reviewer comments (S3 p20, S7 p2 and p3) or personal contact details (S4 p26, S6 p12, S7 p32) are listed but not reproduced.
            """
        ),
    ])
    return


@app.cell(hide_code=True)
def _(data, mo):
    deck = mo.ui.dropdown(["all"] + sorted(data.slides()["deck"].unique()), value="all", label="Deck")
    kind = mo.ui.dropdown(["all"] + sorted(data.slides()["kind"].unique()), value="all", label="Kind of slide")
    text = mo.ui.text(placeholder="search titles and summaries", label="Search")
    chart_pick = mo.ui.dropdown({f"{r.deck} p{r.page} · {r.title}": r.chart_id for r in data.chart_index().itertuples()}, value=None, label="Chart")
    f_pick = mo.ui.dropdown({f"{r.deck} p{r.page} · {r.name}": r.formula_id for r in data.formula_index().itertuples()}, value=None, label="Formula")
    p_pick = mo.ui.dropdown({f"{r.trade_name} ({r.inci})": r.product_id for r in data.products().itertuples()}, value=None, label="Product")
    batch = mo.ui.slider(50, 5000, value=1000, step=50, label="Batch size (g)", show_value=True)
    return batch, chart_pick, deck, f_pick, kind, p_pick, text


@app.cell(hide_code=True)
def _(data, deck, kind, mo, text, ui):
    _s = data.slides()
    if deck.value != "all":
        _s = _s[_s["deck"] == deck.value]
    if kind.value != "all":
        _s = _s[_s["kind"] == kind.value]
    if text.value:
        _m = _s["title"].str.contains(text.value, case=False) | _s["summary"].str.contains(text.value, case=False)
        _s = _s[_m]
    table = mo.ui.table(_s[["deck", "page", "title", "kind", "summary"]].reset_index(drop=True), selection="single", page_size=10, label=f"{len(_s)} slides")
    slides_tab = mo.vstack([mo.hstack([deck, kind, text], justify="start", gap=2), table], gap=0.7)
    return slides_tab, table


@app.cell(hide_code=True)
def _(mo, table, ui):
    _sel = table.value
    if _sel is None or len(_sel) == 0:
        detail = mo.md("Select a slide in the table to open what I extracted from it.")
    else:
        _r = _sel.iloc[0]
        if _r["kind"] == "internal":
            detail = mo.md(f"**{_r['deck']} p{_r['page']}**  \nThis page holds internal reviewer comments and carries no seminar content. It is not reproduced.")
        elif _r["kind"] == "contacts":
            detail = mo.md(f"**{_r['deck']} p{_r['page']}**  \nThis page holds personal contact details and carries no seminar content. It is not reproduced.")
        else:
            _cards = ui.slide_cards(_r["deck"], int(_r["page"]))
            detail = mo.vstack([mo.md(f"### {_r['deck']} p{_r['page']} · {_r['title']}  \n*{_r['kind']}*. {_r['summary']}")] + (_cards or [mo.md("This slide carries no data object of its own.")]), gap=0.8)
    return (detail,)


@app.cell(hide_code=True)
def _(batch, chart_pick, data, f_pick, mo, molecules, p_pick, ui):
    _chart = ui.chart_card(chart_pick.value) if chart_pick.value else mo.md("Choose a chart above.")
    _formula = ui.formula_card(f_pick.value, batch.value) if f_pick.value else mo.md("Choose a formula above; the batch size then scales its batch sheet.")
    _prod = [mo.md("Choose a product above.")]
    if p_pick.value:
        _prod = [ui.product_card(p_pick.value)]
        _keys = [k for k, s in molecules.REGISTRY.items() if p_pick.value in s.products]
        if _keys:
            _prod.append(mo.md("Structures that I drew for this product:"))
            _prod.append(ui.structure_gallery(_keys, size=(400, 220)))
    charts_tab = mo.vstack([chart_pick, _chart], gap=0.8)
    formulas_tab = mo.vstack([mo.hstack([f_pick, batch], justify="start", gap=2), _formula], gap=0.8)
    products_tab = mo.vstack([p_pick] + _prod, gap=0.8)
    return charts_tab, formulas_tab, products_tab


@app.cell(hide_code=True)
def _(data, mo, ui):
    _src = data.sources()[["deck", "title", "file", "pages", "sha256", "note"]]
    sources_tab = mo.vstack([
        mo.md("### Sources"),
        mo.md("The six decks that I worked from. The SHA-256 of each file is recorded so that anyone holding the same deck can check that it is the one used here. "
              "Deck 5 of the numbered series was not among the supplied files."),
        ui.table(_src, 8),
        ui.csv_button(data.slides(), "slide_ledger.csv", "Download the slide ledger"),
        ui.csv_button(data.chart_index(), "chart_index.csv", "Download the chart index"),
    ], gap=0.7)
    return (sources_tab,)


@app.cell(hide_code=True)
def _(charts_tab, detail, formulas_tab, mo, products_tab, slides_tab, sources_tab):
    mo.ui.tabs({"Slides": mo.vstack([slides_tab, detail], gap=1.2), "Charts": charts_tab, "Formulas": formulas_tab, "Products": products_tab, "Sources": sources_tab})
    return


@app.cell(hide_code=True)
def _(ui):
    ui.footer()
    return


if __name__ == "__main__":
    app.run()
