# Created by Muhammad Talaat, Faculty of Pharmacy, Ain Shams University
# SPDX-FileCopyrightText: 2026 Muhammad Talaat
# SPDX-License-Identifier: MIT
"""Coarse-grained molecular dynamics of surfactant self-assembly, run with OpenMM.

Every structure of the registry is mapped to beads (about four heavy atoms per bead) straight from its SMILES; surfactants,
water and ions are then placed at random on a lattice, relaxed, and simulated in explicit solvent at constant temperature and
pressure.  Micelles and bilayers that form are measured on the trajectory: aggregation number, radius of gyration, shape and the
radial density of the heads, tails and water.

The model is a **simplified coarse-grained force field**: the bead sizes, the interaction levels between the five bead types and the
reaction-field electrostatics follow the published MARTINI scheme (Marrink et al. 2007, J. Phys. Chem. B 111, 7812), but the assignment of the
bead types to the head groups is my own coarse-graining and the parameters have not been fitted or validated for each surfactant.  Its output
is labelled *modelled*: it shows how the structures assemble, and it does not predict a measured aggregation number or a phase boundary.
"""

from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass, field
from functools import cache

import numpy as np
from rdkit import Chem
from rdkit.Chem.Draw import rdMolDraw2D
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
from scipy.spatial import cKDTree

from . import molecules

# ------------------------------------------------------------------------------------------------------------
# The force field
# ------------------------------------------------------------------------------------------------------------

TYPES = ("W", "T", "N", "P", "A", "C")
LONG = {"W": "water (four molecules)", "T": "apolar chain", "N": "semi-polar", "P": "polar", "A": "anionic", "C": "cationic"}
COLOUR = {"W": "#6aa7ff", "T": "#35d0ba", "N": "#b48cff", "P": "#ff9f43", "A": "#ff7a90", "C": "#5b9dff"}
MASS = 72.0  # amu per bead
SIGMA = 0.47  # nm
BOND_R, BOND_K = 0.47, 1250.0  # nm, kJ/mol/nm^2
ANGLE_K = 25.0  # kJ/mol, cosine harmonic about 180 degrees
EPS_R = 15.0  # relative permittivity of the explicit-water model
CUTOFF, SWITCH = 1.1, 0.9  # nm
SPACING = 0.493  # nm, lattice spacing that gives the density of the water model
STATE = {"W": 0.0, "T": 0.0, "N": 0.0, "P": 0.0, "A": -1.0, "C": 1.0}

# Lennard-Jones well depth (kJ/mol) and size (nm) of each pair of bead types.  The weak apolar-polar pairs have the larger size 0.62 nm (level IX of the scheme).
_E = {("W", "W"): 5.0, ("W", "T"): 2.0, ("W", "N"): 4.0, ("W", "P"): 5.0, ("W", "A"): 5.0, ("W", "C"): 5.0,
      ("T", "T"): 3.5, ("T", "N"): 3.5, ("T", "P"): 2.0, ("T", "A"): 2.0, ("T", "C"): 2.0,
      ("N", "N"): 3.5, ("N", "P"): 3.5, ("N", "A"): 3.5, ("N", "C"): 3.5,
      ("P", "P"): 5.0, ("P", "A"): 5.0, ("P", "C"): 5.0,
      ("A", "A"): 3.1, ("A", "C"): 5.6, ("C", "C"): 3.1}
_WIDE = {("W", "T"), ("T", "P"), ("T", "A"), ("T", "C")}


def pair_table() -> tuple[np.ndarray, np.ndarray]:
    n = len(TYPES)
    eps, sig = np.zeros((n, n)), np.full((n, n), SIGMA)
    for (a, b), e in _E.items():
        i, j = TYPES.index(a), TYPES.index(b)
        eps[i, j] = eps[j, i] = e
        if (a, b) in _WIDE or (b, a) in _WIDE:
            sig[i, j] = sig[j, i] = 0.62
    return eps, sig


# ------------------------------------------------------------------------------------------------------------
# Coarse-graining a structure
# ------------------------------------------------------------------------------------------------------------

@dataclass
class Bead:
    type: str
    atoms: list[int]
    charge: int = 0


@dataclass
class CGMol:
    key: str
    beads: list[Bead]
    bonds: list[tuple[int, int]]
    n_tail_beads: int
    heavy_atoms: int
    ions: tuple[str, int] | None = None  # ('NA' | 'CL', count) that make the molecule neutral
    root: int = 0

    @property
    def charge(self) -> int:
        return sum(b.charge for b in self.beads)

    @property
    def sequence(self) -> str:
        return " ".join(b.type for b in self.beads)


