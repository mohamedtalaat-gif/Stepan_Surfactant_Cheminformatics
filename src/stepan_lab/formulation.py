# Created by Muhammad Talaat, Faculty of Pharmacy, Ain Shams University
# SPDX-FileCopyrightText: 2026 Muhammad Talaat
# SPDX-License-Identifier: MIT

"""Formulation arithmetic: batch scaling, q.s. handling, actives, naturality and dilution.

All of it is arithmetic on the percentages printed in the decks.  Nothing here predicts viscosity,
stability, mildness or sensory performance of a changed formula.
"""

from __future__ import annotations

import re

import numpy as np
import pandas as pd

from . import data


def _num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return np.nan


def resolve(lines: pd.DataFrame) -> pd.DataFrame:
    """Add a numeric ``pct`` column: the printed w/w percentage, or the remainder for 'q.s. to 100'."""
    df = lines.copy()
    df["pct"] = df["pct_ww"].map(_num)
    to100 = df["qs"] == "to100"
    if to100.sum() == 1:
        df.loc[to100, "pct"] = 100.0 - df.loc[~to100, "pct"].sum(skipna=True)
    df["trace"] = df["pct"].isna()
    return df


def check_sum(lines: pd.DataFrame) -> dict:
    """Total of the fixed percentages and what the q.s. water or a rounding gap leaves."""
    df = lines.copy()
    df["pct"] = df["pct_ww"].map(_num)
    fixed = float(df.loc[df["qs"] != "to100", "pct"].sum(skipna=True))
    has_qs_water = bool((df["qs"] == "to100").any())
    if has_qs_water:
        status = f"q.s. water closes the formula at {100 - fixed:.2f}%"
    elif abs(fixed - 100) < 0.051:
        status = "adds up to 100"
    else:
        status = f"adds up to {fixed:.2f}, not 100"
    return {"fixed_total": round(fixed, 4), "water_remainder": round(100 - fixed, 4) if has_qs_water else None,
            "closes": has_qs_water or abs(fixed - 100) < 0.051, "status": status,
            "trace_items": int(df["pct"].isna().sum() - int(has_qs_water))}


def scale_batch(lines: pd.DataFrame, batch_g: float) -> pd.DataFrame:
    """Grams for a batch.  Trace items (q.s. dye, pH adjusters) stay blank rather than being guessed."""
    df = resolve(lines)
    df["grams"] = df["pct"] * batch_g / 100.0
    return df


# -- actives --------------------------------------------------------------------------------------

def _norm(s: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", s.upper().replace("®", ""))


def match_product(ingredient: str, products: pd.DataFrame | None = None) -> str | None:
    """Product id whose trade name appears in the ingredient text, preferring the longest match."""
    products = data.products() if products is None else products
    text = _norm(ingredient)
    best, size = None, 0
    for _, r in products.iterrows():
        for name in {r["trade_name"], r["trade_name"].split(" (")[0], r["trade_name"].split(" / ")[0]}:
            n = _norm(name)
            if n and n in text and len(n) > size:
                best, size = r["product_id"], len(n)
    return best


def actives_table(lines: pd.DataFrame, products: pd.DataFrame | None = None) -> pd.DataFrame:
    """Active matter per ingredient: the printed 'active' column where the slide has one, otherwise
    the product's printed active content, otherwise unknown."""
    products = data.products() if products is None else products
    df = resolve(lines)
    pid = df["ingredient"].map(lambda s: match_product(s, products))
    df["product_id"] = pid
    pmap = products.set_index("product_id")
    df["product_active_pct"] = pid.map(lambda k: pmap["active_pct"].get(k, np.nan) if k else np.nan)
    df["charge"] = pid.map(lambda k: pmap["charge"].get(k, "") if k else "")
    printed = df["pct_active"].map(_num)
    from_product = df["pct"] * df["product_active_pct"] / 100.0
    df["active_pct_in_formula"] = printed.where(printed.notna(), from_product)
    df["active_source"] = np.where(printed.notna(), "printed on the slide", np.where(from_product.notna(), "product active content", ""))
    return df


def charge_split(lines: pd.DataFrame) -> pd.Series:
    """Active matter by charge class (anionic, amphoteric, nonionic, cationic) where it can be known."""
    t = actives_table(lines)
    t = t[t["active_pct_in_formula"].notna() & (t["charge"] != "")]
    cls = t["charge"].str.split(" ").str[0].replace({"nonionic": "nonionic"})
    return t.groupby(cls)["active_pct_in_formula"].sum()


# -- naturality (ISO 16128 as Stepan uses it) -------------------------------------------------------

def chassis_naturality(lines: pd.DataFrame, noc: dict[str, float], default: float = 1.0) -> float:
    """Sum of (w/w fraction x natural origin content) over the formula, as the S1 and S3 footnotes define it.

    ``noc`` maps a product id to its index; any ingredient without an entry is given ``default``.
    The slides treat water as 1.  The calculation is only as good as the indices supplied.
    """
    df = resolve(lines)
    total = 0.0
    for _, r in df.iterrows():
        if np.isnan(r["pct"]):
            continue
        pid = match_product(r["ingredient"])
        total += r["pct"] / 100.0 * noc.get(pid, default)
    return total


def dilute_naturality(concentrate_noc: float, concentrate_fraction: float, diluent_noc: float = 1.0) -> float:
    """NOC after diluting a concentrate (S2 p22: 1 part concentrate with 3 parts tap water)."""
    return concentrate_fraction * concentrate_noc + (1 - concentrate_fraction) * diluent_noc


def implied_blend_actives(blend_pct: float, target_actives_pct: float) -> float:
    """Active share of a blend implied by a formula that states both its blend level and its actives."""
    return target_actives_pct / blend_pct * 100.0


def naturality_report(lines: pd.DataFrame, noc: dict[str, float], default: float = 1.0) -> dict:
    """Chassis naturality together with the ingredients that had to fall back on the default index."""
    df = resolve(lines)
    assumed = []
    for _, r in df.iterrows():
        if not np.isnan(r["pct"]) and r["pct"] > 0 and match_product(r["ingredient"]) not in noc:
            assumed.append(r["ingredient"])
    return {"score": chassis_naturality(lines, noc, default), "assumed": assumed}


def compare(lines_a: pd.DataFrame, lines_b: pd.DataFrame) -> pd.DataFrame:
    """Two formulas side by side by ingredient name; a name that occurs twice in one formula is summed."""
    def col(df):
        d = df.copy()
        d["pct"] = d["pct_ww"].map(_num)
        return d.groupby("ingredient", sort=False)["pct"].sum(min_count=1)

    both = pd.concat([col(lines_a).rename("A (% w/w)"), col(lines_b).rename("B (% w/w)")], axis=1).reset_index()
    both = both.rename(columns={"index": "ingredient"})
    both["difference B - A"] = (both["B (% w/w)"].fillna(0) - both["A (% w/w)"].fillna(0)).round(3)
    return both
