# Created by Muhammad Talaat, Faculty of Pharmacy, Ain Shams University
# SPDX-FileCopyrightText: 2026 Muhammad Talaat
# SPDX-License-Identifier: MIT

import marimo

__generated_with = "0.25.2"
app = marimo.App(width="medium", app_title="S4 Advanced colour protection systems")


@app.cell(hide_code=True)
def _():
    import altair as alt
    import marimo as mo
    import numpy as np
    import pandas as pd

    from stepan_lab import charts, colour, data, formulation, molecules, physchem, ui

    return alt, charts, colour, data, formulation, mo, molecules, np, pd, physchem, ui


@app.cell(hide_code=True)
def _(mo, ui):
    mo.vstack([
        ui.nav("s4_color_care"),
        ui.header("Advanced colour protection systems", "Session S4: surfactant screening, then anionic-free systems and a cleansing conditioner"),
        ui.byline(),
        mo.md(
            """
            Session S4 asks one question: what is the best way to protect dyed hair in a shampoo? Its answer has two layers. First screen the surfactants one by one
            by measuring colour loss on red-dyed bleached hair, then build complete systems, including one without any anionic surfactant. All five colour-loss
            charts of the session are rebuilt here with their error bars; under **Dry lab** I test what those bars can and cannot support.
            """
        ),
        mo.accordion({"How the numbers are labelled": ui.legend()}),
    ])
    return


@app.cell(hide_code=True)
def _(mo):
    L1, a1, b1 = (mo.ui.slider(0, 100, value=35, step=0.5, label="Reference L*", show_value=True),
                  mo.ui.slider(-60, 80, value=45, step=0.5, label="Reference a*", show_value=True),
                  mo.ui.slider(-60, 80, value=28, step=0.5, label="Reference b*", show_value=True))
    L2, a2, b2 = (mo.ui.slider(0, 100, value=38, step=0.5, label="Washed L*", show_value=True),
                  mo.ui.slider(-60, 80, value=41, step=0.5, label="Washed a*", show_value=True),
                  mo.ui.slider(-60, 80, value=27, step=0.5, label="Washed b*", show_value=True))
    washes = mo.ui.slider(1, 30, value=15, step=1, label="Number of washes", show_value=True)
    ph = mo.ui.slider(2.0, 9.0, value=5.5, step=0.1, label="pH", show_value=True)
    pka = mo.ui.slider(4.0, 8.0, value=6.5, step=0.1, label="Apparent pKa of the amine oxide", show_value=True)
    f_pick = mo.ui.dropdown({"Morning Caresse facial cleanser": "s4_morning_caresse", "Lotus Night body wash": "s4_lotus_night", "Colour-care shampoo 1605": "s4_1605",
                             "Anionic-free chassis": "s4_anionic_free", "Cleansing conditioner": "s4_cleansing_conditioner"}, value="Lotus Night body wash", label="Formula")
    batch = mo.ui.slider(100, 5000, value=1000, step=50, label="Batch size (g)", show_value=True)
    chart_pick = mo.ui.dropdown({"Primary surfactants (p9)": "s4_p09_fade_primary", "Secondary surfactants (p14)": "s4_p14_fade_secondary", "AMMONYX LO (p17)": "s4_p17_fade_ammonyx",
                                 "Prototype against market leader (p20)": "s4_p20_fade_prototype", "Next-generation systems (p25)": "s4_p25_fade_nextgen"},
                                value="Primary surfactants (p9)", label="Colour-loss chart")
    return L1, L2, a1, a2, b1, b2, batch, chart_pick, f_pick, ph, pka, washes


