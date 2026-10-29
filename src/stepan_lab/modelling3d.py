# Created by Muhammad Talaat, Faculty of Pharmacy, Ain Shams University
# SPDX-FileCopyrightText: 2026 Muhammad Talaat
# SPDX-License-Identifier: MIT
"""Three-dimensional models of the surfactants and of the aggregates they form.

A molecule is embedded with ETKDG and relaxed with MMFF94 (RDKit).  An aggregate is a *geometric* model: relaxed
monomers are oriented tail-in on a sphere, a capsule (rod) or two parallel sheets, with the number of monomers taken
from the packing model of physchem.py, and monomers that overlap are pushed apart by rigid translations.  It shows how a mixture of structures fills space; it is not a molecular
dynamics result, and nothing in it is a measurement.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from rdkit import Chem
from rdkit.Chem import AllChem, Descriptors3D, rdFreeSASA
from scipy.spatial import cKDTree

from . import molecules, physchem

POLAR = {"N", "O", "S", "P"}


@dataclass
class Unit:
    """One relaxed monomer: heavy-atom coordinates with the lowest chain end on z = 0 and the head along +z."""

    key: str
    symbols: list[str]
    names: list[str]
    xyz: np.ndarray
    renewable: np.ndarray
    length: float


def embed(key: str, n_confs: int = 60, seed: int = 11) -> Chem.Mol:
    """Hydrogen-complete molecule with conformers relaxed by MMFF94 (ions kept, counter-ions dropped)."""
    m = Chem.AddHs(molecules.clean(molecules.mol(key)))
    big = max(Chem.GetMolFrags(m, asMols=True), key=lambda f: f.GetNumAtoms())
    m = Chem.Mol(big)
    params = AllChem.ETKDGv3()
    params.randomSeed = seed
    params.pruneRmsThresh = 0.5
    params.useRandomCoords = True  # long ethoxylate chains do not embed from the distance-geometry default
    ids = list(AllChem.EmbedMultipleConfs(m, n_confs, params))
    if not ids:
        raise RuntimeError(f"no conformer for {key}")
    res = AllChem.MMFFOptimizeMoleculeConfs(m, maxIters=2000)
    for cid, (_, e) in zip(ids, res):
        m.GetConformer(cid).SetDoubleProp("mmff_energy", float(e))
    return m


def conformer_energies(m: Chem.Mol) -> list[float]:
    return [m.GetConformer(c.GetId()).GetDoubleProp("mmff_energy") for c in m.GetConformers()]


def lowest_conformer(m: Chem.Mol) -> int:
    e = conformer_energies(m)
    return m.GetConformers()[int(np.argmin(e))].GetId()


def _span(m: Chem.Mol, cid: int) -> float:
    xyz = m.GetConformer(cid).GetPositions()
    heavy = [a.GetIdx() for a in m.GetAtoms() if a.GetAtomicNum() > 1]
    return float(np.linalg.norm(xyz[heavy][:, None] - xyz[heavy][None], axis=-1).max())


def extended_conformer(m: Chem.Mol, window_kcal: float = 12.0, compact: float = 1.0) -> int:
    """A conformer within an energy window of the lowest whose end-to-end span is ``compact`` times the longest.

    ``compact`` = 1 returns the most extended chain; a smaller value picks a partly folded chain, which fills the
    core of an aggregate more like the disordered chains of a real micelle."""
    ids = [c.GetId() for c in m.GetConformers()]
    e = np.array(conformer_energies(m))
    pool = [(cid, _span(m, cid)) for cid, ec in zip(ids, e) if ec - e.min() <= window_kcal]
    longest = max(sp for _, sp in pool)
    return min(pool, key=lambda t: abs(t[1] - compact * longest))[0]


def descriptors3d(m: Chem.Mol, conf_id: int | None = None) -> dict:
    """Shape and size descriptors of one conformer (default: the lowest in energy)."""
    cid = lowest_conformer(m) if conf_id is None else conf_id
    radii = rdFreeSASA.classifyAtoms(m)
    sasa = rdFreeSASA.CalcSASA(m, radii, confIdx=cid)
    e = np.array(conformer_energies(m))
    return {
        "conformers": m.GetNumConformers(),
        "mmff_energy_kcal": round(float(e.min()), 1),
        "shown_above_minimum_kcal": round(float(m.GetConformer(cid).GetDoubleProp("mmff_energy") - e.min()), 1),
        "within_3_kcal": int((e - e.min() <= 3.0).sum()),
        "radius_of_gyration_A": round(Descriptors3D.RadiusOfGyration(m, confId=cid), 2),
        "npr1": round(Descriptors3D.NPR1(m, confId=cid), 3),
        "npr2": round(Descriptors3D.NPR2(m, confId=cid), 3),
        "asphericity": round(Descriptors3D.Asphericity(m, confId=cid), 3),
        "sasa_A2": round(float(sasa), 1),
    }


def _tail_tip_and_head(m: Chem.Mol, conf: np.ndarray) -> tuple[int, np.ndarray]:
    """Terminal methyl carbon farthest from the polar atoms, and the centroid of the polar atoms."""
    polar = [a.GetIdx() for a in m.GetAtoms() if a.GetSymbol() in POLAR]
    head = conf[polar].mean(axis=0)
    tips = [a.GetIdx() for a in m.GetAtoms() if a.GetSymbol() == "C" and sum(1 for n in a.GetNeighbors() if n.GetAtomicNum() > 1) == 1]
    tip = max(tips, key=lambda i: np.linalg.norm(conf[i] - head))
    return tip, head


def _rotation_to_z(v: np.ndarray) -> np.ndarray:
    v = v / np.linalg.norm(v)
    z = np.array([0.0, 0.0, 1.0])
    c = float(np.dot(v, z))
    if c > 1 - 1e-9:
        return np.eye(3)
    if c < -1 + 1e-9:
        return np.diag([1.0, -1.0, -1.0])
    axis = np.cross(v, z)
    s = np.linalg.norm(axis)
    k = axis / s
    kx = np.array([[0, -k[2], k[1]], [k[2], 0, -k[0]], [-k[1], k[0], 0]])
    return np.eye(3) + kx * s + kx @ kx * (1 - c)


def make_unit(key: str, n_confs: int = 60, seed: int = 11, compact: float = 0.8) -> Unit:
    m = embed(key, n_confs, seed)
    cid = extended_conformer(m, compact=compact)
    conf = m.GetConformer(cid).GetPositions()
    tip, head = _tail_tip_and_head(m, conf)
    xyz = conf - conf[tip]
    rot = _rotation_to_z(head - conf[tip])
    xyz = xyz @ rot.T
    ren = molecules.mol(key)
    flags = {a.GetIdx(): a.GetAtomMapNum() == molecules.RENEWABLE for a in ren.GetAtoms()}
    heavy = [a.GetIdx() for a in m.GetAtoms() if a.GetAtomicNum() > 1]
    # heavy-atom order of the embedded fragment follows the input SMILES order (counter-ions come last)
    symbols = [m.GetAtomWithIdx(i).GetSymbol() for i in heavy]
    names = [f"{s}{n + 1}" for n, s in enumerate(symbols)]
    renew = np.array([flags.get(i, False) for i in heavy])
    pts = xyz[heavy]
    pts[:, 2] -= pts[:, 2].min()  # the lowest chain end sits on the anchor plane, so a second chain never crosses it
    return Unit(key, symbols, names, pts, renew, float(pts[:, 2].max()))


def _fibonacci(n: int) -> np.ndarray:
    i = np.arange(n) + 0.5
    phi = np.arccos(1 - 2 * i / n)
    th = math.pi * (1 + 5**0.5) * i
    return np.stack([np.cos(th) * np.sin(phi), np.sin(th) * np.sin(phi), np.cos(phi)], axis=1)


def _capsule_lattice(radius: float, cyl_len: float, gap: float) -> tuple[np.ndarray, np.ndarray]:
    """Points about ``gap`` apart on a capsule (rings on the cylinder, a Fibonacci spiral on each cap) and normals."""
    pts, nor = [], []
    per_ring = max(int(2 * math.pi * radius / gap), 3)
    rings = max(int(cyl_len / gap), 1)
    for k in range(rings):
        z = (k + 0.5) / rings * cyl_len - cyl_len / 2
        off = (k % 2) * math.pi / per_ring
        for j in range(per_ring):
            th = 2 * math.pi * j / per_ring + off
            pts.append([radius * math.cos(th), radius * math.sin(th), z])
            nor.append([math.cos(th), math.sin(th), 0.0])
    ncap = max(int(2 * math.pi * radius**2 / gap**2), 3)
    for sign in (1, -1):
        i = np.arange(ncap) + 0.5
        phi = np.arccos(1 - i / ncap)  # hemisphere
        th = math.pi * (1 + 5**0.5) * i
        for ph, t in zip(phi, th):
            d = np.array([math.cos(t) * math.sin(ph), math.sin(t) * math.sin(ph), sign * math.cos(ph)])
            pts.append(list(radius * d + np.array([0, 0, sign * cyl_len / 2])))
            nor.append(list(d))
    return np.array(pts), np.array(nor)


def _capsule_points(n: int, radius0: float, chain_len: float, gap: float, ratio: float) -> tuple[np.ndarray, np.ndarray, float]:
    r = radius0
    for _ in range(200):
        pts, nor = _capsule_lattice(r, ratio * (r + chain_len), gap)
        if len(pts) >= n:
            keep = np.linspace(0, len(pts) - 1, n).astype(int)
            return pts[keep], nor[keep], r
        r += 0.15
    raise RuntimeError("capsule too small")


def _sheet_points(n: int, side: float) -> np.ndarray:
    g = int(math.ceil(math.sqrt(n)))
    xs = (np.arange(g) + 0.5) / g * side - side / 2
    pts = np.array([[x, y] for x in xs for y in xs])[:n]
    return pts


def _place(unit: Unit, anchor: np.ndarray, outward: np.ndarray, roll: float) -> np.ndarray:
    """Move a monomer so that its tail tip sits at ``anchor`` and its head points along ``outward``."""
    xyz = unit.xyz.copy()
    c, s = math.cos(roll), math.sin(roll)
    xyz = xyz @ np.array([[c, s, 0], [-s, c, 0], [0, 0, 1]])
    return xyz @ _rotation_to_z(outward) + anchor  # row-vector form of the rotation that takes +z to ``outward``


def _best_roll(unit: Unit, anchor: np.ndarray, outward: np.ndarray, placed: np.ndarray, start: float, tries: int = 24) -> np.ndarray:
    """Orientation about the long axis with the fewest close atoms among the monomers already placed."""
    tree = cKDTree(placed) if len(placed) else None
    best, best_score = None, math.inf
    for t in range(tries):
        cand = _place(unit, anchor, outward, start + 2 * math.pi * t / tries)
        score = 0.0 if tree is None else float((np.clip(3.0 - tree.query(cand)[0], 0, None) ** 2).sum())
        if score < best_score:
            best, best_score = cand, score
            if score == 0.0:
                break
    return best


def relax_overlaps(pts: list[np.ndarray], target: float = 3.0, iters: int = 600, spring: float = 0.01, max_move: float = 0.4) -> list[np.ndarray]:
    """Push apart monomers whose heavy atoms are closer than ``target`` angstrom (rigid-body moves, a weak spring to the start).

    Only translations are applied, so every monomer keeps the relaxed conformation it was embedded with."""
    n = len(pts)
    base = np.vstack(pts)
    mono = np.repeat(np.arange(n), [len(q) for q in pts])
    shift = np.zeros((n, 3))
    for _ in range(iters):
        cur = base + shift[mono]
        pairs = cKDTree(cur).query_pairs(target, output_type="ndarray")
        if len(pairs):
            pairs = pairs[mono[pairs[:, 0]] != mono[pairs[:, 1]]]
        if not len(pairs):
            break
        d = cur[pairs[:, 0]] - cur[pairs[:, 1]]
        dist = np.linalg.norm(d, axis=1) + 1e-9
        push = d / dist[:, None] * ((target - dist) / 2)[:, None]
        force = np.zeros((n, 3))
        np.add.at(force, mono[pairs[:, 0]], push)
        np.add.at(force, mono[pairs[:, 1]], -push)
        count = np.bincount(np.concatenate([mono[pairs[:, 0]], mono[pairs[:, 1]]]), minlength=n).clip(min=1)
        move = force / count[:, None] * 2.0 - spring * shift
        norm = np.linalg.norm(move, axis=1)
        move *= np.minimum(1.0, max_move / np.maximum(norm, 1e-9))[:, None]
        shift += move
    return [base[mono == i] + shift[i] for i in range(n)]


@dataclass
class Aggregate:
    shape: str
    n: int
    species: list[str]
    symbols: list[str]
    names: list[str]
    resnames: list[str]
    resids: list[int]
    renewable: list[bool]
    xyz: np.ndarray
    radius_A: float
    note: str

    def pdb(self) -> str:
        lines = []
        c = self.xyz - self.xyz.mean(axis=0)
        for i, (s, n, r, rid, p, ren) in enumerate(zip(self.symbols, self.names, self.resnames, self.resids, c, self.renewable), 1):
            lines.append("HETATM%5d %-4s %3s A%4d    %8.2f%8.2f%8.2f  1.00%6.2f          %2s" % (i % 100000, n[:4], r[:3], rid % 10000, p[0], p[1], p[2], 1.0 if ren else 0.0, s))
        lines.append("END")
        return "\n".join(lines)


def build_aggregate(units: dict[str, Unit], composition: dict[str, float], shape: str, n_total: int,
                    a0: float, chain_len: float, seed: int = 3, rod_ratio: float = 4.0, resnames: dict[str, str] | None = None) -> Aggregate:
    """Assemble ``n_total`` monomers (mixed in the given mole fractions) into a sphere, a rod or a bilayer patch.

    ``resnames`` maps each structure key to the three-letter residue name written to the PDB file (default: the first three letters of the key)."""
    rng = np.random.default_rng(seed)
    keys = list(composition)
    frac = np.array([composition[k] for k in keys], float)
    frac /= frac.sum()
    counts = np.floor(frac * n_total).astype(int)
    counts[0] += n_total - counts.sum()
    order = np.concatenate([[k] * c for k, c in zip(keys, counts)])
    rng.shuffle(order)
    n = len(order)
    tip_gap = 4.6  # spacing of the tail tips in angstrom: about the cross-section of a packed chain
    anchors, outs = [], []
    if shape == "sphere":
        r_t = max(math.sqrt(n * tip_gap**2 / (4 * math.pi)), 3.0)
        d = _fibonacci(n)
        anchors, outs = d * r_t, d
        radius = r_t + chain_len
    elif shape == "rod":
        anchors, outs, r_t = _capsule_points(n, 3.0, chain_len, tip_gap, rod_ratio)
        radius = r_t + chain_len
    elif shape == "bilayer":
        half = n // 2
        side = math.sqrt(half * a0 * 0.9)
        xy = _sheet_points(half, side)
        gap = 1.5
        anchors = np.vstack([np.c_[xy, np.full(half, gap)], np.c_[_sheet_points(n - half, side), np.full(n - half, -gap)]])
        outs = np.vstack([np.tile([0, 0, 1.0], (half, 1)), np.tile([0, 0, -1.0], (n - half, 1))])
        radius = side / 2
    else:
        raise ValueError(shape)
    sym, names, res, rid, ren, pts = [], [], [], [], [], []
    placed = np.empty((0, 3))
    for i, k in enumerate(order):
        u = units[k]
        p = _best_roll(u, anchors[i], outs[i], placed, rng.uniform(0, 2 * math.pi))
        placed = np.vstack([placed, p])
        pts.append(p)
        sym += u.symbols
        names += u.names
        res += [(resnames or {}).get(k, k.upper()[:3])] * len(u.symbols)
        rid += [i + 1] * len(u.symbols)
        ren += list(u.renewable)
    pts = relax_overlaps(pts)
    xyz = np.vstack(pts)
    if shape == "rod":
        xyz = xyz[:, [2, 0, 1]]  # axis along x
    elif shape == "bilayer":
        xyz = xyz[:, [1, 2, 0]]  # sheet normal along y
    return Aggregate(shape, n, list(order), sym, names, res, rid, ren, xyz, float(radius),
                     "geometric model: monomers oriented tail-in; not a dynamics result")


def contacts_below(agg: Aggregate, cutoff: float = 1.0) -> int:
    """Number of atom pairs from different monomers that are closer than the cutoff (angstrom)."""
    tree = cKDTree(agg.xyz)
    bad = 0
    ids = np.array(agg.resids)
    for i, j in tree.query_pairs(cutoff):
        if ids[i] != ids[j]:
            bad += 1
    return bad


def aggregate_summary(agg: Aggregate, p_value: float) -> dict:
    return {"shape": agg.shape, "monomers": agg.n, "atoms": len(agg.symbols), "radius_A": round(agg.radius_A, 1),
            "packing_parameter": round(p_value, 2), "close_contacts": contacts_below(agg, 2.0)}


def packing_for(keys: dict[str, float], a0_factor: float = 1.0) -> tuple[float, float, float]:
    """(mean chain carbons, mean head-group area, packing parameter) of a mixture of registry structures.

    ``a0_factor`` scales every head-group area (salt screening is represented by a factor below 1)."""
    comps = []
    for k, x in keys.items():
        s = molecules.REGISTRY[k]
        comps.append((x, s.chain_n, s.head_a0 * a0_factor, 2 if k in ("eq_b", "soleil_eq") else 1))
    p = physchem.mixed_packing_parameter(comps)
    tot = sum(c[0] for c in comps)
    n_mean = sum(c[0] * c[1] for c in comps) / tot
    a_mean = sum(c[0] * c[2] for c in comps) / tot
    return n_mean, a_mean, p
