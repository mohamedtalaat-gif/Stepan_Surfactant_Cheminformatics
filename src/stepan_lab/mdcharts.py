# Created by Muhammad Talaat, Faculty of Pharmacy, Ain Shams University
# SPDX-FileCopyrightText: 2026 Muhammad Talaat
# SPDX-License-Identifier: MIT
"""Charts and tables of the coarse-grained molecular dynamics results (the dictionaries of md.to_dict)."""

from __future__ import annotations

import altair as alt
import pandas as pd

from . import md

TEAL, PINK, BLUE, AMBER = "#0f9d8a", "#d6385a", "#3d6fd1", "#d98c1f"


def series_frame(d: dict) -> pd.DataFrame:
    s = d["series"]
    return pd.DataFrame({"t (ns)": s["t_ns"], "largest aggregate": s["largest"], "mean aggregate size": s["mean_agg"], "aggregates": s["aggregates"],
                         "free fraction": s["free_fraction"], "Rg of the largest (nm)": s["rg_nm"], "asphericity": s["asphericity"], "potential energy (kJ/mol)": s["energy_kj_mol"]})


def size_chart(d: dict, height: int = 220) -> alt.Chart:
    df = series_frame(d).melt("t (ns)", ["largest aggregate", "mean aggregate size"], var_name="measure", value_name="molecules")
    return (alt.Chart(df).mark_line(strokeWidth=2).encode(
        x=alt.X("t (ns):Q", title="time (ns)"), y=alt.Y("molecules:Q", title="molecules in the aggregate"),
        color=alt.Color("measure:N", scale=alt.Scale(range=[TEAL, PINK]), legend=alt.Legend(orient="top", title=None)),
        tooltip=["t (ns)", "measure", "molecules"]).properties(height=height, title="Aggregation").interactive())


def shape_chart(d: dict, height: int = 220) -> alt.Chart:
    df = series_frame(d).melt("t (ns)", ["Rg of the largest (nm)", "asphericity"], var_name="measure", value_name="value")
    return (alt.Chart(df).mark_line(strokeWidth=2).encode(
        x=alt.X("t (ns):Q", title="time (ns)"), y=alt.Y("value:Q", title=None), color=alt.Color("measure:N", scale=alt.Scale(range=[BLUE, AMBER]), legend=alt.Legend(orient="top", title=None)),
        tooltip=["t (ns)", "measure", alt.Tooltip("value:Q", format=".3f")]).properties(height=height, title="Size and shape of the largest aggregate").interactive())


def free_chart(d: dict, height: int = 220) -> alt.Chart:
    df = series_frame(d)
    return (alt.Chart(df).mark_line(strokeWidth=2, color=PINK).encode(
        x=alt.X("t (ns):Q", title="time (ns)"), y=alt.Y("free fraction:Q", title="share of molecules outside aggregates", scale=alt.Scale(domain=[0, 1])),
        tooltip=["t (ns)", alt.Tooltip("free fraction:Q", format=".2f")]).properties(height=height, title="Free molecules").interactive())


def profile_chart(d: dict, height: int = 240) -> alt.Chart | None:
    p = d.get("profile") or {}
    if not p:
        return None
    df = pd.DataFrame({"r (nm)": p["r"], "chain beads": p["tail"], "head beads": p["head"], "water": p["water"], "ions": p["ion"]})
    long = df.melt("r (nm)", var_name="component", value_name="density (beads/nm3)")
    return (alt.Chart(long).mark_line(strokeWidth=2).encode(
        x=alt.X("r (nm):Q", title="distance from the centre of the aggregate (nm)"), y=alt.Y("density (beads/nm3):Q", title="bead density (per nm3)"),
        color=alt.Color("component:N", scale=alt.Scale(domain=["chain beads", "head beads", "water", "ions"], range=[TEAL, PINK, BLUE, AMBER]), legend=alt.Legend(orient="top", title=None)),
        tooltip=["r (nm)", "component", alt.Tooltip("density (beads/nm3):Q", format=".2f")]).properties(height=height, title="Radial density, second half of the run"))


def summary_table(runs: dict[str, dict]) -> pd.DataFrame:
    rows = []
    for name, d in runs.items():
        s = d["summary"]
        rows.append({"system": name, "molecules": s["molecules"], "ns": s["ns"], "mean aggregate size": s["aggregation_number"], "largest aggregate": s["largest_aggregate"],
                     "aggregates": s["aggregates"], "free share": s["free_fraction"], "Rg (nm)": s["rg_nm"], "asphericity": s["asphericity"], "kappa2": s["kappa2"]})
    return pd.DataFrame(rows)


def bead_table(key: str) -> pd.DataFrame:
    cg = md.coarse_grain(key)
    return pd.DataFrame([{"bead": i + 1, "type": b.type, "meaning": md.LONG[b.type], "heavy atoms": len(b.atoms), "charge": b.charge,
                          "bonded to": ", ".join(str((y if x == i else x) + 1) for x, y in cg.bonds if i in (x, y))} for i, b in enumerate(cg.beads)])


def interaction_table() -> pd.DataFrame:
    eps, sig = md.pair_table()
    t = md.TYPES
    df = pd.DataFrame(eps, index=t, columns=t).astype(float)
    return df
