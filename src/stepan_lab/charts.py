# Created by Muhammad Talaat, Faculty of Pharmacy, Ain Shams University
# SPDX-FileCopyrightText: 2026 Muhammad Talaat
# SPDX-License-Identifier: MIT

"""Altair renderers for the charts captured from the slides (data in data/charts)."""

from __future__ import annotations

import math

import altair as alt
import pandas as pd

from . import data

PALETTE = ["#1b7f8c", "#d1495b", "#3d3b8e", "#7a9e3f", "#e1a22c", "#8c4a8c", "#5c6b73", "#a6523b",
           "#2a9d8f", "#b5838d", "#6d597a", "#6c8a4b"]
ERR = " (error bar half-length)"
WIDTH, HEIGHT = 560, 330


def _colour(series):
    names = list(dict.fromkeys(series))
    return alt.Color("series:N", scale=alt.Scale(domain=names, range=(PALETTE * 3)[: len(names)]),
                     legend=alt.Legend(orient="bottom", columns=1, labelLimit=600, title=None, symbolType="stroke"))


def _split(df: pd.DataFrame, pattern: str | None, exclude: bool = False) -> pd.DataFrame:
    if not pattern:
        return df
    m = df["series"].str.contains(pattern, regex=True)
    return df[~m] if exclude else df[m]


def line(df: pd.DataFrame, x_title: str, y_title: str, *, points: bool = False, dashed_flag: str = "projection",
         width: int = WIDTH, height: int = HEIGHT, x_domain=None, y_domain=None, zero: bool = True) -> alt.Chart:
    d = df.copy()
    d["x"] = pd.to_numeric(d["x"], errors="coerce")
    d = d.dropna(subset=["x"])
    d["dashed"] = d["flag"].eq(dashed_flag)
    xs = alt.X("x:Q", title=x_title, scale=alt.Scale(zero=False, domain=x_domain) if x_domain else alt.Scale(zero=False))
    ys = alt.Y("y:Q", title=y_title, scale=alt.Scale(zero=zero, domain=y_domain) if y_domain else alt.Scale(zero=zero))
    base = alt.Chart(d).encode(x=xs, y=ys, color=_colour(d["series"]),
                               tooltip=["series:N", alt.Tooltip("x:Q", format=".3~f"), alt.Tooltip("y:Q", format=",.4~g")])
    chart = base.mark_line(strokeWidth=2).encode(strokeDash=alt.StrokeDash("dashed:N", legend=None,
                                                                         scale=alt.Scale(domain=[False, True], range=[[1, 0], [5, 4]])))
    if points:
        chart = chart + base.mark_point(filled=True, size=45)
    return chart.properties(width=width, height=height)


def bars(df: pd.DataFrame, x_title: str, y_title: str, *, width: int = WIDTH, height: int = HEIGHT, horizontal: bool = False,
         label_fmt: str = ",.3~g", y_domain=None) -> alt.Chart:
    err = df[df["series"].str.endswith(ERR)].copy()
    val = df[~df["series"].str.endswith(ERR)].copy()
    val["y"] = pd.to_numeric(val["y"], errors="coerce")
    if not err.empty:
        err["series"] = err["series"].str[: -len(ERR)]
        val = val.merge(err[["series", "x", "y"]].rename(columns={"y": "err"}), on=["series", "x"], how="left")
        val["lo"], val["hi"] = val["y"] - val["err"], val["y"] + val["err"]
    order = list(dict.fromkeys(val["x"]))
    multi = val["series"].nunique() > 1
    ysc = alt.Scale(domain=y_domain) if y_domain else alt.Scale()
    enc = dict(x=alt.X("x:N", sort=order, title=x_title, axis=alt.Axis(labelAngle=-30 if len(order) > 3 else 0, labelLimit=220)),
               y=alt.Y("y:Q", title=y_title, scale=ysc), color=_colour(val["series"]) if multi else alt.value(PALETTE[0]),
               tooltip=["series:N", "x:N", alt.Tooltip("y:Q", format=",.4~g")])
    if multi:
        enc["xOffset"] = alt.XOffset("series:N")
    base = alt.Chart(val)
    chart = base.mark_bar().encode(**enc)
    if "err" in val:
        e = dict(enc)
        e.pop("color", None)
        eb = base.mark_rule(color="#333", strokeWidth=1.4).encode(x=enc["x"], y=alt.Y("lo:Q"), y2="hi:Q",
                                                                     **({"xOffset": enc["xOffset"]} if multi else {}))
        chart = chart + eb
    txt = base.mark_text(dy=-6, fontSize=11, color="#555").encode(x=enc["x"], y="y:Q", text=alt.Text("y:Q", format=label_fmt),
                                                                  **({"xOffset": enc["xOffset"]} if multi else {}))
    return (chart + txt).properties(width=width, height=height)


