# Created by Muhammad Talaat, Faculty of Pharmacy, Ain Shams University
# SPDX-FileCopyrightText: 2026 Muhammad Talaat
# SPDX-License-Identifier: MIT

"""Marimo building blocks shared by the notebooks.

The functions are renderers: they take values (often read from a UI element that lives in the notebook)
and return something marimo can display.  Keeping state in the notebook keeps every cell reactive.
"""

from __future__ import annotations

import html

import marimo as mo
import numpy as np
import pandas as pd

from . import charts, data, evidence, formulation, molecules
from .provenance import CREDIT_LINE, ORCID, SOURCE_NOTICE, __version__

SESSIONS = {
    "S1": ("s1_aos_economics", "When sulfate free is the economical solution", "Alpha olefin sulfonate, thickening hacks, prototypes"),
    "S2": ("s2_modern_hair_care", "Mastering modern hair care", "Market, ALPHA-STEP PC-48 claims, lubricity and simplicity"),
    "S3": ("s3_stepanblend_asf_mb", "STEPANBLEND ASF/MB", "One ready-to-dilute blend, three formulas"),
    "S4": ("s4_color_care", "Advanced colour protection", "Surfactant screening and colour-care systems"),
    "S6": ("s6_hair_conditioning", "Ester quats in hair conditioners", "Substitutes for BTAC and CTAC, bio-based boosters"),
    "S7": ("s7_sustainable_conditioning", "Sustainably sourced ingredients for haircare", "STEPANQUAT Soleil, claims and guidelines"),
}
LABS = {
    "lab_molecules": ("Molecules and physical chemistry", "Structures in 3D, micelles and bilayers, packing, CMC, screening, renewable carbon"),
    "lab_dynamics": ("Molecular dynamics", "Self-assembly of the surfactants in water: micelles and bilayers from random chains"),
    "lab_formulation_math": ("Formulation arithmetic", "Batch sheets, actives, naturality, dilution for all 34 formulas"),
    "lab_salt_curves": ("Salt curves", "Every viscosity-against-salt curve of the seminar, with metrics"),
    "lab_colour_foam_mildness": ("Colour, foam and mildness", "dE, error bars, foam decay, Zein and M.C.I.I."),
    "slide_archive": ("Slide archive", "All 164 slides, 40 charts, 34 formulas, 33 products"),
}


# -- page furniture ----------------------------------------------------------------------------------

def byline() -> mo.Html:
    return mo.Html(
        f'<div style="color:#667;font-size:0.92em;margin:-6px 0 8px 0">{html.escape(CREDIT_LINE)}'
        f' &middot; ORCID <a href="https://orcid.org/{ORCID}">{ORCID}</a> &middot; version {__version__}</div>'
    )


def header(title: str, subtitle: str = "") -> mo.Html:
    sub = f'<div style="font-size:1.12em;color:#556;margin-top:2px">{html.escape(subtitle)}</div>' if subtitle else ""
    return mo.Html(
        f'<div style="padding:6px 0 4px 0"><div style="font-size:2.0em;font-weight:700;line-height:1.15;color:#1c2a39">{html.escape(title)}</div>{sub}</div>'
    )


def nav(current: str = "") -> mo.Html:
    items = [("Start", "/")] + [(f"{k}", f"/{v[0]}") for k, v in SESSIONS.items()] + [(v[0], f"/{k}") for k, v in LABS.items()]
    links = " &nbsp;|&nbsp; ".join(f'<a href="{u}" style="text-decoration:none;{"font-weight:700" if current==u.strip("/") else ""}">{html.escape(t)}</a>' for t, u in items)
    return mo.Html(f'<div style="font-size:0.88em;color:#667;padding:2px 0 6px 0">Sessions and labs: {links}</div>')


def footer() -> mo.Html:
    return mo.Html(
        f'<hr style="margin-top:28px"><div style="font-size:0.82em;color:#667;line-height:1.5">{html.escape(CREDIT_LINE)}. '
        f'{html.escape(SOURCE_NOTICE)} Nothing here is a formulation recommendation: a modified formula has to be checked in the laboratory '
        f'for stability, safety, performance and regulatory status.</div>'
    )


def legend() -> mo.Html:
    return mo.Html(evidence.legend_html())


def badge(kind: str) -> str:
    return evidence.badge(kind)


# -- tables ------------------------------------------------------------------------------------------

def table(df: pd.DataFrame, page_size: int = 12, selection=None, label: str = ""):
    return mo.ui.table(df.reset_index(drop=True), selection=selection, page_size=page_size, label=label, show_download=True)


def csv_button(df: pd.DataFrame, filename: str, label: str = "Download CSV"):
    return mo.download(data=df.to_csv(index=False).encode("utf-8"), filename=filename, mimetype="text/csv", label=label)


# -- charts ------------------------------------------------------------------------------------------

def chart_kinds(df: pd.DataFrame) -> list[str]:
    src = set(df["y_source"].astype(str))
    out = []
    if src & {"printed", "reference"}:
        out.append("reported")
    if src & {"geometry", "raster"}:
        out.append("digitised")
    return out or ["digitised"]


