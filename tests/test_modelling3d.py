# Created by Muhammad Talaat, Faculty of Pharmacy, Ain Shams University
# SPDX-FileCopyrightText: 2026 Muhammad Talaat
# SPDX-License-Identifier: MIT

import numpy as np
import pytest

from stepan_lab import modelling3d as M
from stepan_lab import molecules, physchem


@pytest.fixture(scope="module")
def units():
    return {k: M.make_unit(k, n_confs=12) for k in ("sls", "cocobetaine", "eq_b", "cetylalcohol")}


def test_embedding_gives_hydrogen_complete_relaxed_conformers():
    m = M.embed("sls", n_confs=8)
    assert m.GetNumConformers() >= 2
    assert sum(1 for a in m.GetAtoms() if a.GetAtomicNum() == 1) == 25  # C12H25
    assert all(np.isfinite(M.conformer_energies(m)))
    assert M.embed("sls", n_confs=8).GetConformer(0).GetPositions() == pytest.approx(m.GetConformer(0).GetPositions())  # fixed seed


def test_counter_ions_are_dropped_from_the_model():
    m = M.embed("sls", n_confs=4)
    assert not any(a.GetSymbol() == "Na" for a in m.GetAtoms())


def test_the_extended_conformer_is_longer_than_the_lowest_one():
    m = M.embed("sls", n_confs=30)
    low, ext = M.lowest_conformer(m), M.extended_conformer(m)
    assert M._span(m, ext) >= M._span(m, low)
    d_low, d_ext = M.descriptors3d(m, low), M.descriptors3d(m, ext)
    assert d_ext["radius_of_gyration_A"] >= d_low["radius_of_gyration_A"]
    assert 0 <= d_ext["npr1"] <= d_ext["npr2"] <= 1.0
    assert d_ext["shown_above_minimum_kcal"] <= 12.0 + 1e-6
    assert d_low["shown_above_minimum_kcal"] == 0.0


def test_a_monomer_has_its_head_up_and_its_lowest_chain_end_on_the_plane(units):
    for u in units.values():
        assert u.xyz[:, 2].min() == pytest.approx(0.0, abs=1e-9)
        assert u.length == pytest.approx(u.xyz[:, 2].max())
    sls = units["sls"]
    polar = [i for i, s in enumerate(sls.symbols) if s in ("O", "S")]
    chain = [i for i, s in enumerate(sls.symbols) if s == "C"]
    assert sls.xyz[polar, 2].mean() > sls.xyz[chain, 2].mean()
    assert sls.renewable.sum() == 12  # every carbon of lauryl is renewable


def test_rotation_takes_a_direction_to_the_z_axis():
    for v in (np.array([1.0, 0, 0]), np.array([0, 1.0, 1.0]), np.array([0, 0, -1.0]), np.array([0.3, -0.5, 0.8])):
        r = M._rotation_to_z(v)
        assert r @ (v / np.linalg.norm(v)) == pytest.approx([0, 0, 1.0], abs=1e-9)
        assert np.linalg.det(r) == pytest.approx(1.0)


def test_overlapping_monomers_are_pushed_apart():
    a = np.array([[0.0, 0, 0], [1.5, 0, 0]])
    b = a + np.array([0.4, 0.3, 0.0])
    out = M.relax_overlaps([a, b])
    d = np.linalg.norm(out[0][:, None] - out[1][None], axis=-1).min()
    assert d >= 2.9
    assert out[0] - out[0][0] == pytest.approx(a - a[0])  # rigid: shapes are kept


@pytest.mark.parametrize("shape,n", [("sphere", 40), ("rod", 80), ("bilayer", 60)])
def test_aggregates_have_the_requested_monomers_and_no_overlap(units, shape, n):
    comp = {"sls": 0.7, "cocobetaine": 0.3}
    agg = M.build_aggregate(units, comp, shape, n, 55.0, 14.0, seed=5)
    assert agg.n == n and len(set(agg.resids)) == n
    assert agg.species.count("sls") == 28 and agg.species.count("cocobetaine") == 12 if shape == "sphere" else agg.n == n
    assert M.contacts_below(agg, 2.0) == 0
    assert len(agg.symbols) == len(agg.names) == len(agg.resnames) == len(agg.renewable) == len(agg.xyz)