def dual_axis(df: pd.DataFrame, x_title: str, left: tuple[str, str], right: tuple[str, str], *, width: int = WIDTH,
              height: int = HEIGHT, right_kind: str = "point") -> alt.Chart:
    """Bars on the left axis, markers or a line on the right axis."""
    lv = df[df["series"] == left[0]].copy()
    rv = df[df["series"] == right[0]].copy()
    for d in (lv, rv):
        d["y"] = pd.to_numeric(d["y"], errors="coerce")
    order = list(dict.fromkeys(lv["x"]))
    xax = alt.X("x:N", sort=order, title=x_title, axis=alt.Axis(labelAngle=-25 if len(order) > 3 else 0, labelLimit=220))
    b = alt.Chart(lv).mark_bar(color=PALETTE[0], opacity=0.85, size=34).encode(
        x=xax, y=alt.Y("y:Q", title=left[1], axis=alt.Axis(titleColor=PALETTE[0])), tooltip=["x:N", alt.Tooltip("y:Q", format=",.4~g")])
    bl = alt.Chart(lv).mark_text(dy=-8, fontSize=11, color=PALETTE[0]).encode(x=xax, y="y:Q", text=alt.Text("y:Q", format=",.0f"))
    mark = alt.Chart(rv)
    if right_kind == "line":
        r = mark.mark_line(color=PALETTE[1], strokeWidth=2.2, point=alt.OverlayMarkDef(color=PALETTE[1], size=70)).encode(
            x=xax, y=alt.Y("y:Q", title=right[1], axis=alt.Axis(titleColor=PALETTE[1])), tooltip=["x:N", alt.Tooltip("y:Q", format=",.4~g")])
    else:
        r = mark.mark_point(shape="diamond", filled=True, size=210, color=PALETTE[1]).encode(
            x=xax, y=alt.Y("y:Q", title=right[1], axis=alt.Axis(titleColor=PALETTE[1])), tooltip=["x:N", alt.Tooltip("y:Q", format=",.4~g")])
    return alt.layer(b + bl, r).resolve_scale(y="independent").properties(width=width, height=height)


def radar(df: pd.DataFrame, *, rmax: float | None = None, rings: int = 5, size: int = 440, unit_label: str = "") -> alt.Chart:
    """Radar chart drawn from polar coordinates; categories run clockwise from the top."""
    d = df.copy()
    d["y"] = pd.to_numeric(d["y"], errors="coerce")
    cats = list(dict.fromkeys(d["x"]))
    k = len(cats)
    rmax = rmax or float(math.ceil(d["y"].max() * 1.1 * 2) / 2)
    ang = {c: 2 * math.pi * i / k for i, c in enumerate(cats)}
    d["px"] = [r / rmax * math.sin(ang[c]) for r, c in zip(d["y"], d["x"])]
    d["py"] = [r / rmax * math.cos(ang[c]) for r, c in zip(d["y"], d["x"])]
    d["order"] = [cats.index(c) for c in d["x"]]
    closed = []
    for s, g in d.groupby("series", sort=False):
        g = g.sort_values("order")
        closed.append(pd.concat([g, g.iloc[[0]].assign(order=k)]))
    poly = pd.concat(closed)
    grid = []
    for ri in range(1, rings + 1):
        rr = ri / rings
        for i in range(k + 1):
            a = 2 * math.pi * (i % k) / k
            grid.append({"ring": ri, "i": i, "gx": rr * math.sin(a), "gy": rr * math.cos(a)})
    grid = pd.DataFrame(grid)
    spokes = pd.DataFrame([{"x0": 0, "y0": 0, "x1": math.sin(ang[c]), "y1": math.cos(ang[c])} for c in cats])
    labels = pd.DataFrame([{"lx": 1.18 * math.sin(ang[c]), "ly": 1.18 * math.cos(ang[c]), "t": c} for c in cats])
    scale = alt.Scale(domain=[-1.6, 1.6])
    ax = dict(axis=None, scale=scale)
    g = alt.Chart(grid).mark_line(color="#c9c9c9", strokeWidth=0.8).encode(x=alt.X("gx:Q", **ax), y=alt.Y("gy:Q", **ax), detail="ring:N", order="i:Q")
    sp = alt.Chart(spokes).mark_rule(color="#c9c9c9", strokeWidth=0.8).encode(x=alt.X("x0:Q", **ax), y=alt.Y("y0:Q", **ax), x2="x1:Q", y2="y1:Q")
    lb = alt.Chart(labels).mark_text(fontSize=11, color="#444", limit=130).encode(x=alt.X("lx:Q", **ax), y=alt.Y("ly:Q", **ax), text="t:N")
    colour = _colour(poly["series"])
    pl = alt.Chart(poly).mark_line(strokeWidth=2.2).encode(x=alt.X("px:Q", **ax), y=alt.Y("py:Q", **ax), color=colour, order="order:Q")
    pt = alt.Chart(d).mark_point(filled=True, size=55).encode(x=alt.X("px:Q", **ax), y=alt.Y("py:Q", **ax), color=colour,
                                                              tooltip=["series:N", "x:N", alt.Tooltip("y:Q", format=".3~g")])
    ring_lbl = pd.DataFrame([{"lx": 0.03, "ly": ri / rings, "t": f"{rmax * ri / rings:.3g}"} for ri in range(1, rings + 1)])
    rl = alt.Chart(ring_lbl).mark_text(fontSize=9, color="#888", align="left").encode(x=alt.X("lx:Q", **ax), y=alt.Y("ly:Q", **ax), text="t:N")
    return (g + sp + lb + rl + pl + pt).properties(width=size, height=size)