def _groups(m: Chem.Mol, head: list[int]) -> list[list[int]]:
    """Functional groups kept in one bead: sulfate, sulfonate, carboxylate and phosphate with their oxygens, ammonium and N-oxide with their leaf atoms."""
    hs, used, groups = set(head), set(), []
    for i in head:
        a = m.GetAtomWithIdx(i)
        if i in used:
            continue
        leaf = [n.GetIdx() for n in a.GetNeighbors() if n.GetDegree() == 1 and n.GetIdx() in hs and n.GetIdx() not in used]
        if a.GetSymbol() in ("S", "P") or a.GetSymbol() == "C" and any(m.GetAtomWithIdx(j).GetSymbol() == "O" and m.GetAtomWithIdx(j).GetFormalCharge() < 0 for j in leaf):
            g = [i] + [j for j in leaf if m.GetAtomWithIdx(j).GetSymbol() == "O"]
        elif a.GetSymbol() == "N" and a.GetFormalCharge() > 0:
            g = [i] + leaf
        else:
            continue
        if len(g) > 1:
            groups.append(g)
            used.update(g)
    return groups


def _merge_small(m: Chem.Mol, chunks: list[list[int]]) -> list[list[int]]:
    """Pieces of one or two atoms join the neighbouring piece that carries a charge (otherwise the largest neighbour)."""
    chunks = [list(c) for c in chunks]
    while True:
        where = {a: k for k, c in enumerate(chunks) for a in c}
        small = [k for k, c in enumerate(chunks) if len(c) <= 2]
        done = False
        for k in small:
            nb = {where[n.GetIdx()] for a in chunks[k] for n in m.GetAtomWithIdx(a).GetNeighbors() if n.GetIdx() in where and where[n.GetIdx()] != k}
            if not nb:  # a piece that touches only the chain (the oxygen of an amide, say) joins its sibling on the same chain atom
                for a in chunks[k]:
                    for n in m.GetAtomWithIdx(a).GetNeighbors():
                        if n.GetIdx() not in where:
                            nb |= {where[n2.GetIdx()] for n2 in n.GetNeighbors() if n2.GetIdx() in where and where[n2.GetIdx()] != k}
            if not nb:
                continue
            def key(t):
                ch = abs(sum(m.GetAtomWithIdx(a).GetFormalCharge() for a in chunks[t]))
                return (ch, len(chunks[t]))
            best = max(nb, key=key)
            chunks[best] += chunks[k]
            chunks[k] = []
            done = True
            break
        chunks = [c for c in chunks if c]
        if not done:
            return chunks


def _round_half_up(x: float) -> int:
    return int(math.floor(x + 0.5))


def _tails(m: Chem.Mol) -> list[list[int]]:
    """Alkyl chains: from a terminal methyl along the carbons up to the first carbon that bears a heteroatom or a branch."""
    out = []
    for a in m.GetAtoms():
        if a.GetSymbol() != "C" or a.GetDegree() != 1 or a.GetNeighbors()[0].GetSymbol() != "C":
            continue
        path, cur = [a.GetIdx()], a
        while True:
            nbrs = [n for n in cur.GetNeighbors() if n.GetIdx() not in path]
            if any(n.GetSymbol() != "C" for n in nbrs) or len(nbrs) != 1:
                break
            cur = nbrs[0]
            path.append(cur.GetIdx())
        if len(path) >= 6:
            out.append(path)
    return out


