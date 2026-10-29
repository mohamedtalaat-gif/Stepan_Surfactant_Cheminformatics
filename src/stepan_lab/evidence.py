# Created by Muhammad Talaat, Faculty of Pharmacy, Ain Shams University
# SPDX-FileCopyrightText: 2026 Muhammad Talaat
# SPDX-License-Identifier: MIT

"""The four kinds of statement the lab makes, and how each one is labelled on screen.

A number in this project is always one of: printed on a slide (reported), read from a drawing or a
picture on a slide (digitised), calculated from reported numbers (derived), or produced by a textbook
model that is not part of the seminar (modelled).  Keeping the four apart is what stops a calculation
from being mistaken for a measurement.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Kind:
    key: str
    label: str
    colour: str
    meaning: str


KINDS = {
    "reported": Kind("reported", "Reported", "#2b6a4f", "Printed on a slide, in a table or as a data label."),
    "digitised": Kind("digitised", "Digitised", "#245b8f", "Read from the geometry of a chart or from a picture on a slide; the resolution is stated."),
    "derived": Kind("derived", "Derived", "#8a5a00", "Arithmetic on reported numbers; nothing new was measured."),
    "modelled": Kind("modelled", "Modelled", "#7a2f6b", "Output of a textbook model that is not part of the seminar; the parameters are assumptions you can change."),
}


def badge(kind: str) -> str:
    """Small inline label as an HTML string."""
    k = KINDS[kind]
    return (
        f'<span style="display:inline-block;padding:1px 8px;border-radius:10px;font-size:0.78em;'
        f'font-weight:600;color:#fff;background:{k.colour}" title="{k.meaning}">{k.label}</span>'
    )


def legend_html() -> str:
    rows = "".join(f"<li>{badge(k)} {v.meaning}</li>" for k, v in KINDS.items())
    return f'<ul style="list-style:none;padding-left:0;line-height:2">{rows}</ul>'