# ---------------------------------------------------------------------------------------------
# One entry point that knows how each captured chart should be drawn
# ---------------------------------------------------------------------------------------------

DUAL = {
    "s1_p12_foam_anionics": ("Foam volume (mL)", "Half life (s)"),
    "s1_p16_betaine_foam": ("Foam volume (mL)", "Half life (s)"),
    "s3_p09_foam": ("Foam volume (mL)", "Half life (s)"),
    "s4_p08_foam_aos": ("Foam volume (mL)", "Half life (s)"),
    "s4_p21_foam_prototype": ("Foam volume (mL)", "Half life (s)"),
    "s1_p20_ninol_foam": ("Foam volume (mL)", "Half life (s)"),
}


def render(chart_id: str, *, width: int = WIDTH, height: int = HEIGHT, **kw):
    """Return one Altair chart, or a list of charts for slides that held several panels."""
    meta = data.chart_meta(chart_id)
    df = data.chart(chart_id)
    xt, yt = meta["x_label"], meta["y_label"]

    if chart_id in DUAL:
        a, b = DUAL[chart_id]
        return dual_axis(df, xt, (a, a), (b, b), width=width, height=height)
    if chart_id == "s2_p05_market":
        return dual_axis(df, xt, ("Retail value (USD million)", "Retail value (USD million)"),
                         ("Current-year growth (%)", "Current-year growth (%)"), width=width, height=height, right_kind="line")
    if chart_id == "s2_p10_foam_sensory":
        return [bars(_split(df, r"^Sensory", exclude=True), "Shampoo and time", "Foam height (cm)", width=width, height=height, label_fmt=".2f"),
                radar(_split(df, r"^Sensory"), rmax=5, rings=5)]
    if chart_id == "s2_p13_breakage_drying":
        w = _split(df, r"^Water loss")
        w = w.assign(series=w["series"].str.replace("Water loss: ", "", regex=False))
        return [bars(_split(df, r"^Water loss", exclude=True), "Shampoo", "Hair breakage (%)", width=width, height=height, label_fmt=".3f"),
                line(w, "Time interval (min)", "Water loss (%)", points=True, width=width, height=height)]
    if chart_id == "s7_p30_gcc_tangles_shine":
        return [bars(_split(df, "Dry combing"), "Shampoo", "Dry combing peak load (gmf), lower is better", width=width, height=height),
                bars(_split(df, "Shine"), "Shampoo", "Shine change (%), higher is better", width=width, height=height)]
    if chart_id == "s7_p31_gcc_frizz_volume":
        return [bars(_split(df, "Frizz"), "Shampoo", "Frizz reduction (%)", width=width, height=height),
                bars(_split(df, "Volume"), "Shampoo", "Volume change (%)", width=width, height=height)]
    if chart_id == "s7_p18_wet_combing":
        return [bars(_split(df, "Inset", exclude=True), "Treatment", yt, width=width + 160, height=height),
                bars(_split(df, "Inset"), "Ester quat", "Wet combing peak load (gmf), type 1A/1B", width=width, height=height)]
    if meta["kind"] == "radar" or chart_id.startswith("s6_p0") and "sensory" in chart_id:
        mx = None if chart_id.startswith("s6_p08") else 2.0
        return radar(df, rmax=mx or 1.0, rings=5 if mx is None else 4)
    if chart_id == "s3_p10_salt_curves":
        curves = df[pd.to_numeric(df["x"], errors="coerce").notna()]
        return line(curves, xt, yt, width=width, height=height, x_domain=[0, 5])
    if meta["kind"] == "line":
        pts = chart_id in ("s2_p12_moisture", "s1_p20_ninol_visc", "s7_p23_viscosity_cetearyl")
        return line(df, xt, yt, points=pts, width=width, height=height)
    return bars(df, xt, yt, width=width, height=height)
