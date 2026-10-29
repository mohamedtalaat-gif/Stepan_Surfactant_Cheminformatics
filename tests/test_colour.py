# Created by Muhammad Talaat, Faculty of Pharmacy, Ain Shams University
# SPDX-FileCopyrightText: 2026 Muhammad Talaat
# SPDX-License-Identifier: MIT

import pytest

from stepan_lab import colour as K

# Sharma, Wu and Dalal (2005), Color Res. Appl. 30, 21: first three test pairs
PAIRS = [((50.0, 2.6772, -79.7751), (50.0, 0.0, -82.7485), 2.0425),
         ((50.0, 3.1571, -77.2803), (50.0, 0.0, -82.7485), 2.8615),
         ((50.0, 2.8361, -74.0200), (50.0, 0.0, -82.7485), 3.4412)]


@pytest.mark.parametrize("l1,l2,expected", PAIRS)
def test_ciede2000_matches_the_published_test_pairs(l1, l2, expected):
    assert K.delta_e2000(l1, l2) == pytest.approx(expected, abs=1e-4)


def test_cie76_is_euclidean_and_cie94_does_not_exceed_it():
    a, b = (50, 20, 10), (55, 25, 5)
    assert K.delta_e76(a, b) == pytest.approx((25 + 25 + 25) ** 0.5)
    assert K.delta_e94(a, b) <= K.delta_e76(a, b)


def test_srgb_round_trip_and_white_point():
    L, a, b = K.srgb_to_lab((255, 255, 255))
    assert L == pytest.approx(100, abs=0.01) and abs(a) < 0.01 and abs(b) < 0.01
    assert K.lab_to_srgb(K.srgb_to_lab((200, 30, 40))) == (200, 30, 40)


def test_reading_rule_of_the_slide():
    assert "imperceptible" in K.perceptibility(0.5)
    assert "clearly" in K.perceptibility(3.5)
