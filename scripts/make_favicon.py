# Created by Muhammad Talaat, Faculty of Pharmacy, Ain Shams University
# SPDX-FileCopyrightText: 2026 Muhammad Talaat
# SPDX-License-Identifier: MIT
"""Draw the icon of the interactive page: a micelle, with chains pointing to the centre and the head groups outside.

    python scripts/make_favicon.py      # writes docs/card/favicon.png (64 px) and docs/card/apple-touch-icon.png (180 px)
"""

from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw

CARD = Path(__file__).resolve().parents[1] / "docs" / "card"
BG, LINE, TAIL, HEAD = (11, 16, 32), (53, 208, 186), (53, 208, 186), (255, 122, 144)


def draw(size: int) -> Image.Image:
    k = 8  # supersampling
    s = size * k
    im = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, s - 1, s - 1], int(0.22 * s), fill=BG + (255,), outline=LINE + (255,), width=max(2, int(0.035 * s)))
    c = s / 2
    chains = 9
    for i in range(chains):
        a = 2 * math.pi * i / chains + math.pi / chains
        for r, rad, col in ((0.105, 0.058, TAIL), (0.205, 0.062, TAIL), (0.325, 0.082, HEAD)):
            x, y = c + r * s * math.cos(a), c + r * s * math.sin(a)
            d.ellipse([x - rad * s, y - rad * s, x + rad * s, y + rad * s], fill=col + (255,))
    return im.resize((size, size), Image.Resampling.LANCZOS)


if __name__ == "__main__":
    draw(64).save(CARD / "favicon.png", optimize=True)
    draw(180).save(CARD / "apple-touch-icon.png", optimize=True)
    print("wrote", CARD / "favicon.png", CARD / "apple-touch-icon.png")
