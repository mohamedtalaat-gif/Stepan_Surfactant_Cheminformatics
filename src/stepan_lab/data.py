# Created by Muhammad Talaat, Faculty of Pharmacy, Ain Shams University
# SPDX-FileCopyrightText: 2026 Muhammad Talaat
# SPDX-License-Identifier: MIT

"""Loaders for the tables in ``data/``.  Every table keeps the deck and page it came from."""

from __future__ import annotations

from functools import cache
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
CHARTS = DATA / "charts"


def _read(name: str, **kw) -> pd.DataFrame:
    return pd.read_csv(DATA / name, **kw)


@cache
def products() -> pd.DataFrame:
    return _read("products.csv")


@cache
def formula_index() -> pd.DataFrame:
    return _read("formula_index.csv", dtype={"reference_no": str, "page": str})


@cache
def formula_lines() -> pd.DataFrame:
    return _read("formula_lines.csv", dtype={"phase": str, "qs": str}).fillna({"phase": "", "qs": "", "inci": "", "note": ""})


@cache
def process_steps() -> pd.DataFrame:
    return _read("process_steps.csv")


@cache
def chart_index() -> pd.DataFrame:
    return pd.read_csv(CHARTS / "_index.csv")


@cache
def chart(chart_id: str) -> pd.DataFrame:
    df = pd.read_csv(CHARTS / f"{chart_id}.csv")
    df["flag"] = df["flag"].astype(object).where(df["flag"].notna(), "")
    return df


def chart_meta(chart_id: str) -> dict:
    row = chart_index().loc[chart_index()["chart_id"] == chart_id]
    if row.empty:
        raise KeyError(chart_id)
    return row.iloc[0].to_dict()


@cache
def survey_tables() -> pd.DataFrame:
    return _read("survey_tables.csv")


@cache
def claims() -> pd.DataFrame:
    return _read("claims.csv")


@cache
def additive_ratings() -> pd.DataFrame:
    return _read("additive_ratings.csv")


@cache
def timeline() -> pd.DataFrame:
    return _read("timeline.csv")


@cache
def slides() -> pd.DataFrame:
    return _read("slides.csv", dtype={"page": int}).fillna("")


@cache
def sources() -> pd.DataFrame:
    return _read("sources.csv")


def formula(formula_id: str) -> tuple[dict, pd.DataFrame]:
    """One formula: its header row and its ingredient lines in printed order."""
    idx = formula_index()
    head = idx.loc[idx["formula_id"] == formula_id]
    if head.empty:
        raise KeyError(formula_id)
    lines = formula_lines()
    return head.iloc[0].to_dict(), lines.loc[lines["formula_id"] == formula_id].sort_values("order").reset_index(drop=True)


def printed_vs_drawn() -> pd.DataFrame:
    """Every value that a slide prints next to a mark, with the value read from the mark itself."""
    rows = []
    for cid in chart_index()["chart_id"]:
        d = chart(cid)
        b = d[d["y_geometry"].notna() & (d["y_source"] == "printed")]
        for r in b.itertuples():
            rows.append({"chart_id": cid, "series": r.series, "x": r.x, "printed": float(r.y), "drawn": float(r.y_geometry)})
    out = pd.DataFrame(rows)
    out["abs_gap"] = (out["printed"] - out["drawn"]).abs()
    out["rel_gap"] = out["abs_gap"] / out["printed"].abs()
    return out