def chart_card(chart_id: str, *, show_data: bool = True, width: int = charts.WIDTH, height: int = charts.HEIGHT) -> mo.Html:
    meta = data.chart_meta(chart_id)
    df = data.chart(chart_id)
    figs = charts.render(chart_id, width=width, height=height)
    figs = figs if isinstance(figs, list) else [figs]
    badges = " ".join(badge(k) for k in chart_kinds(df))
    raster = "raster" in set(df["y_source"].astype(str))
    method = "read from a picture on the slide" if raster else "read from the drawing on the slide, calibrated on its axis labels"
    res = f", resolution about {meta['resolution']}" if str(meta["resolution"]) not in ("", "nan") else ""
    head = mo.md(
        f"**{meta['title']}**  \n"
        f"<span style='color:#667;font-size:0.9em'>Slide {meta['deck']} p{int(meta['page'])} &middot; {method}{res}</span> {badges}"
    )
    parts = [head, mo.hstack([mo.ui.altair_chart(f) if hasattr(f, "to_dict") else f for f in figs], wrap=True, justify="start")]
    if str(meta["note"]) not in ("", "nan"):
        parts.append(mo.md(f"<span style='color:#556;font-size:0.9em'>{meta['note']}</span>"))
    if show_data:
        parts.append(mo.accordion({"Data behind this chart": mo.vstack([table(df[["series", "x", "y", "y_source", "y_geometry", "flag"]], 8),
                                                                       csv_button(df, f"{chart_id}.csv")])}))
    return mo.vstack(parts, gap=0.6)


# -- formulas ----------------------------------------------------------------------------------------

def formula_table(formula_id: str, batch_g: float | None = None) -> pd.DataFrame:
    head, lines = data.formula(formula_id)
    df = formulation.resolve(lines)
    out = pd.DataFrame({
        "phase": lines["phase"], "ingredient": lines["ingredient"], "INCI": lines["inci"],
        "% w/w": df["pct"].round(3), "% active (printed)": lines["pct_active"], "note": lines["qs"].map({"qs": "q.s.", "to100": "q.s. to 100", "to_pH": "q.s. to pH"}).fillna("")
        + np.where(lines["note"] != "", " " + lines["note"], ""),
    })
    if batch_g:
        out.insert(4, "grams", (df["pct"] * batch_g / 100.0).round(2))
    for col in ("phase", "INCI", "note"):
        if (out[col].astype(str).str.strip() == "").all():
            out = out.drop(columns=col)
    if out["% active (printed)"].isna().all() or (out["% active (printed)"].astype(str).str.strip() == "").all():
        out = out.drop(columns="% active (printed)")
    return out


def formula_card(formula_id: str, batch_g: float | None = None) -> mo.Html:
    head, lines = data.formula(formula_id)
    chk = formulation.check_sum(lines)
    meta_bits = []
    for label, key in (("Reference", "reference_no"), ("Total actives (%)", "total_actives_pct"), ("pH", "ph"),
                       ("Viscosity (cP)", "viscosity_cp"), ("Method", "viscosity_method"), ("Appearance", "appearance")):
        v = head.get(key)
        if isinstance(v, str) and v and v != "nan":
            meta_bits.append(f"**{label}:** {v}")
    steps = data.process_steps()
    steps = steps[steps["formula_id"] == formula_id]
    parts = [
        mo.md(f"**{head['name']}** &nbsp;<span style='color:#667;font-size:0.9em'>Slide {head['deck']} p{head['page']} &middot; {badge('reported')} &middot; {chk['status']}</span>"),
        mo.md(" &nbsp;|&nbsp; ".join(meta_bits)) if meta_bits else mo.md(""),
        table(formula_table(formula_id, batch_g), page_size=20),
    ]
    if not steps.empty:
        parts.append(mo.accordion({"Process as printed": mo.md("\n".join(f"{int(r.step)}. {r.text}" for r in steps.itertuples()))}))
    if isinstance(head.get("notes"), str) and head["notes"] and head["notes"] != "nan":
        parts.append(mo.md(f"<span style='color:#556;font-size:0.9em'>{head['notes']}</span>"))
    return mo.vstack(parts, gap=0.5)


# -- products and structures ------------------------------------------------------------------------

def product_card(product_id: str) -> mo.Html:
    r = data.products().set_index("product_id").loc[product_id]
    bits = [f"**{r['trade_name']}**", f"INCI: {r['inci']}", f"{r['family']}, {r['charge']}", f"role: {r['role']}"]
    if pd.notna(r["active_pct"]):
        bits.append(f"active: {r['active_pct']:g}%")
    if isinstance(r["form"], str):
        bits.append(r["form"])
    return mo.md(" &nbsp;&middot;&nbsp; ".join(bits) + f"  \n<span style='color:#556;font-size:0.9em'>{r['other_properties']} (slides {r['source_refs']})</span>")


