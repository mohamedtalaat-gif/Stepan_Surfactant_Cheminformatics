# Created by Muhammad Talaat, Faculty of Pharmacy, Ain Shams University
# SPDX-FileCopyrightText: 2026 Muhammad Talaat
# SPDX-License-Identifier: MIT

import numpy as np
import pytest

from stepan_lab import data
from stepan_lab import rheology as R


def test_metrics_on_a_known_peak():
    x = np.linspace(0, 6, 121)
    y = 8000 * np.exp(-((x - 3) ** 2) / 1.5)
    m = R.curve_metrics(x, y, target_cp=4000)
    assert m["peak_cP"] == pytest.approx(8000, rel=0.01) and m["salt_at_peak_pct"] == pytest.approx(3.0, abs=0.05)
    assert 1.5 < m["salt_for_target_pct"] < 3.0


def test_the_14_percent_blend_needs_no_salt_to_reach_a_shampoo_viscosity():
    df = data.chart("s3_p10_salt_curves")
    g = df[df["series"] == "14% STEPANBLEND ASF"]
    m = R.curve_metrics(g["x"].astype(float), g["y"].astype(float), target_cp=5000)
    assert m["salt_for_target_pct"] == pytest.approx(0.0, abs=0.01)
    assert 13000 < m["peak_cP"] < 13600


def test_sles_capb_needs_salt():
    df = data.chart("s3_p10_salt_curves")
    g = df[df["series"] == "SLES/CAPB 10% active"]
    m = R.curve_metrics(g["x"].astype(float), g["y"].astype(float), target_cp=5000)
    assert m["salt_for_target_pct"] > 1.0
