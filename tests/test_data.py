# Created by Muhammad Talaat, Faculty of Pharmacy, Ain Shams University
# SPDX-FileCopyrightText: 2026 Muhammad Talaat
# SPDX-License-Identifier: MIT

import hashlib
from pathlib import Path

import pandas as pd
import pytest

from stepan_lab import data, molecules

ROOT = Path(__file__).resolve().parents[1]


def test_every_slide_of_every_deck_is_in_the_ledger():
    s = data.slides()
    assert len(s) == 164
    assert s.groupby("deck").size().to_dict() == {"S1": 39, "S2": 29, "S3": 26, "S4": 26, "S6": 12, "S7": 32}
    assert not s.duplicated(["deck", "page"]).any()
    for deck, g in s.groupby("deck"):
        assert sorted(g["page"]) == list(range(1, len(g) + 1))


def test_slide_references_resolve():
    charts = set(data.chart_index()["chart_id"])
    formulas = set(data.formula_index()["formula_id"])
    products = set(data.products()["product_id"])
    tables = set(data.survey_tables()["table_id"]) | {"additive_ratings"}
    for r in data.slides().itertuples():
        for ref in [x for x in str(r.refs).split(";") if x]:
            kind, _, key = ref.partition(":")
            if kind == "chart":
                assert key in charts, (r.deck, r.page, ref)
            elif kind == "formula":
                assert key in formulas, (r.deck, r.page, ref)
            elif kind == "product":
                assert key in products, (r.deck, r.page, ref)
            elif kind == "table":
                assert key in tables, (r.deck, r.page, ref)
            else:
                assert kind in {"timeline", "claim"}, ref


def test_formula_lines_belong_to_known_formulas():
    idx = set(data.formula_index()["formula_id"])
    lines = data.formula_lines()
    assert set(lines["formula_id"]) == idx
    assert data.formula_index()["formula_id"].is_unique
    for fid, g in lines.groupby("formula_id"):
        assert list(g["order"]) == list(range(1, len(g) + 1)), fid


def test_every_formula_with_printed_percentages_closes_or_is_flagged():
    from stepan_lab import formulation as F

    odd = {}
    for fid in data.formula_index()["formula_id"]:
        _, lines = data.formula(fid)
        chk = F.check_sum(lines)
        if not chk["closes"]:
            odd[fid] = chk["fixed_total"]
    # printed totals that do not close, kept as printed (see data/formula_index.csv notes)
    assert odd == {"s7_serum": 100.1, "s7_solidbar": 101.0}


def test_product_ids_unique_and_structures_point_at_real_products():
    p = data.products()
    assert p["product_id"].is_unique
    known = set(p["product_id"])
    for s in molecules.REGISTRY.values():
        for pid in s.products:
            assert pid in known, (s.key, pid)


def test_chart_files_match_the_index_and_have_values():
    idx = data.chart_index()
    for r in idx.itertuples():
        df = data.chart(r.chart_id)
        assert len(df) == r.rows, r.chart_id
        assert pd.to_numeric(df["y"], errors="coerce").notna().all(), r.chart_id
        assert df["series"].notna().all()


@pytest.mark.skipif(not (ROOT / "references" / "source_decks").exists(), reason="decks are not shipped with the repository")
def test_source_checksums_match_the_decks():
    src = data.sources()
    for r in src.itertuples():
        f = ROOT / "references" / "source_decks" / r.file
        if f.exists():
            assert hashlib.sha256(f.read_bytes()).hexdigest() == r.sha256


def test_the_readme_table_matches_the_data():
    import re
    from pathlib import Path

    from stepan_lab import data, molecules

    text = (Path(__file__).resolve().parents[1] / "README.md").read_text(encoding="utf-8")
    row = lambda label: int(re.search(rf"\| {label}[^|]*\| (\d+)", text).group(1))
    assert row("Slides recorded") == len(data.slides())
    assert row("Charts rebuilt") == len(data.chart_index())
    assert row("Formulas transcribed") == len(data.formula_index())
    assert row("Products registered") == len(data.products())
    assert row("Structures drawn") == len(molecules.REGISTRY)
    n = len(list((Path(__file__).resolve().parents[1] / "notebooks").glob("*.py")))
    assert n == 13 and "and six labs" in text


def test_the_stored_decks_carry_no_personal_details():
    import csv
    import re
    from pathlib import Path

    import pymupdf

    root = Path(__file__).resolve().parents[1]
    files = {r["deck"]: r["file"] for r in csv.DictReader((root / "data" / "sources.csv").open(encoding="utf-8", newline=""))}
    ledger = list(csv.DictReader((root / "data" / "slides.csv").open(encoding="utf-8", newline="")))
    withheld = {(r["deck"], int(r["page"])) for r in ledger if r["kind"] in ("internal", "contacts")}
    assert len(withheld) == 6
    for pdf in sorted((root / "references" / "source_decks").glob("*.pdf")):
        assert pdf.name in files.values(), pdf.name  # every stored deck is registered: no stray copies
    for deck, name in files.items():
        doc = pymupdf.open(root / "references" / "source_decks" / name)
        assert not doc.metadata.get("author") and not doc.metadata.get("keywords") and not doc.metadata.get("subject")
        for number, page in enumerate(doc, 1):
            text = page.get_text()
            assert not re.search(r"[\w.+-]+@[\w-]+\.[\w.-]+", text), (deck, number)
            if (deck, number) in withheld:
                assert text.startswith("Page withheld in this copy") and not page.get_images(), (deck, number)
            else:
                assert not text.startswith("Page withheld"), (deck, number)
