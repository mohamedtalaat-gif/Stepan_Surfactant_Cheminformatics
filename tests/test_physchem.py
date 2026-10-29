# Created by Muhammad Talaat, Faculty of Pharmacy, Ain Shams University
# SPDX-FileCopyrightText: 2026 Muhammad Talaat
# SPDX-License-Identifier: MIT


import pytest

from stepan_lab import molecules as M
from stepan_lab import physchem as P


def test_sodium_dodecyl_sulfate_sits_at_the_sphere_rod_boundary():
    p = P.packing_parameter(12, 62)
    assert p == pytest.approx(1 / 3, abs=0.01)
    assert P.chain_volume_A3(12) == pytest.approx(350.2) and P.chain_length_A(12) == pytest.approx(16.68)


def test_a_smaller_head_group_raises_the_packing_parameter():
    assert P.packing_parameter(12, 45) > P.packing_parameter(12, 62)
    mix = P.mixed_packing_parameter([(0.67, 14, 57), (0.33, 12, 48)])
    assert mix > P.packing_parameter(14, 57)


def test_klevens_line_reproduces_its_own_data_and_extrapolates_sensibly():
    a, b = P.klevens_fit()
    assert P.klevens_cmc_mM(12, a, b) == pytest.approx(8.2, rel=0.08)
    assert 0.3 < P.klevens_cmc_mM(16, a, b) < 0.8
    assert 0.28 < b < 0.32


def test_debye_length_of_a_tenth_molar_salt():
    assert P.debye_length_nm(0.1) == pytest.approx(0.96, abs=0.01)
    assert P.debye_length_nm(1.0) < P.debye_length_nm(0.01)


def test_one_percent_salt_is_about_a_sixth_molar():
    assert P.salt_wt_pct_to_molar(1.0) == pytest.approx(0.171, abs=0.001)


def test_laplace_pressure_and_ripening_gap():
    assert P.laplace_pressure_Pa(30, 74) == pytest.approx(811, abs=2)
    assert P.ripening_pressure_gap_Pa(30, 74, 95) > 0


def test_foam_half_life_decay():
    assert P.foam_remaining(500, 500) == pytest.approx(0.5)
    assert P.foam_remaining(0, 500) == 1.0


def test_griffin_hlb_of_steareth_20():
    mw = M.descriptors("steareth20")["mw_formula_unit"]
    assert P.hlb_griffin_ethoxylate(20, mw) == pytest.approx(15.3, abs=0.2)


def test_protonation_is_half_at_the_pka():
    assert P.fraction_protonated(6.5, 6.5) == pytest.approx(0.5)
    assert P.fraction_protonated(3, 6.5) > 0.99
