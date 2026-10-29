# Created by Muhammad Talaat, Faculty of Pharmacy, Ain Shams University
# SPDX-FileCopyrightText: 2026 Muhammad Talaat
# SPDX-License-Identifier: MIT

"""Physical chemistry of surfactant aggregation, foam and electrolytes.

Everything here is a textbook model with its origin named.  None of it is part of the seminar: the
outputs are labelled *modelled* in the notebooks and the assumptions (head-group areas, surface
tension, apparent pKa) are inputs the reader can change.
"""

from __future__ import annotations

import math

import numpy as np
from scipy import constants as C

# ---------------------------------------------------------------------------------------------
# Hydrocarbon chain geometry and the critical packing parameter
# Tanford, C. (1972) J. Phys. Chem. 76, 3020; Israelachvili, Mitchell and Ninham (1976) J. Chem. Soc.
# Faraday Trans. 2, 72, 1525.
# ---------------------------------------------------------------------------------------------

def chain_volume_A3(n_c: float) -> float:
    """Volume of a saturated hydrocarbon chain of n_c carbons, in cubic angstrom (Tanford)."""
    return 27.4 + 26.9 * n_c


def chain_length_A(n_c: float) -> float:
    """Fully extended chain length in angstrom (Tanford)."""
    return 1.5 + 1.265 * n_c


def packing_parameter(n_c: float, a0_A2: float, n_chains: int = 1) -> float:
    """P = v / (a0 * lc).  Dimensionless; a0 is the head-group area at the aggregate surface.

    ``n_chains`` counts the hydrocarbon chains that share one head group (two for an ester quat)."""
    return n_chains * chain_volume_A3(n_c) / (a0_A2 * chain_length_A(n_c))


def aggregate_shape(p: float) -> str:
    if abs(p - 1 / 3) < 0.02:
        return "at the sphere-to-rod boundary (P close to 1/3)"
    if p < 1 / 3:
        return "spherical micelles"
    if p < 1 / 2:
        return "cylindrical (rod-like) micelles"
    if p < 1.0:
        return "vesicles or flexible bilayers"
    if p < 1.3:
        return "planar bilayers (lamellar)"
    return "inverted structures"


def mixed_packing_parameter(components: list[tuple[float, float, float]]) -> float:
    """Packing parameter of a mixed aggregate by mole-fraction averaging.

    ``components`` is a list of (mole fraction, chain carbons, head-group area in square angstrom) and an
    optional fourth entry, the number of chains per head group (default 1).
    This is the simple ideal-mixing estimate: volumes, lengths and areas are averaged linearly.
    """
    x = np.array([c[0] for c in components], float)
    x = x / x.sum()
    v = float(np.dot(x, [(c[3] if len(c) > 3 else 1) * chain_volume_A3(c[1]) for c in components]))
    l = float(np.dot(x, [chain_length_A(c[1]) for c in components]))
    a = float(np.dot(x, [c[2] for c in components]))
    return v / (a * l)


def micelle_radius_nm(n_c: float) -> float:
    """Radius of a spherical micelle core, bounded by the extended chain length."""
    return chain_length_A(n_c) / 10.0


def aggregation_number_sphere(n_c: float, a0_A2: float) -> float:
    """Aggregation number of a sphere whose core radius equals the extended chain length."""
    r = chain_length_A(n_c)
    return 4 * math.pi * r * r / a0_A2


# ---------------------------------------------------------------------------------------------
# Critical micelle concentration
# Klevens, H. B. (1953) J. Am. Oil Chem. Soc. 30, 74: log10 CMC = A - B n, linear in chain length.
# The four points are the textbook values for sodium n-alkyl sulfates in water at 25 C
# (Mukerjee and Mysels, 1971, NSRDS-NBS 36).
# ---------------------------------------------------------------------------------------------

SODIUM_ALKYL_SULFATE_CMC_MM = {8: 136.0, 10: 33.0, 12: 8.2, 14: 2.1}


def klevens_fit(data: dict[int, float] | None = None) -> tuple[float, float]:
    """Least-squares (A, B) of log10(CMC / mol per litre) = A - B n."""
    data = data or SODIUM_ALKYL_SULFATE_CMC_MM
    n = np.array(sorted(data), float)
    y = np.log10(np.array([data[int(k)] for k in n]) / 1000.0)
    slope, intercept = np.polyfit(n, y, 1)
    return float(intercept), float(-slope)


def klevens_cmc_mM(n_c: float, a: float, b: float) -> float:
    return 1000.0 * 10 ** (a - b * n_c)


def delta_g_micellisation_kJ(cmc_M: float, beta: float = 0.0, T: float = 298.15) -> float:
    """Standard free energy of micellisation per mole of monomer, dG = (1 + beta) R T ln X_cmc.

    X_cmc is the CMC as a mole fraction (water at 55.5 mol/L); beta is the fraction of counter-ions
    bound to the micelle (zero for a non-ionic surfactant).  Zana (1980) and standard texts.
    """
    x = cmc_M / 55.5
    return (1 + beta) * C.R * T * math.log(x) / 1000.0


# ---------------------------------------------------------------------------------------------
# Electrolyte screening
# ---------------------------------------------------------------------------------------------

def salt_wt_pct_to_molar(wt_pct: float, mw: float = 58.44, density_g_mL: float = 1.0) -> float:
    """Molar concentration of a salt added at wt% in water (default: sodium chloride)."""
    return wt_pct * 10.0 * density_g_mL / mw


def debye_length_nm(ionic_strength_M: float, T: float = 298.15, eps_r: float = 78.4) -> float:
    """Debye screening length of a 1:1 electrolyte, in nanometre (Debye and Hueckel, 1923)."""
    I = max(ionic_strength_M, 1e-12) * 1000.0  # mol per cubic metre
    k2 = 2 * C.N_A * C.e**2 * I / (eps_r * C.epsilon_0 * C.k * T)
    return 1e9 / math.sqrt(k2)


def fraction_protonated(pH: float, pKa: float) -> float:
    """Henderson-Hasselbalch: share of a weak base present as its conjugate acid."""
    return 1.0 / (1.0 + 10 ** (pH - pKa))


# ---------------------------------------------------------------------------------------------
# Foam
# ---------------------------------------------------------------------------------------------

def laplace_pressure_Pa(gamma_mN_m: float, radius_um: float) -> float:
    """Excess pressure inside a bubble, 2 gamma / R (Young and Laplace)."""
    return 2 * gamma_mN_m * 1e-3 / (radius_um * 1e-6)


def ripening_pressure_gap_Pa(gamma_mN_m: float, r_small_um: float, r_large_um: float) -> float:
    """Pressure gap that drives gas from a small bubble into a large one (Ostwald ripening)."""
    return laplace_pressure_Pa(gamma_mN_m, r_small_um) - laplace_pressure_Pa(gamma_mN_m, r_large_um)


def foam_remaining(t_s, half_life_s: float):
    """Fraction of foam volume left after t seconds if decay is exponential with the given half-life."""
    return 0.5 ** (np.asarray(t_s, float) / half_life_s)


# ---------------------------------------------------------------------------------------------
# Hydrophile-lipophile balance for ethoxylates (Griffin, 1954)
# ---------------------------------------------------------------------------------------------

EO_UNIT_MW = 44.053


def hlb_griffin_ethoxylate(n_eo: int, total_mw: float) -> float:
    """HLB = E / 5, with E the weight percent of oxyethylene (Griffin 1954)."""
    return 20.0 * n_eo * EO_UNIT_MW / total_mw
