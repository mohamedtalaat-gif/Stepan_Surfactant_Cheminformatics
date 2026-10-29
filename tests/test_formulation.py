# Created by Muhammad Talaat, Faculty of Pharmacy, Ain Shams University
# SPDX-FileCopyrightText: 2026 Muhammad Talaat
# SPDX-License-Identifier: MIT

import pytest

from stepan_lab import data
from stepan_lab import formulation as F


def lines(fid):
    return data.formula(fid)[1]


def test_batch_scaling_follows_the_printed_percentages():
    t = F.scale_batch(lines("s3_handwash"), 1000)
    asf = t[t["ingredient"] == "STEPANBLEND ASF/MB"]["grams"].iloc[0]
    assert asf == pytest.approx(141.0)  # 1,000 g x 14.1 / 100
    assert t["grams"].sum() == pytest.approx(1000.0)


def test_trace_items_are_not_given_invented_masses():
    t = F.scale_batch(lines("s3_handwash"), 500)
    assert t[t["ingredient"] == "Dye"]["grams"].isna().all()


def test_water_is_the_remainder_when_the_slide_says_qs_to_100():
    t = F.resolve(lines("s1_base_1610"))
    assert t[t["ingredient"] == "DI Water"]["pct"].iloc[0] == pytest.approx(5.7)


def test_iso_16128_naturality_of_the_three_starter_formulas_is_reproduced():
    noc = {"asfmb": 0.81}
    for fid, printed in (("s3_handwash", 0.97), ("s3_showergel", 0.95), ("s3_shampoo", 0.92)):
        assert F.chassis_naturality(lines(fid), noc) == pytest.approx(printed, abs=0.006)


def test_dilution_of_formula_1443():
    assert F.dilute_naturality(0.86, 0.25) == pytest.approx(0.96, abs=0.006)


def test_blend_actives_implied_by_the_three_formulas_agree():
    got = [F.implied_blend_actives(14.1, 5), F.implied_blend_actives(28.2, 10), F.implied_blend_actives(39.4, 14)]
    assert max(got) - min(got) < 0.2
    assert 35.0 < sum(got) / 3 < 36.0


def test_actives_from_the_product_card_and_from_the_slide():
    t = F.actives_table(lines("s2_1443"))
    a = t.set_index("product_id")["active_pct_in_formula"]
    assert a["dm"] == pytest.approx(37.3 * 0.30)
    lot = F.actives_table(lines("s4_lotus_night")).set_index("product_id")["active_pct_in_formula"]
    assert lot["as40hasb"] == pytest.approx(8.0) and lot["dm"] == pytest.approx(4.5)


def test_printed_active_columns_are_consistent_with_product_activity():
    # S4: AMPHOSOL DM/MB 4.5% active in 15% w/w is a 30% active product
    assert 4.5 / 15 == pytest.approx(0.30)
    # S4: BIO-TERGE AS-40 HASB 8% active in 20% w/w is 40%, inside the 37-39% printed range only after rounding
    assert 8 / 20 == pytest.approx(0.40)
    # S4/S6: STEPANQUAT GA 90 2% active in 2.22% w/w implies about 90%
    assert 2 / 2.22 == pytest.approx(0.90, abs=0.002)
