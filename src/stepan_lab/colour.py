# Created by Muhammad Talaat, Faculty of Pharmacy, Ain Shams University
# SPDX-FileCopyrightText: 2026 Muhammad Talaat
# SPDX-License-Identifier: MIT

"""CIELAB colour difference, as used for the colour-fading charts (dE in the slides).

The seminar reports dE between a washed tress and the unwashed one, measured with a Hunter Lab
UltraScan VIS (S3 p23) or by L*a*b* measurement (S4).  The slides do not say which dE formula the
instrument software applied, so all three common ones are provided.
"""

from __future__ import annotations

import math

import numpy as np

# D65 reference white, 2 degree observer
_WHITE = np.array([0.95047, 1.0, 1.08883])


def srgb_to_lab(rgb) -> tuple[float, float, float]:
    """sRGB (0-255) to CIE L*a*b* under D65."""
    c = np.asarray(rgb, float) / 255.0
    lin = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    m = np.array([[0.4124564, 0.3575761, 0.1804375], [0.2126729, 0.7151522, 0.0721750], [0.0193339, 0.1191920, 0.9503041]])
    xyz = m @ lin / _WHITE
    f = np.where(xyz > (6 / 29) ** 3, np.cbrt(xyz), xyz / (3 * (6 / 29) ** 2) + 4 / 29)
    return float(116 * f[1] - 16), float(500 * (f[0] - f[1])), float(200 * (f[1] - f[2]))


def lab_to_srgb(lab) -> tuple[int, int, int]:
    L, a, b = lab
    fy = (L + 16) / 116
    f = np.array([fy + a / 500, fy, fy - b / 200])
    xyz = np.where(f > 6 / 29, f**3, 3 * (6 / 29) ** 2 * (f - 4 / 29)) * _WHITE
    m = np.array([[3.2404542, -1.5371385, -0.4985314], [-0.9692660, 1.8760108, 0.0415560], [0.0556434, -0.2040259, 1.0572252]])
    lin = np.clip(m @ xyz, 0, 1)
    c = np.where(lin <= 0.0031308, 12.92 * lin, 1.055 * lin ** (1 / 2.4) - 0.055)
    return tuple(int(round(float(v) * 255)) for v in np.clip(c, 0, 1))


def delta_e76(l1, l2) -> float:
    return float(math.dist(l1, l2))


def delta_e94(l1, l2, kL=1.0, K1=0.045, K2=0.015) -> float:
    """CIE94 (graphic arts weights); l1 is the reference."""
    L1, a1, b1 = l1
    L2, a2, b2 = l2
    C1, C2 = math.hypot(a1, b1), math.hypot(a2, b2)
    dL, dC = L1 - L2, C1 - C2
    da, db = a1 - a2, b1 - b2
    dH2 = max(da * da + db * db - dC * dC, 0.0)
    sC, sH = 1 + K1 * C1, 1 + K2 * C1
    return math.sqrt((dL / kL) ** 2 + (dC / sC) ** 2 + dH2 / sH**2)


def delta_e2000(l1, l2, kL=1.0, kC=1.0, kH=1.0) -> float:
    """CIEDE2000 following Sharma, Wu and Dalal (2005) Color Res. Appl. 30, 21."""
    L1, a1, b1 = l1
    L2, a2, b2 = l2
    C1, C2 = math.hypot(a1, b1), math.hypot(a2, b2)
    Cm = (C1 + C2) / 2
    G = 0.5 * (1 - math.sqrt(Cm**7 / (Cm**7 + 25**7)))
    a1p, a2p = (1 + G) * a1, (1 + G) * a2
    C1p, C2p = math.hypot(a1p, b1), math.hypot(a2p, b2)
    h1p = math.degrees(math.atan2(b1, a1p)) % 360
    h2p = math.degrees(math.atan2(b2, a2p)) % 360
    dLp, dCp = L2 - L1, C2p - C1p
    if C1p * C2p == 0:
        dhp = 0.0
    else:
        d = h2p - h1p
        dhp = d - 360 if d > 180 else d + 360 if d < -180 else d
    dHp = 2 * math.sqrt(C1p * C2p) * math.sin(math.radians(dhp / 2))
    Lpm, Cpm = (L1 + L2) / 2, (C1p + C2p) / 2
    if C1p * C2p == 0:
        hpm = h1p + h2p
    elif abs(h1p - h2p) <= 180:
        hpm = (h1p + h2p) / 2
    else:
        hpm = (h1p + h2p + 360) / 2 if h1p + h2p < 360 else (h1p + h2p - 360) / 2
    T = (1 - 0.17 * math.cos(math.radians(hpm - 30)) + 0.24 * math.cos(math.radians(2 * hpm))
         + 0.32 * math.cos(math.radians(3 * hpm + 6)) - 0.20 * math.cos(math.radians(4 * hpm - 63)))
    dtheta = 30 * math.exp(-(((hpm - 275) / 25) ** 2))
    Rc = 2 * math.sqrt(Cpm**7 / (Cpm**7 + 25**7))
    Sl = 1 + 0.015 * (Lpm - 50) ** 2 / math.sqrt(20 + (Lpm - 50) ** 2)
    Sc, Sh = 1 + 0.045 * Cpm, 1 + 0.015 * Cpm * T
    Rt = -math.sin(math.radians(2 * dtheta)) * Rc
    return math.sqrt((dLp / (kL * Sl)) ** 2 + (dCp / (kC * Sc)) ** 2 + (dHp / (kH * Sh)) ** 2
                     + Rt * (dCp / (kC * Sc)) * (dHp / (kH * Sh)))


def perceptibility(de: float) -> str:
    """The reading rule printed on S3 p23: below 1 imperceptible, above 3 clearly visible."""
    if de < 1:
        return "typically imperceptible"
    if de <= 3:
        return "between the slide's two thresholds (1 and 3)"
    return "clearly visible difference"