@app.cell(hide_code=True)
def _(chart_pick, charts, data, mo, pd, ui):
    _d = data.chart(chart_pick.value)
    _v = _d[_d["series"] == "dE"].set_index("x")["y"].astype(float)
    _e = _d[_d["series"] == "dE error bar half-length"].set_index("x")["y"].astype(float)
    _names = list(_v.index)
    _m = pd.DataFrame(index=_names, columns=_names, dtype=object)
    for _i in _names:
        for _j in _names:
            _diff = _v[_i] - _v[_j]
            _m.loc[_i, _j] = "" if _i == _j else (f"{_diff:+.2f}  (bars overlap)" if abs(_diff) < _e[_i] + _e[_j] else f"{_diff:+.2f}  (bars apart)")
    _m = _m.reset_index().rename(columns={"index": "row minus column"})
    fade = mo.vstack([
        mo.md("### How far apart are the colour-loss bars?  " + ui.badge("reported") + " " + ui.badge("digitised") + " " + ui.badge("derived")),
        mo.md(
            "On each chart the dE values are printed and the error bars are drawn. I read the error bars from the drawing, and **all of them have exactly the same half-length, 1.0 dE**, "
            "bar after bar and chart after chart. A measured scatter would hardly come out identical every time, so I suspect a fixed +/-1 added to every bar; the slides do not "
            "say what the bars are. Taken at face value they set a simple rule: two bars whose difference is less than 2.0 overlap."
        ),
        chart_pick,
        mo.ui.altair_chart(charts.bars(_d, "System", "Colour change dE (lower is better)", label_fmt=".2f", width=620)),
        mo.md("Pairwise differences (row minus column), with the overlap test against the drawn bars:"),
        ui.table(_m, 6),
        mo.md(
            "By that rule most of the headline contrasts hold (for instance SLES against AMMONYX LO, 8.71 against 3.61), but neighbouring bars such as the market leader and the "
            "Stepan prototype (6.63 against 6.12) overlap, which fits the slide's own wording 'similar performance'."
        ),
    ], gap=0.7)
    return (fade,)


@app.cell(hide_code=True)
def _(L1, L2, a1, a2, b1, b2, colour, mo, ui):
    _r, _w = (L1.value, a1.value, b1.value), (L2.value, a2.value, b2.value)
    _sw = lambda lab: "rgb(%d,%d,%d)" % colour.lab_to_srgb(lab)  # noqa: E731
    _d76, _d94, _d00 = colour.delta_e76(_r, _w), colour.delta_e94(_r, _w), colour.delta_e2000(_r, _w)
    lab = mo.vstack([
        mo.md("### A dE calculator  " + ui.badge("modelled")),
        mo.md(
            "The slides report dE from an L*a*b* measurement but do not say which dE formula the instrument applied. Set a reference colour (an unwashed red tress) "
            "and a washed one, and compare the three common formulas."
        ),
        mo.hstack([mo.vstack([L1, a1, b1]), mo.vstack([L2, a2, b2])], justify="start", gap=3),
        mo.Html(f'<div style="display:flex;gap:16px;align-items:center"><div style="width:120px;height:56px;border-radius:6px;background:{_sw(_r)}"></div>'
                f'<div style="width:120px;height:56px;border-radius:6px;background:{_sw(_w)}"></div>'
                f'<div>dE76 = <b>{_d76:.2f}</b> &nbsp; dE94 = <b>{_d94:.2f}</b> &nbsp; dE2000 = <b>{_d00:.2f}</b><br>'
                f'<span style="color:#556">By the slide\'s rule (S3 p23): {colour.perceptibility(_d00)}</span></div></div>'),
    ], gap=0.7)
    return (lab,)


@app.cell(hide_code=True)
def _(alt, data, mo, np, pd, ui, washes):
    _f = data.chart("s3_p23_fade")
    _rows, _curves = [], []
    _n = np.array([5.0, 10.0, 15.0])
    for _s, _g in _f.groupby("series", sort=False):
        _y = _g.sort_values("x", key=lambda c: c.str.extract(r"(\d+)")[0].astype(int))["y"].astype(float).to_numpy()
        _b, _la = np.polyfit(np.log(_n), np.log(_y), 1)
        _rows.append({"shampoo": _s, "exponent b in dE = a n^b": round(_b, 2), "a": round(float(np.exp(_la)), 2),
                      "dE at the chosen number of washes": round(float(np.exp(_la) * washes.value ** _b), 2)})
        for _k in range(1, 31):
            _curves.append({"series": _s, "washes": _k, "dE": float(np.exp(_la) * _k**_b), "kind": "fitted" if _k <= 15 else "extrapolated"})
    _c = pd.DataFrame(_curves)
    _pts = pd.DataFrame([{"series": r.series, "washes": int(str(r.x).split()[0]), "dE": float(r.y)} for r in _f.itertuples()])
    _line = alt.Chart(_c).mark_line().encode(x=alt.X("washes:Q", title="Number of washes"), y=alt.Y("dE:Q", title="Colour change dE"), color=alt.Color("series:N", legend=alt.Legend(orient="bottom", columns=1, title=None)),
                                             strokeDash=alt.StrokeDash("kind:N", scale=alt.Scale(domain=["fitted", "extrapolated"], range=[[1, 0], [5, 4]]), legend=None))
    _p = alt.Chart(_pts).mark_point(filled=True, size=70).encode(x="washes:Q", y="dE:Q", color="series:N")
    power = mo.vstack([
        mo.md("### A power law through three points  " + ui.badge("modelled")),
        mo.md(
            "S3 p23 gives dE after 5, 10 and 15 washes for three shampoos. Three points per shampoo are enough for a power law and no more, so treat this as a way of "
            "describing the shape rather than a prediction: colour loss keeps rising with every wash, at a decreasing rate (exponent well below 1)."
        ),
        washes,
        mo.ui.altair_chart((_line + _p).properties(width=560, height=300)),
        ui.table(pd.DataFrame(_rows), 3),
        mo.md("The dashed part beyond 15 washes is extrapolation. The slide has no data there."),
    ], gap=0.7)
    return (power,)