@cache
def coarse_grain(key: str) -> CGMol:
    """Map a registry structure to beads: apolar chain beads (four carbons each) and head beads typed by charge and polarity."""
    full = molecules.clean(molecules.mol(key))
    m = molecules._largest_fragment(full)
    tails = _tails(m)
    if not tails:
        raise ValueError(f"{key} has no alkyl chain to coarse-grain")
    bead_of = {}
    beads: list[Bead] = []
    bonds: list[tuple[int, int]] = []
    anchors: list[tuple[int, int]] = []  # (bead index of the last chain bead, atom index of its last carbon)
    tail_beads: list[int] = []
    for t in tails:
        n_b = max(1, _round_half_up(len(t) / 4))
        edges = np.linspace(0, len(t), n_b + 1).round().astype(int)
        first = len(beads)
        for s, e in zip(edges[:-1], edges[1:]):
            for i in t[s:e]:
                bead_of[i] = len(beads)
            tail_beads.append(len(beads))
            beads.append(Bead("T", list(t[s:e])))
        bonds += [(first + i, first + i + 1) for i in range(n_b - 1)]
        anchors.append((len(beads) - 1, t[-1]))
    head = [a.GetIdx() for a in m.GetAtoms() if a.GetIdx() not in bead_of]
    # head atoms in order of distance from the chain ends, then grouped four at a time along the bonds
    dist = {i: 1e9 for i in head}
    queue = deque()
    for _, atom in anchors:
        for n in m.GetAtomWithIdx(atom).GetNeighbors():
            if n.GetIdx() in dist and dist[n.GetIdx()] == 1e9:
                dist[n.GetIdx()] = 1
                queue.append(n.GetIdx())
    while queue:
        i = queue.popleft()
        for n in m.GetAtomWithIdx(i).GetNeighbors():
            if n.GetIdx() in dist and dist[n.GetIdx()] > dist[i] + 1:
                dist[n.GetIdx()] = dist[i] + 1
                queue.append(n.GetIdx())
    for i in head:
        if dist[i] == 1e9:  # a fragment that is not bonded to a chain is left out of the model
            dist[i] = 99
    chunks = [g for g in _groups(m, head)]
    taken = {a for g in chunks for a in g}
    for i in sorted(head, key=lambda x: (dist[x], x)):
        if i in taken:
            continue
        chunk, frontier = [i], deque([i])
        taken.add(i)
        while frontier and len(chunk) < 4:
            cur = frontier.popleft()
            for n in sorted(m.GetAtomWithIdx(cur).GetNeighbors(), key=lambda x: dist.get(x.GetIdx(), 99)):
                j = n.GetIdx()
                if j in dist and j not in taken and len(chunk) < 4:
                    taken.add(j)
                    chunk.append(j)
                    frontier.append(j)
        chunks.append(chunk)
    chunks = _merge_small(m, chunks)
    chunks.sort(key=lambda c: min(dist[a] for a in c))
    for chunk in chunks:
        for j in chunk:
            bead_of[j] = len(beads)
        charge = sum(m.GetAtomWithIdx(j).GetFormalCharge() for j in chunk)
        hetero = sum(1 for j in chunk if m.GetAtomWithIdx(j).GetSymbol() != "C")
        if charge > 0:
            typ = "C"
        elif charge < 0:
            typ = "A"
        elif hetero == 0:
            typ = "N"  # carbon-only pieces of a head group are not allowed to behave as chain
        else:
            typ = "P" if hetero / len(chunk) >= 0.4 else "N"
        beads.append(Bead(typ, chunk, int(np.sign(charge))))
    seen = set(bonds)
    for b in m.GetBonds():
        x, y = bead_of.get(b.GetBeginAtomIdx()), bead_of.get(b.GetEndAtomIdx())
        if x is not None and y is not None and x != y and (min(x, y), max(x, y)) not in seen:
            seen.add((min(x, y), max(x, y)))
            bonds.append((min(x, y), max(x, y)))
    # the root of the random placement is the head bead of highest degree (the head group)
    deg = np.zeros(len(beads), int)
    for x, y in bonds:
        deg[x] += 1
        deg[y] += 1
    head_idx = [i for i in range(len(beads)) if i not in tail_beads] or [tail_beads[-1]]
    root = max(head_idx, key=lambda i: (deg[i], -i))
    cg = CGMol(key, beads, bonds, len(tail_beads), m.GetNumAtoms(), None, root)
    q = cg.charge
    if q:
        cg.ions = ("NA" if q < 0 else "CL", abs(q))
    return cg


def draw_mapping(key: str, size: tuple[int, int] = (460, 220)) -> str:
    """The structure with the atoms of each bead coloured by the bead type."""
    cg = coarse_grain(key)
    m = molecules._largest_fragment(molecules.clean(molecules.mol(key)))
    d = rdMolDraw2D.MolDraw2DSVG(*size)
    d.drawOptions().addAtomIndices = False
    cols, rad = {}, {}
    for b in cg.beads:
        h = COLOUR[b.type].lstrip("#")
        c = tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
        for a in b.atoms:
            cols[a], rad[a] = c, 0.45
    rdMolDraw2D.PrepareAndDrawMolecule(d, m, highlightAtoms=list(cols), highlightAtomColors=cols, highlightAtomRadii=rad)
    d.FinishDrawing()
    return d.GetDrawingText()


# ------------------------------------------------------------------------------------------------------------
# Building a simulation box
# ------------------------------------------------------------------------------------------------------------

@dataclass
class Box:
    n_side: int
    types: list[str]
    charges: list[float]
    kind: list[str]            # 'S' surfactant bead, 'W' water, 'I' ion
    mol: list[int]             # surfactant molecule index, -1 otherwise
    species: list[str]         # structure key of the surfactant, '' otherwise
    bonds: list[tuple[int, int]]
    mols: list[list[int]]      # particle indices of each surfactant molecule
    pos: np.ndarray            # nm
    length: float = 0.0        # nm, cubic box edge
    note: str = ""
    adj: dict = field(default_factory=dict)  # bead index -> bonded beads

    @property
    def n(self) -> int:
        return len(self.types)