def test_a_sphere_has_its_heads_outside_and_its_tails_inside(units):
    agg = M.build_aggregate(units, {"sls": 1.0}, "sphere", 40, 62.0, 13.0, seed=2)
    c = agg.xyz - agg.xyz.mean(axis=0)
    r = np.linalg.norm(c, axis=1)
    sym = np.array(agg.symbols)
    assert r[np.isin(sym, ["S", "O"])].mean() > r[sym == "C"].mean() + 2.0
    assert sym[np.argmin(r)] == "C"  # the core is chain
    assert np.ptp(c, axis=0).max() / np.ptp(c, axis=0).min() < 1.3  # roughly round


def test_a_rod_is_longer_than_wide_and_a_bilayer_has_two_leaflets(units):
    rod = M.build_aggregate(units, {"sls": 1.0}, "rod", 120, 50.0, 13.0, seed=2)
    ext = np.ptp(rod.xyz, axis=0)
    assert ext[0] > 1.4 * max(ext[1], ext[2])  # axis along x
    bil = M.build_aggregate(units, {"eq_b": 0.5, "cetylalcohol": 0.5}, "bilayer", 40, 42.0, 20.0, seed=2)
    y = bil.xyz[:, 1] - bil.xyz[:, 1].mean()
    heads = np.array(bil.symbols) != "C"
    assert y[heads].max() > 5 and y[heads].min() < -5  # heads on both faces
    assert np.ptp(bil.xyz[:, 0]) > 25 and np.ptp(bil.xyz[:, 2]) > 25  # the sheet spreads in x and z, its normal is y


def test_pdb_text_is_fixed_width_and_keeps_the_renewable_flag(units):
    agg = M.build_aggregate(units, {"sls": 1.0}, "sphere", 20, 62.0, 13.0, seed=1)
    lines = agg.pdb().splitlines()
    atoms = [ln for ln in lines if ln.startswith("HETATM")]
    assert lines[-1] == "END" and len(atoms) == len(agg.symbols)
    assert {len(ln) for ln in atoms} == {78}
    xyz = np.array([[float(ln[30:38]), float(ln[38:46]), float(ln[46:54])] for ln in atoms])
    assert xyz.mean(axis=0) == pytest.approx([0, 0, 0], abs=0.01)  # centred
    flags = np.array([float(ln[60:66]) for ln in atoms])
    assert set(flags) <= {0.0, 1.0}
    assert flags.sum() == 12 * 20
    assert {ln[17:20] for ln in atoms} == {"SLS"}


def test_residue_names_can_be_set(units):
    agg = M.build_aggregate(units, {"sls": 0.5, "cocobetaine": 0.5}, "sphere", 20, 55.0, 13.0, seed=1, resnames={"sls": "PRI", "cocobetaine": "SEC"})
    assert set(agg.resnames) == {"PRI", "SEC"}


def test_packing_for_follows_the_packing_model():
    n, a, p = M.packing_for({"sls": 1.0})
    assert (n, a) == (12, molecules.REGISTRY["sls"].head_a0)
    assert p == pytest.approx(physchem.mixed_packing_parameter([(1.0, 12, a)]))
    _, a2, p2 = M.packing_for({"sls": 1.0}, 0.8)
    assert a2 == pytest.approx(0.8 * a) and p2 == pytest.approx(p / 0.8)
    # an ester quat has two chains per head, so P is well above that of a single-chain surfactant
    assert M.packing_for({"eq_b": 1.0})[2] > 1.5 * M.packing_for({"sls": 1.0})[2]


def test_unknown_shape_is_rejected(units):
    with pytest.raises(ValueError):
        M.build_aggregate(units, {"sls": 1.0}, "cube", 10, 50.0, 13.0)