@app.cell(hide_code=True)
def _(alt, mo, np, pd, ph, physchem, pka, ui):
    _grid = np.linspace(2, 9, 71)
    _df = pd.DataFrame({"pH": _grid, "cationic share": [physchem.fraction_protonated(x, pka.value) for x in _grid]})
    _chart = alt.Chart(_df).mark_line(color="#1b7f8c", strokeWidth=2.4).encode(x="pH:Q", y=alt.Y("cationic share:Q", scale=alt.Scale(domain=[0, 1]))) + \
        alt.Chart(pd.DataFrame({"pH": [ph.value]})).mark_rule(color="#d1495b").encode(x="pH:Q")
    amine = mo.vstack([
        mo.md("### An amine oxide changes charge with pH  " + ui.badge("modelled")),
        mo.md(
            "S4 p15 and p16 draw AMMONYX LO as an amine oxide that is non-ionic above pH 6.5 and cationic below it. That is a protonation equilibrium of the N-oxide oxygen. "
            "I model it with the Henderson-Hasselbalch relation and an apparent pKa that you can move; the default 6.5 simply places the slide's transition at the "
            "half-protonated point."
        ),
        mo.hstack([ph, pka], justify="start", gap=2),
        mo.ui.altair_chart(_chart.properties(width=520, height=240)),
        mo.md(f"At pH {ph.value:.1f} about **{100 * physchem.fraction_protonated(ph.value, pka.value):.0f}%** of the amine oxide is protonated. The slides list "
              "'antistatic properties' and 'compatibility with quats' among the benefits, which both follow from a cationic charge at the pH of a shampoo."),
    ], gap=0.7)
    return (amine,)


@app.cell(hide_code=True)
def _(batch, data, f_pick, mo, pd, ui):
    _rows = []
    for _fid in ("s4_morning_caresse", "s4_lotus_night", "s4_anionic_free", "s4_cleansing_conditioner", "s6_conditioner"):
        _l = data.formula(_fid)[1]
        for _r in _l.itertuples():
            try:
                _w, _a = float(_r.pct_ww), float(_r.pct_active)
            except (TypeError, ValueError):
                continue
            if _w > 0 and _a > 0:
                _rows.append({"formula": _fid, "ingredient": _r.ingredient, "active (%)": _a, "w/w (%)": _w, "implied activity of the raw material (%)": round(100 * _a / _w, 1)})
    activity = mo.vstack([
        mo.md("### Active matter against as-supplied weight  " + ui.badge("derived")),
        mo.md(
            "Five S4 and S6 formulas print two columns, '% active' and '% w/w'. Their ratio is the activity of the raw material as supplied, so it can be checked "
            "against the product cards. AMPHOSOL DM/MB comes out at 30% (the card says 30%), STEPAN-MILD LSB/MB at 25% (card: 25%), the amine oxides at 30% (card: 30%). "
            "BIO-TERGE AS-40 HASB comes out at 40% in the Lotus Night formula, a little above the 37 to 39% on its card; STEPANQUAT GA 90 at about 90%; decyl glucoside at 50%."
        ),
        ui.table(pd.DataFrame(_rows), 14),
        mo.hstack([f_pick, batch], justify="start", gap=2),
        ui.formula_card(f_pick.value, batch.value),
    ], gap=0.7)
    return (activity,)