def box_size_for(composition: dict[str, int], molar: float = 0.25) -> int:
    """Lattice sites per edge of a cubic box that holds the surfactants at about ``molar`` mol/L and leaves at least three quarters of the sites to water."""
    n = sum(composition.values())
    beads = sum(c * (len(coarse_grain(k).beads) + (coarse_grain(k).ions[1] if coarse_grain(k).ions else 0)) for k, c in composition.items())
    by_conc = (n / (molar * 0.6022)) ** (1 / 3) / SPACING  # nm3 per mol/L: 1 / 0.6022
    by_room = (4 * beads) ** (1 / 3)
    return max(8, int(math.ceil(max(by_conc, by_room))))


def build_box(composition: dict[str, int], n_side: int = 16, seed: int = 1) -> Box:
    """Place the surfactants as random chains on a cubic lattice, add their counter-ions, and fill the rest of the box with water."""
    rng = np.random.default_rng(seed)
    free = np.ones((n_side,) * 3, bool)
    nbr = np.array([[1, 0, 0], [-1, 0, 0], [0, 1, 0], [0, -1, 0], [0, 0, 1], [0, 0, -1]])
    types, charges, kind, mol, species, bonds, mols, pos = [], [], [], [], [], [], [], []

    def site_pos(s):
        return (np.array(s) + 0.5) * SPACING

    order = [k for k, c in composition.items() for _ in range(c)]
    rng.shuffle(order)
    ion_counts = {"NA": 0, "CL": 0}
    for mi, key in enumerate(order):
        cg = coarse_grain(key)
        adj = {i: [] for i in range(len(cg.beads))}
        for a, b in cg.bonds:
            adj[a].append(b)
            adj[b].append(a)
        for attempt in range(2000):
            placed, sites = {}, []
            root_site = tuple(rng.integers(0, n_side, 3))
            if not free[root_site]:
                continue
            placed[cg.root] = root_site
            free[root_site] = False
            sites.append(root_site)
            queue, ok = deque([cg.root]), True
            while queue and ok:
                cur = queue.popleft()
                for nb in adj[cur]:
                    if nb in placed:
                        continue
                    cands = [tuple((np.array(placed[cur]) + d) % n_side) for d in nbr[rng.permutation(6)]]
                    cands = [c for c in cands if free[c]]
                    if not cands:
                        ok = False
                        break
                    placed[nb] = cands[0]
                    free[cands[0]] = False
                    sites.append(cands[0])
                    queue.append(nb)
            if ok and len(placed) == len(cg.beads):
                break
            for s in sites:
                free[s] = True
        else:
            raise RuntimeError(f"could not place {key}; use a larger box")
        base = len(types)
        idx = []
        for bi, b in enumerate(cg.beads):
            types.append(b.type)
            charges.append(float(b.charge))
            kind.append("S")
            mol.append(mi)
            species.append(key)
            pos.append(site_pos(placed[bi]))
            idx.append(base + bi)
        mols.append(idx)
        bonds += [(base + a, base + b) for a, b in cg.bonds]
        if cg.ions:
            ion_counts[cg.ions[0]] += cg.ions[1]
    sites = np.argwhere(free)
    rng.shuffle(sites)
    cursor = 0
    for kindname, n in ion_counts.items():
        for _ in range(n):
            s = sites[cursor]
            cursor += 1
            types.append("C" if kindname == "NA" else "A")
            charges.append(1.0 if kindname == "NA" else -1.0)
            kind.append("I")
            mol.append(-1)
            species.append(kindname)
            pos.append(site_pos(s))
    for s in sites[cursor:]:
        types.append("W")
        charges.append(0.0)
        kind.append("W")
        mol.append(-1)
        species.append("")
        pos.append(site_pos(s))
    L = n_side * SPACING
    adj: dict[int, list[int]] = {}
    for a, b in bonds:
        adj.setdefault(a, []).append(b)
        adj.setdefault(b, []).append(a)
    return Box(n_side, types, charges, kind, mol, species, bonds, mols, np.array(pos), L, adj=adj)


# ------------------------------------------------------------------------------------------------------------
# Simulation
# ------------------------------------------------------------------------------------------------------------

PLATFORM = None  # set to "CPU", "OpenCL", "CUDA" or "HIP" to force a platform


