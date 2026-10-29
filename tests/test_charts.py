# Created by Muhammad Talaat, Faculty of Pharmacy, Ain Shams University
# SPDX-FileCopyrightText: 2026 Muhammad Talaat
# SPDX-License-Identifier: MIT

import numpy as np
import pytest

from stepan_lab import charts, data


def val(chart_id, series, x):
    df = data.chart(chart_id)
    return float(df[(df["series"] == series) & (df["x"].astype(str) == str(x))]["y"].iloc[0])


def test_printed_values_agree_with_the_drawn_geometry():
    for cid in data.chart_index()["chart_id"]:
        df = data.chart(cid)
        both = df[df["y_geometry"].notna() & (df["y_source"] == "printed")]
        for r in both.itertuples():
            span = float(r.y) if float(r.y) else 1.0
            assert abs(float(r.y) - float(r.y_geometry)) <= max(0.02 * abs(span), 0.8), (cid, r.series, r.x, r.y, r.y_geometry)


def test_percentages_printed_on_s3_are_reproduced_from_the_digitised_bars():
    sulf = val("s3_p23_fade", "Commercial sulfated shampoo", "15 washes")
    free = val("s3_p23_fade", "Commercial sulfate-free shampoo", "15 washes")
    asf = val("s3_p23_fade", "STEPANBLEND ASF (14% solids)", "15 washes")
    assert abs(100 * (sulf - asf) / sulf - 32) < 1.0
    assert abs(100 * (free - asf) / free - 8) < 1.0
    sles = val("s3_p19_combing", "Combing force (gf)", "SLES/CAPB 14% (active ratio 2:1)")
    blend = val("s3_p19_combing", "Combing force (gf)", "STEPANBLEND ASF/MB")
    assert abs(100 * (sles - blend) / sles - 65) < 1.5


def test_delta_e_error_bars_are_all_one_unit():
    for cid in ("s4_p09_fade_primary", "s4_p14_fade_secondary", "s4_p17_fade_ammonyx", "s4_p20_fade_prototype", "s4_p25_fade_nextgen"):
        df = data.chart(cid)
        err = df[df["series"] == "dE error bar half-length"]["y"].astype(float)
        assert len(err) and np.allclose(err, 1.0, atol=0.03), cid


def test_the_s3_salt_curve_keeps_the_stretch_hidden_behind_the_legend():
    df = data.chart("s3_p10_salt_curves")
    sles = df[df["series"] == "SLES/CAPB 10% active"]
    assert float(sles["x"].astype(float).max()) == pytest.approx(5.0, abs=0.01)
    assert float(sles[sles["x"].astype(float) > 4.9]["y"].iloc[-1]) == pytest.approx(8550, abs=120)


def test_sensory_radar_is_clockwise_from_the_top():
    df = data.chart("s2_p10_foam_sensory")
    pc = df[df["series"] == "Sensory: ALPHA-STEP PC-48"].set_index("x")["y"].astype(float)
    sl = df[df["series"] == "Sensory: Sodium Laureth Sulfate"].set_index("x")["y"].astype(float)
    assert pc["Speed of foam"] > 4.0 and sl["Speed of foam"] < 3.5
    assert sl["Creaminess"] > 3.5 and abs(pc["Creaminess"] - sl["Creaminess"]) < 0.5


@pytest.mark.parametrize("cid", list(data.chart_index()["chart_id"]))
def test_every_chart_renders(cid):
    out = charts.render(cid)
    for ch in (out if isinstance(out, list) else [out]):
        assert ch.to_dict()
