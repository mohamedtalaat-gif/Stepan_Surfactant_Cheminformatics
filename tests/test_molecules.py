# Created by Muhammad Talaat, Faculty of Pharmacy, Ain Shams University
# SPDX-FileCopyrightText: 2026 Muhammad Talaat
# SPDX-License-Identifier: MIT

import pytest

from stepan_lab import molecules as M


@pytest.mark.parametrize("key", list(M.REGISTRY))
def test_every_structure_parses_and_draws(key):
    assert M.mol(key) is not None
    assert M.draw_svg(key).lstrip().startswith("<?xml") or "<svg" in M.draw_svg(key)


def test_renewable_carbon_shares_follow_from_the_structures():
    assert M.renewable_fraction("slsa") == pytest.approx(12 / 14)
    assert M.renewable_fraction("ninol") == pytest.approx(12 / 14)
    assert M.renewable_fraction("lauramineoxide") == pytest.approx(12 / 14)
    assert M.renewable_fraction("gcc_c8") == 1.0
    assert M.renewable_fraction("l3") == 1.0
    assert M.renewable_fraction("sles2") == pytest.approx(12 / 16)
    assert M.renewable_fraction("cocobetaine") == pytest.approx(12 / 16)


def test_the_printed_indices_match_the_structure_based_shares():
    # printed on the slides: LATHANOL LAL BCI 86-87, NINOL CAA NOI 0.86, AMMONYX LO BCI 86, STEPAN-MILD GCC / L3 BCI 100
    assert abs(100 * M.renewable_fraction("slsa") - 86) < 1.0
    assert abs(M.renewable_fraction("ninol") - 0.86) < 0.01
    assert abs(100 * M.renewable_fraction("lauramineoxide") - 86) < 1.0


def test_descriptors_of_sodium_lauryl_sulfate():
    d = M.descriptors("sls")
    assert d["formula"] == "C12H25NaO4S"
    assert d["mw_formula_unit"] == pytest.approx(288.38, abs=0.05)
    assert d["net_charge"] == -1


def test_the_ester_quat_has_two_chains_and_one_charge():
    d = M.descriptors("eq_b")
    assert d["net_charge"] == 1
    r, t = M.carbon_counts(M.mol("eq_b"))
    assert (r, t) == (32, 40)