def platform_candidates() -> list[str]:
    """Platforms in the order to try them: a GPU through CUDA, HIP or OpenCL first, then the CPU."""
    import openmm as mm

    names = [mm.Platform.getPlatform(i).getName() for i in range(mm.Platform.getNumPlatforms())]
    if PLATFORM in names:
        return [PLATFORM]
    return [n for n in ("CUDA", "HIP", "OpenCL", "CPU", "Reference") if n in names] or names


def platform_name() -> str:
    """The platform a simulation starts on."""
    return platform_candidates()[0]


def make_simulation(box: Box, temperature: float = 310.0, dt_ps: float = 0.02, seed: int = 7, threads: int | None = None, platform: str | None = None):
    """OpenMM simulation of the box: bonds, linear-chain angles, Lennard-Jones by bead type, reaction-field electrostatics, barostat."""
    import openmm as mm
    from openmm import unit as u

    system = mm.System()
    L = box.length
    system.setDefaultPeriodicBoxVectors(mm.Vec3(L, 0, 0), mm.Vec3(0, L, 0), mm.Vec3(0, 0, L))
    eps, sig = pair_table()
    n_t = len(TYPES)
    lj = mm.CustomNonbondedForce("4*eps*((s/r)^12-(s/r)^6); eps=epstab(t1,t2); s=sigtab(t1,t2)")
    lj.addPerParticleParameter("t")
    lj.addTabulatedFunction("epstab", mm.Discrete2DFunction(n_t, n_t, eps.flatten(order="F").tolist()))
    lj.addTabulatedFunction("sigtab", mm.Discrete2DFunction(n_t, n_t, sig.flatten(order="F").tolist()))
    lj.setNonbondedMethod(mm.CustomNonbondedForce.CutoffPeriodic)
    lj.setCutoffDistance(CUTOFF)
    lj.setUseSwitchingFunction(True)
    lj.setSwitchingDistance(SWITCH)
    lj.setUseLongRangeCorrection(False)
    el = mm.NonbondedForce()
    el.setNonbondedMethod(mm.NonbondedForce.CutoffPeriodic)
    el.setCutoffDistance(CUTOFF)
    el.setReactionFieldDielectric(1.0e6)
    el.setUseDispersionCorrection(False)
    scale = 1.0 / math.sqrt(EPS_R)  # a relative permittivity of 15 is applied by scaling the charges
    for t, q in zip(box.types, box.charges):
        system.addParticle(MASS)
        lj.addParticle([TYPES.index(t)])
        el.addParticle(q * scale, 0.1, 0.0)
    bond = mm.HarmonicBondForce()
    for a, b in box.bonds:
        bond.addBond(a, b, BOND_R, BOND_K)
    # exclusions between bonded beads in both nonbonded forces
    for a, b in box.bonds:
        lj.addExclusion(a, b)
        el.addException(a, b, 0.0, 0.1, 0.0)
    angle = mm.CustomAngleForce("0.5*k*(1+cos(theta))^2")
    angle.addGlobalParameter("k", ANGLE_K)
    adj: dict[int, list[int]] = {}
    for a, b in box.bonds:
        adj.setdefault(a, []).append(b)
        adj.setdefault(b, []).append(a)
    for mid, nb in adj.items():
        if len(nb) == 2:
            angle.addAngle(nb[0], mid, nb[1], [])
    for f in (lj, el, bond, angle):
        system.addForce(f)
    barostat = mm.MonteCarloBarostat(1.0 * u.bar, temperature * u.kelvin, 25)
    barostat.setRandomNumberSeed(seed)
    system.addForce(barostat)
    integrator = mm.LangevinMiddleIntegrator(temperature * u.kelvin, 1.0 / u.picosecond, dt_ps * u.picoseconds)
    integrator.setRandomNumberSeed(seed)
    pname = platform or platform_name()
    plat = mm.Platform.getPlatformByName(pname)
    props = {"Threads": str(threads)} if (threads and pname == "CPU") else {}
    from openmm import app

    sim = app.Simulation(_topology(box), system, integrator, plat, props)
    sim.context.setPositions(box.pos)
    return sim


def _topology(box: Box):
    from openmm import app

    top = app.Topology()
    chain = top.addChain()
    res = top.addResidue("BOX", chain)
    elem = app.Element.getBySymbol("C")
    atoms = [top.addAtom(f"B{i}", elem, res) for i in range(box.n)]
    for a, b in box.bonds:
        top.addBond(atoms[a], atoms[b])
    return top


def positions_nm(sim) -> np.ndarray:
    from openmm import unit as u

    return np.array(sim.context.getState(getPositions=True).getPositions(asNumpy=True).value_in_unit(u.nanometer))


