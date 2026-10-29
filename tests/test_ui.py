# Created by Muhammad Talaat, Faculty of Pharmacy, Ain Shams University
# SPDX-FileCopyrightText: 2026 Muhammad Talaat
# SPDX-License-Identifier: MIT

"""Every option the notebooks offer in a drop-down is exercised here, so that choosing a different formula,
chart, slide or product cannot fail for the first time in front of a reader."""

import pytest

from stepan_lab import data, formulation, molecules, ui

FORMULAS = list(data.formula_index()["formula_id"])
CHARTS = list(data.chart_index()["chart_id"])
SLIDES = [(r.deck, int(r.page)) for r in data.slides().itertuples()]
PRODUCTS = list(data.products()["product_id"])


@pytest.mark.parametrize("fid", FORMULAS)
def test_every_formula_can_be_shown_scaled_and_analysed(fid):
    _, lines = data.formula(fid)
    ui.formula_card(fid, 750)
    formulation.check_sum(lines)
    formulation.scale_batch(lines, 500)
    formulation.actives_table(lines)
    formulation.charge_split(lines)
    rep = formulation.naturality_report(lines, {"asfmb": 0.81}, 1.0)
    assert 0 <= rep["score"] <= 1.011  # two formulas print totals of 100.1 and 101.0


@pytest.mark.parametrize("fid", FORMULAS)
def test_every_formula_can_be_compared_with_one_that_repeats_an_ingredient(fid):
    a = data.formula(fid)[1]
    b = data.formula("s7_2in1")[1]  # citric acid appears twice
    out = formulation.compare(a, b)
    assert out["ingredient"].is_unique


@pytest.mark.parametrize("cid", CHARTS)
def test_every_chart_card_builds(cid):
    ui.chart_card(cid)


@pytest.mark.parametrize("deck,page", SLIDES)
def test_every_slide_opens_with_its_data(deck, page):
    ui.slide_cards(deck, page)


@pytest.mark.parametrize("pid", PRODUCTS)
def test_every_product_card_builds(pid):
    ui.product_card(pid)


@pytest.mark.parametrize("key", list(molecules.REGISTRY))
def test_every_structure_card_builds(key):
    ui.structure_card(key)


def test_survey_tables_and_walkthroughs_build():
    for tid in set(data.survey_tables()["table_id"]) | {"additive_ratings"}:
        ui.survey_table_card(tid)
    for deck in data.slides()["deck"].unique():
        ui.slide_walkthrough(deck)
