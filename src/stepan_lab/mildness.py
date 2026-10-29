# Created by Muhammad Talaat, Faculty of Pharmacy, Ain Shams University
# SPDX-FileCopyrightText: 2026 Muhammad Talaat
# SPDX-License-Identifier: MIT

"""Skin-irritation scales printed in the seminar."""

from __future__ import annotations

# S3 p21: M.C.I.I. (mean cumulative irritation index) classes for a 48 h occlusive patch test
MCII_CLASSES = [
    (0.25, "Non irritating (NI)"),
    (0.50, "Very slightly irritating (VSI)"),
    (1.0, "Slightly irritating (SI)"),
    (2.0, "Moderately irritating (MI)"),
    (float("inf"), "Irritating (I)"),
]


def mcii_class(value: float) -> str:
    for upper, label in MCII_CLASSES:
        if value < upper:
            return label
    return MCII_CLASSES[-1][1]


def zein_relative(score: float, reference: float = 100.0) -> float:
    """Zein scores are normalised so that sodium lauryl sulfate scores 100; lower is milder."""
    return score / reference


def percent_milder(score: float, reference_score: float) -> float:
    """How much lower the score is than a reference score, in percent."""
    return 100.0 * (reference_score - score) / reference_score