def _energy(sim) -> float:
    from openmm import unit as u

    return float(sim.context.getState(getEnergy=True).getPotentialEnergy().value_in_unit(u.kilojoule_per_mole))


def box_length_nm(sim) -> float:
    from openmm import unit as u

    return float(sim.context.getState().getPeriodicBoxVectors(asNumpy=True).value_in_unit(u.nanometer)[0][0])


def relax(sim, steps_fast: int = 4000) -> None:
    """Energy minimisation, then short runs with small time steps so the random start does not blow up."""

    sim.minimizeEnergy(maxIterations=1000)
    for dt, n in ((0.002, steps_fast), (0.005, steps_fast), (0.010, steps_fast)):
        sim.integrator.setStepSize(dt)
        sim.context.setVelocitiesToTemperature(sim.integrator.getTemperature())
        sim.step(n)
    sim.integrator.setStepSize(0.02)


# ------------------------------------------------------------------------------------------------------------
# Analysis of a frame
# ------------------------------------------------------------------------------------------------------------

def _mic(d: np.ndarray, L: float) -> np.ndarray:
    return d - L * np.round(d / L)


def _whole(pos: np.ndarray, idx: list[int], adj: dict[int, list[int]], L: float) -> np.ndarray:
    """Coordinates of one molecule made whole by following its bonds, so that a molecule longer than half the box is not torn apart."""
    out = {idx[0]: pos[idx[0]].copy()}
    queue = deque([idx[0]])
    while queue:
        a = queue.popleft()
        for b in adj.get(a, []):
            if b not in out:
                out[b] = out[a] + _mic(pos[b] - pos[a], L)
                queue.append(b)
    return np.array([out[i] for i in idx])


@dataclass
class Frame:
    t_ns: float
    sizes: list[int]
    largest: int
    mean_agg: float
    free_fraction: float
    rg: float
    asphericity: float
    kappa2: float


def clusters(box: Box, pos: np.ndarray, L: float, cutoff: float = 0.60, minimum: int = 4):
    """Surfactants whose chain beads touch (closer than ``cutoff`` nm) are in the same aggregate; returns the label of each molecule."""
    tail = [i for i, (t, k) in enumerate(zip(box.types, box.kind)) if k == "S" and t == "T"]
    tree = cKDTree(np.mod(pos[tail], L), boxsize=L)
    pairs = tree.query_pairs(cutoff, output_type="ndarray")
    mol = np.array(box.mol)[tail]
    n = len(box.mols)
    if len(pairs):
        a, b = mol[pairs[:, 0]], mol[pairs[:, 1]]
        keep = a != b
        g = coo_matrix((np.ones(keep.sum()), (a[keep], b[keep])), shape=(n, n))
    else:
        g = coo_matrix((n, n))
    _, labels = connected_components(g, directed=False)
    return labels, mol, pairs


def whole_cluster(box: Box, pos: np.ndarray, L: float, members: list[int]) -> np.ndarray:
    """Coordinates (nm) of the beads of the member molecules, each made whole along its bonds and the molecules joined into one piece."""
    whole = {}
    for m in members:
        whole[m] = _whole(pos, box.mols[m], box.adj, L)
    placed = {members[0]: whole[members[0]]}
    remaining = set(members[1:])
    while remaining:
        pts = np.vstack(list(placed.values()))
        tree = cKDTree(np.mod(pts, L), boxsize=L)
        best, best_d, best_shift = None, 1e9, None
        for m in remaining:
            d, j = tree.query(np.mod(whole[m], L))
            b = int(np.argmin(d))
            if d[b] < best_d:
                best, best_d = m, float(d[b])
                best_shift = pts[j[b]] + _mic(whole[m][b] - pts[j[b]], L) - whole[m][b]
        placed[best] = whole[best] + best_shift
        remaining.remove(best)
    return np.vstack([placed[m] for m in members])


def gyration(points: np.ndarray) -> tuple[float, float, float]:
    """Radius of gyration (nm), asphericity b and relative shape anisotropy kappa^2 of a set of beads of equal mass."""
    c = points - points.mean(axis=0)
    S = c.T @ c / len(c)
    lam = np.sort(np.linalg.eigvalsh(S))[::-1]
    rg2 = float(lam.sum())
    b = float(lam[0] - 0.5 * (lam[1] + lam[2]))
    k2 = float(1.5 * (lam**2).sum() / rg2**2 - 0.5) if rg2 > 0 else 0.0
    return math.sqrt(rg2), b / rg2 if rg2 > 0 else 0.0, k2