def structure_card(key: str, *, size=(430, 240)) -> mo.Html:
    s = molecules.REGISTRY[key]
    d = molecules.descriptors(key)
    r, t = molecules.carbon_counts(molecules.mol(key))
    ren = f"{r}/{t} carbons renewable = {r / t:.0%}" if s.renewable_known else "renewable carbon not derived for this structure"
    svg = molecules.draw_svg(key, size=size)
    cap = (f"<b>{html.escape(s.name)}</b><br><span style='color:#556'>{html.escape(s.family)}, {html.escape(s.charge_class)}</span><br>"
           f"<span style='font-size:0.88em'>{d['formula']} &middot; M(amphiphile) {d['mw_amphiphile']} &middot; {ren}</span>")
    return mo.Html(f'<div style="border:1px solid #d8dde3;border-radius:8px;padding:6px 10px;display:inline-block;margin:4px;vertical-align:top;max-width:{size[0]+30}px">{svg}<div style="font-size:0.95em">{cap}</div></div>')


def structure_gallery(keys: list[str], size=(400, 220)) -> mo.Html:
    return mo.Html("".join(structure_card(k, size=size).text for k in keys))


# -- slides ------------------------------------------------------------------------------------------

KIND_ICON = {"chart": "chart", "formula": "formula", "product": "product", "table": "table", "diagram": "diagram", "photo": "photo",
             "poll": "poll", "divider": "divider", "title": "title", "closing": "closing", "contacts": "contacts", "internal": "withheld",
             "timeline": "timeline", "agenda": "agenda", "video": "video", "statistic": "statistic"}


def slide_cards(deck: str, page: int) -> list:
    sl = data.slides()
    row = sl[(sl["deck"] == deck) & (sl["page"] == page)].iloc[0]
    out = []
    for ref in [x for x in str(row["refs"]).split(";") if x]:
        kind, _, key = ref.partition(":")
        try:
            if kind == "chart":
                out.append(chart_card(key))
            elif kind == "formula":
                out.append(formula_card(key))
            elif kind == "product":
                out.append(product_card(key))
            elif kind == "table":
                out.append(survey_table_card(key))
            elif kind == "timeline":
                out.append(table(data.timeline()[data.timeline()["deck"] == deck]))
        except KeyError:
            continue
    cl = data.claims()
    cl = cl[(cl["deck"] == deck) & (cl["page"].astype(str) == str(page))]
    if not cl.empty:
        out.append(mo.md("\n".join(f"- {r.statement} <span style='color:#667'>({badge('reported')})</span>" for r in cl.itertuples())))
    return out


def survey_table_card(table_id: str) -> mo.Html:
    if table_id == "additive_ratings":
        df = data.additive_ratings()
        wide = df.pivot(index="attribute", columns="product", values="stars").reset_index()
        return mo.vstack([mo.md("**Star ratings, STEPAN additives** (0 = not applicable or blank, 1 marginal, 2 good, 3 excellent)"), table(wide, 14)])
    df = data.survey_tables()
    df = df[df["table_id"] == table_id]
    head = df.iloc[0]
    wide = df.pivot(index="row", columns="column", values="value").reset_index()
    return mo.vstack([mo.md(f"**{head['title']}** &nbsp;<span style='color:#667;font-size:0.9em'>Slide {head['deck']} p{head['page']} &middot; {badge('reported')}</span>"),
                      table(wide, 12), mo.md(f"<span style='color:#556;font-size:0.9em'>{head['note']}</span>")])


def slide_walkthrough(deck: str) -> mo.Html:
    sl = data.slides()
    sl = sl[sl["deck"] == deck].sort_values("page")
    items = {}
    for r in sl.itertuples():
        label = f"p{r.page:02d} &nbsp; {r.title} &nbsp; ({r.kind})"
        body = [mo.md(r.summary)]
        if r.kind == "internal":
            body = [mo.md("This page of the supplied file holds internal reviewer comments. It carries no seminar content and is not reproduced.")]
        elif r.kind == "contacts":
            body = [mo.md("This page of the supplied file holds personal contact details. It carries no seminar content and is not reproduced.")]
        else:
            body += slide_cards(deck, int(r.page))
        items[label] = mo.vstack(body, gap=0.6)
    return mo.accordion(items, multiple=True)


# -- quiz --------------------------------------------------------------------------------------------

def quiz_elements(questions: list[dict]):
    return mo.ui.dictionary({q["id"]: mo.ui.radio(options=q["options"], label=q["q"]) for q in questions})


def quiz_feedback(questions: list[dict], answers: dict):
    lines, score, answered = [], 0, 0
    for q in questions:
        a = answers.get(q["id"])
        if a is None:
            continue
        answered += 1
        ok = a == q["answer"]
        score += ok
        lines.append(f"{'Correct' if ok else 'Not quite'}. **{q['q']}**  \nYou chose *{a}*. {q['why']} <span style='color:#667'>({q['source']})</span>")
    if not answered:
        return mo.md("Answer a question to see the explanation and the slide it comes from.")
    return mo.md(f"**{score} of {answered} answered correctly.**\n\n" + "\n\n".join(lines))