@app.cell(hide_code=True)
def _(mo, ui):
    _qs = [
        {"id": "q1", "q": "How were the tresses treated in the colour-loss test?", "options": ["Two ultrasound cycles of 10 min at 30 C, 3% actives, 500 mL per 3 wefts", "Fifteen washes by hand", "One 60 min soak at 45 C"],
         "answer": "Two ultrasound cycles of 10 min at 30 C, 3% actives, 500 mL per 3 wefts", "why": "This is the method box on every S4 colour-fade slide.", "source": "S4 p9, p14, p17, p20, p25"},
        {"id": "q2", "q": "Which system shows the lowest dE of all five charts?", "options": ["Cleansing conditioner (3.06)", "AMMONYX LO (3.61)", "DI water (3.41)"], "answer": "Cleansing conditioner (3.06)",
         "why": "3.06 is lower than DI water at 3.41 and AMMONYX LO at 3.61, but the error bars of +/-1 overlap.", "source": "S4 p25, p17"},
        {"id": "q3", "q": "Below which pH is an amine oxide cationic according to S4?", "options": ["6.5", "9", "3"], "answer": "6.5", "why": "The slide states 'cationic when pH < 6.5'.", "source": "S4 p15, p16"},
        {"id": "q4", "q": "In the Lotus Night formula, AMPHOSOL DM/MB is 4.5% active and 15% w/w. The raw material is:", "options": ["30% active", "45% active", "15% active"], "answer": "30% active", "why": "4.5 / 15 = 0.30, which matches the product card.", "source": "S4 p13, p11"},
    ]
    answers = ui.quiz_elements(_qs)
    quiz_questions = _qs
    return answers, quiz_questions


@app.cell(hide_code=True)
def _(answers, data, mo, quiz_questions, ui):
    quiz = mo.vstack([mo.md("### Check yourself"), answers, ui.quiz_feedback(quiz_questions, answers.value)], gap=0.6)
    _c = data.chart_index()
    _c = _c[_c["deck"] == "S4"]
    data_tab = mo.vstack([mo.md("### Data behind this session"), ui.table(_c[["chart_id", "page", "title", "kind", "resolution"]], 8),
                          ui.csv_button(data.slides()[data.slides()["deck"] == "S4"], "s4_slide_ledger.csv", "Download the S4 slide ledger")], gap=0.6)
    return data_tab, quiz


@app.cell(hide_code=True)
def _(activity, amine, data_tab, fade, lab, mo, power, quiz, ui):
    walk = ui.slide_walkthrough("S4")
    chem = mo.vstack([
        mo.md("### The molecules of the session"),
        mo.md("The identity cards of S4 draw the structures of LSB/MB, AS-40 HASB, AMPHOSOL DM/MB and the amine oxides. These are my own drawings from the same INCI names, with renewable carbon shaded."),
        ui.structure_gallery(["slsa", "dsls", "aos_ene", "aos_hydroxy", "cocobetaine", "lauramineoxide", "l3", "gcc_c8", "decylglucoside"], size=(380, 210)),
    ], gap=0.6)
    brief = mo.md(
        """
        ### What the session argued

        Anionic surfactants, and sulfates in particular, are the main cause of colour fading, so the first step is to choose gentle ones (STEPAN-MILD LSB/MB,
        BIO-TERGE AS-40 HASB) and the right secondary surfactant. The second step goes further: an anionic-free base built on an amine oxide, and a
        cleansing conditioner, both reaching colour loss close to plain water.

        ### What I would keep in mind

        * Every bar is one test with the same method; the error bars are +/-1.0 on every bar, so differences below 2 dE should not be over-read.
        * dE of DI water (3.41) is not zero: some colour is lost from the dyed tresses even without surfactant.
        * Foam is checked only for the prototype against one market leader (S4 p21), with similar volume and slightly lower stability.
        """
    )
    mo.ui.tabs({"The session": brief, "Dry lab": mo.vstack([fade, lab, power, amine, activity, chem], gap=1.6), "Every slide": walk, "Check yourself": quiz, "Data": data_tab})
    return


@app.cell(hide_code=True)
def _(ui):
    ui.footer()
    return


if __name__ == "__main__":
    app.run()