def analyse(box: Box, pos: np.ndarray, L: float, t_ns: float, minimum: int = 4) -> tuple[Frame, np.ndarray | None, list[int]]:
    labels, _, _ = clusters(box, pos, L)
    sizes = np.bincount(labels)
    big = int(np.argmax(sizes))
    members = [m for m in range(len(box.mols)) if labels[m] == big]
    agg_sizes = [int(s) for s in sizes if s >= minimum]
    in_agg = sum(agg_sizes)
    rg = asph = k2 = 0.0
    pts = None
    if len(members) >= minimum:
        pts = whole_cluster(box, pos, L, members)
        rg, asph, k2 = gyration(pts)
    fr = Frame(t_ns, sorted(agg_sizes, reverse=True), int(sizes.max()), float(np.mean(agg_sizes)) if agg_sizes else 0.0,
               1.0 - in_agg / len(box.mols), rg, asph, k2)
    return fr, pts, members


def radial_profile(box: Box, pos: np.ndarray, L: float, pts: np.ndarray, r_max: float = 4.0, dr: float = 0.15) -> dict:
    """Number density (beads per nm^3) of chain beads, head beads and water about the centre of the aggregate."""
    centre = pts.mean(axis=0)
    r = np.linalg.norm(_mic(pos - centre, L), axis=1)
    types = np.array(box.types)
    kinds = np.array(box.kind)
    edges = np.arange(0.0, r_max + dr, dr)
    vol = 4 / 3 * math.pi * (edges[1:] ** 3 - edges[:-1] ** 3)
    sel = {"tail": (kinds == "S") & (types == "T"), "head": (kinds == "S") & (types != "T"), "water": kinds == "W", "ion": kinds == "I"}
    out = {"r": ((edges[1:] + edges[:-1]) / 2).tolist()}
    for name, mask in sel.items():
        out[name] = (np.histogram(r[mask], edges)[0] / vol).tolist()
    return out


def frame_for_view(box: Box, pos: np.ndarray, L: float, members: list[int] | None) -> np.ndarray:
    """Surfactant bead positions (angstrom) with every molecule whole and the largest aggregate in the middle of the picture."""
    centre = np.full(3, L / 2)
    if members:
        centre = whole_cluster(box, pos, L, members).mean(axis=0)
    out = np.zeros((len(box.types), 3))
    for idx in box.mols:
        pts = _whole(pos, idx, box.adj, L)
        shift = _mic(pts.mean(axis=0) - centre, L) + centre - pts.mean(axis=0)
        out[idx] = pts + shift
    surf = [i for i, k in enumerate(box.kind) if k == "S"]
    return (out[surf] - centre) * 10.0


@dataclass
class Result:
    system: str
    species: dict[str, int]
    n_molecules: int
    box_nm: float
    temperature: float
    ns: float
    series: list[Frame] = field(default_factory=list)
    profile: dict = field(default_factory=dict)
    frames: list[list[float]] = field(default_factory=list)
    frame_times: list[float] = field(default_factory=list)
    beads: list[dict] = field(default_factory=list)
    bonds: list[tuple[int, int]] = field(default_factory=list)
    energy_kj: list[float] = field(default_factory=list)
    platform: str = ""


def run(system: str, composition: dict[str, int], ns: float = 20.0, n_side: int = 16, seed: int = 1, temperature: float = 310.0,
        n_view_frames: int = 40, sample_ps: float = 100.0, progress=None, threads: int | None = None, relax_steps: int = 4000) -> Result:
    """Self-assembly run: build, relax, simulate ``ns`` nanoseconds at 20 fs per step, analyse every ``sample_ps``; returns the summary and a trajectory for viewing.

    A graphics card is used when OpenMM finds one; if that platform fails or gives non-finite coordinates the run is repeated on the next platform, ending on the CPU."""
    candidates = platform_candidates()
    for i, name in enumerate(candidates):
        try:
            return _run_on(name, system, composition, ns, n_side, seed, temperature, n_view_frames, sample_ps, progress, threads, relax_steps)
        except Exception:
            if i == len(candidates) - 1:
                raise
    raise RuntimeError("no OpenMM platform")


def _run_on(platform: str, system: str, composition: dict[str, int], ns: float, n_side: int, seed: int, temperature: float,
            n_view_frames: int, sample_ps: float, progress, threads: int | None, relax_steps: int) -> Result:
    box = build_box(composition, n_side, seed)
    sim = make_simulation(box, temperature, 0.02, seed, threads, platform)
    relax(sim, relax_steps)
    dt = 0.02
    steps_per_sample = max(1, int(round(sample_ps / dt)))  # dt in ps
    total = int(round(ns * 1000.0 / dt))
    n_samples = max(1, total // steps_per_sample)
    res = Result(system, dict(composition), len(box.mols), box.length, temperature, ns, platform=platform)
    surf_idx = [i for i, k in enumerate(box.kind) if k == "S"]
    res.beads = [{"mol": box.mol[i], "type": box.types[i], "species": box.species[i]} for i in surf_idx]
    pos_of = {old: new for new, old in enumerate(surf_idx)}
    res.bonds = [(pos_of[a], pos_of[b]) for a, b in box.bonds]
    # frames for the viewer: spaced evenly in log time (the assembly happens early) and evenly in time, from the start of the run to the end
    n_geo = min(n_samples, max(2, n_view_frames * 4 // 9))
    view = {0, n_samples} | {int(round(x)) for x in np.geomspace(1, n_samples, n_geo)} | {int(round(x)) for x in np.linspace(0, n_samples, max(2, n_view_frames - n_geo))}
    prof_acc, n_prof = None, 0
    for k in range(n_samples + 1):
        if k > 0:
            sim.step(steps_per_sample)
        L = box_length_nm(sim)
        pos = positions_nm(sim)
        if not np.isfinite(pos).all():
            raise FloatingPointError("the simulation became unstable (non-finite coordinates)")
        t = k * steps_per_sample * dt / 1000.0
        fr, pts, members = analyse(box, pos, L, t)
        res.series.append(fr)
        res.energy_kj.append(_energy(sim))
        if k in view:
            res.frames.append(np.round(frame_for_view(box, pos, L, members if len(members) >= 4 else None), 1).ravel().tolist())
            res.frame_times.append(round(t, 3))
        if k > n_samples // 2 and len(members) >= 4:  # second half of the run is the production part
            p = radial_profile(box, pos, L, pts)
            if prof_acc is None:
                prof_acc = {kk: np.array(v) for kk, v in p.items()}
            else:
                for kk in p:
                    if kk != "r":
                        prof_acc[kk] = prof_acc[kk] + np.array(p[kk])
            n_prof += 1
        if progress:
            progress(k / n_samples, fr)
    if prof_acc is not None and n_prof:
        res.profile = {kk: (v / n_prof if kk != "r" else v).round(4).tolist() for kk, v in prof_acc.items()}
    res.box_nm = box_length_nm(sim)
    return res


def summary(res: Result, tail_fraction: float = 0.5) -> dict:
    """Averages over the last part of the run (the aggregation number of the aggregates, their size and shape)."""
    s = res.series[int(len(res.series) * (1 - tail_fraction)):]
    big = [f for f in s if f.largest >= 4]
    return {
        "molecules": res.n_molecules,
        "ns": res.ns,
        "aggregation_number": round(float(np.mean([f.mean_agg for f in s if f.mean_agg > 0])), 1) if any(f.mean_agg > 0 for f in s) else 0.0,
        "largest_aggregate": round(float(np.mean([f.largest for f in s])), 1),
        "aggregates": round(float(np.mean([len(f.sizes) for f in s])), 2),
        "free_fraction": round(float(np.mean([f.free_fraction for f in s])), 3),
        "rg_nm": round(float(np.mean([f.rg for f in big])), 3) if big else 0.0,
        "asphericity": round(float(np.mean([f.asphericity for f in big])), 3) if big else 0.0,
        "kappa2": round(float(np.mean([f.kappa2 for f in big])), 3) if big else 0.0,
    }


def to_dict(res: Result, extra: dict | None = None) -> dict:
    """The run as plain data (JSON-ready): the time series, the radial profile, the summary and the frames for viewing."""
    s = res.series
    return {
        "system": res.system, "platform": res.platform, "species": res.species, "molecules": res.n_molecules, "box_nm": round(res.box_nm, 3), "temperature_K": res.temperature, "ns": res.ns,
        "summary": summary(res),
        "series": {"t_ns": [round(f.t_ns, 4) for f in s], "largest": [f.largest for f in s], "mean_agg": [round(f.mean_agg, 2) for f in s],
                   "aggregates": [len(f.sizes) for f in s], "free_fraction": [round(f.free_fraction, 3) for f in s], "rg_nm": [round(f.rg, 3) for f in s],
                   "asphericity": [round(f.asphericity, 3) for f in s], "kappa2": [round(f.kappa2, 3) for f in s], "energy_kj_mol": [round(e, 1) for e in res.energy_kj]},
        "final_sizes": s[-1].sizes if s else [],
        "profile": res.profile,
        "beads": res.beads, "bonds": [list(b) for b in res.bonds],
        "frames": res.frames, "frame_t_ns": res.frame_times,
        **(extra or {}),
    }
