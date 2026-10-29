# Created by Muhammad Talaat, Faculty of Pharmacy, Ain Shams University
# SPDX-FileCopyrightText: 2026 Muhammad Talaat
# SPDX-License-Identifier: MIT

import json
import math
from collections import Counter
from pathlib import Path

import numpy as np
import pytest

from stepan_lab import card, md, mdcharts, molecules

ROOT = Path(__file__).resolve().parents[1]
MD_DIR = ROOT / "docs" / "card" / "md"


@pytest.mark.parametrize("key", list(molecules.REGISTRY))
def test_every_structure_is_coarse_grained_into_a_connected_molecule(key):
    cg = md.coarse_grain(key)
    m = molecules._largest_fragment(molecules.clean(molecules.mol(key)))
    atoms = sorted(a for b in cg.beads for a in b.atoms)
    assert atoms == list(range(m.GetNumAtoms()))  # every heavy atom of the amphiphile is in exactly one bead
    assert cg.heavy_atoms == m.GetNumAtoms()
    seen, todo = {0}, [0]
    adj = {i: [] for i in range(len(cg.beads))}
    for a, b in cg.bonds:
        adj[a].append(b)
        adj[b].append(a)
    while todo:
        for n in adj[todo.pop()]:
            if n not in seen:
                seen.add(n)
                todo.append(n)
    assert len(seen) == len(cg.beads)  # one connected molecule
    assert cg.n_tail_beads >= 2 and all(cg.beads[i].type == "T" for i in range(cg.n_tail_beads)) or cg.root >= 0


def test_bead_types_follow_charge_and_chain():
    sls = md.coarse_grain("sls")
    assert sls.sequence == "T T T A" and sls.charge == -1 and sls.ions == ("NA", 1)
    assert md.coarse_grain("btac").sequence.endswith("C") and md.coarse_grain("btac").ions == ("CL", 1)
    betaine = md.coarse_grain("cocobetaine")
    assert betaine.sequence == "T T T C A" and betaine.charge == 0 and betaine.ions is None  # a zwitterion needs no counter-ion
    assert md.coarse_grain("dsls").charge == -2 and md.coarse_grain("dsls").ions == ("NA", 2)
    eq = md.coarse_grain("eq_b")
    assert eq.n_tail_beads == 8 and eq.charge == 1  # two chains of four beads


def test_chain_length_sets_the_number_of_chain_beads():
    assert md.coarse_grain("sls").n_tail_beads == 3      # C12
    assert md.coarse_grain("ctac").n_tail_beads == 4     # C16
    assert md.coarse_grain("btac").n_tail_beads == 6     # C22
    assert md.coarse_grain("gcc_c8").n_tail_beads == 2   # C8


def test_the_pair_table_is_symmetric_and_has_the_published_levels():
    eps, sig = md.pair_table()
    assert np.allclose(eps, eps.T) and np.allclose(sig, sig.T)
    i = {t: md.TYPES.index(t) for t in md.TYPES}
    assert eps[i["W"], i["W"]] == 5.0 and eps[i["T"], i["T"]] == 3.5
    assert eps[i["T"], i["W"]] == 2.0 and sig[i["T"], i["W"]] == 0.62
    assert sig[i["T"], i["T"]] == md.SIGMA and sig[i["W"], i["W"]] == md.SIGMA


def test_the_mapping_drawing_is_an_svg():
    assert md.draw_mapping("capb").lstrip().startswith("<?xml") or "<svg" in md.draw_mapping("capb")


def test_a_box_has_the_right_composition_density_and_charge():
    box = md.build_box({"sls": 20, "cocobetaine": 10}, 10, seed=3)
    assert box.n == 10**3 and len(box.mols) == 30
    kinds = Counter(box.kind)
    assert kinds["S"] == 20 * 4 + 10 * 5 and kinds["I"] == 20  # a sodium for every sulfate, none for the betaine
    assert sum(box.charges) == pytest.approx(0.0)
    sites = {tuple(np.floor(p / md.SPACING).astype(int)) for p in box.pos}
    assert len(sites) == box.n  # no two beads on one site
    assert box.length == pytest.approx(10 * md.SPACING)
    for idx in box.mols:  # bonded beads are one lattice step apart
        pass
    d = [np.linalg.norm(md._mic(box.pos[a] - box.pos[b], box.length)) for a, b in box.bonds]
    assert max(d) == pytest.approx(md.SPACING)


def test_the_box_is_reproducible_and_too_small_a_box_is_refused():
    a, b = md.build_box({"sls": 10}, 8, seed=5), md.build_box({"sls": 10}, 8, seed=5)
    assert np.array_equal(a.pos, b.pos)
    with pytest.raises(RuntimeError):
        md.build_box({"soleil_eq": 40}, 6, seed=1)


def test_the_box_size_follows_the_concentration():
    n = md.box_size_for({"sls": 30})
    c = 30 / (0.6022 * (n * md.SPACING) ** 3)
    assert 0.15 < c <= 0.25
    assert md.box_size_for({"sls": 100}) > md.box_size_for({"sls": 30})


def test_gyration_separates_a_rod_from_a_sphere():
    rng = np.random.default_rng(0)
    sphere = rng.normal(size=(400, 3))
    rod = rng.normal(size=(400, 3)) * np.array([6.0, 1.0, 1.0])
    rg_s, b_s, k_s = md.gyration(sphere)
    rg_r, b_r, k_r = md.gyration(rod)
    assert b_s < 0.1 and k_s < 0.05 and b_r > 0.8 and k_r > 0.7
    assert rg_s == pytest.approx(math.sqrt(3), rel=0.15)


def test_aggregates_are_found_across_the_periodic_boundary():
    box = md.build_box({"sls": 12}, 8, seed=2)
    L = box.length
    pos = np.zeros_like(box.pos)
    for k, idx in enumerate(box.mols):  # two stacks of six molecules, one of them straddling the box edge
        base = np.array([0.05, 2.0, 2.0]) if k < 6 else np.array([L - 0.2, 3.0, 2.0]) if k < 12 else np.zeros(3)
        for j, i in enumerate(idx):
            pos[i] = base + np.array([0.0, 0.0, 0.45 * j + (0 if k < 6 else 0.0)]) + np.array([0.0, 0.2 * (k % 6), 0.0])
    labels, _, _ = md.clusters(box, np.mod(pos, L), L)
    assert len(set(labels)) <= 2
    pts = md.whole_cluster(box, np.mod(pos, L), L, list(range(12)))
    assert np.ptp(pts[:, 0]) < L / 2  # made whole: not spread over the box


def test_a_short_simulation_runs_and_reports_aggregation():
    md.PLATFORM = "CPU"
    try:
        res = md.run("test", {"sls": 12}, ns=0.06, n_side=8, seed=2, sample_ps=20.0, n_view_frames=3, relax_steps=300)
    finally:
        md.PLATFORM = None
    d = md.to_dict(res)
    json.dumps(d)
    assert d["molecules"] == 12 and len(d["series"]["t_ns"]) == 4 and d["series"]["t_ns"][0] == 0.0  # the start and three samples
    assert all(np.isfinite(d["series"]["energy_kj_mol"]))
    assert len(d["frames"]) >= 2 and d["frame_t_ns"][0] == 0.0 and len(d["frames"][0]) == 3 * len(d["beads"]) == 3 * 12 * 4
    assert 0 <= d["summary"]["free_fraction"] <= 1 and d["summary"]["largest_aggregate"] >= 1
    view = card.md_view(d)
    assert set(view) >= {"beads", "bonds", "frames", "frame_t_ns", "series", "species_names"}


@pytest.mark.skipif(not MD_DIR.exists(), reason="stored simulations not built")
@pytest.mark.parametrize("system", ["sls", "aos_betaine", "ester_quat"])
def test_the_stored_simulations_are_complete_and_sensible(system):
    d = json.loads((MD_DIR / f"{system}.json").read_text(encoding="utf-8"))
    s = d["summary"]
    assert d["meta"]["time_step_fs"] == 20 and d["temperature_K"] == 310.0
    assert len(d["series"]["t_ns"]) >= 100 and d["series"]["t_ns"][0] == 0.0 and d["series"]["t_ns"][-1] == pytest.approx(d["ns"], rel=0.01)
    assert len(d["frames"]) == len(d["frame_t_ns"]) >= 20
    assert all(len(f) == 3 * len(d["beads"]) for f in d["frames"])
    assert np.isfinite(np.array(d["frames"])).all() and np.isfinite(d["series"]["energy_kj_mol"]).all()
    assert s["largest_aggregate"] >= 10 and 0 <= s["free_fraction"] < 0.3
    assert 0 <= s["asphericity"] <= 1 and 0 <= s["kappa2"] <= 1
    # the run started from random chains: in the dilute systems the molecules are far less aggregated at the start than at the end
    # (the ester quat box is dense, so its chains already touch at the start)
    assert d["frame_t_ns"][0] == 0.0 and d["series"]["largest"][0] <= d["series"]["largest"][-1]
    if system != "ester_quat":
        assert d["series"]["largest"][0] < 0.5 * d["series"]["largest"][-1]
    # the radial density has chains inside and heads outside of them
    p = d["profile"]
    if p:
        r, tail, head = np.array(p["r"]), np.array(p["tail"]), np.array(p["head"])
        assert r[np.argmax(tail)] < r[np.argmax(head)] + 1e-9


def test_the_charts_and_tables_build_from_a_result():
    md.PLATFORM = "CPU"
    try:
        res = md.run("test", {"sls": 10}, ns=0.04, n_side=8, seed=1, sample_ps=20.0, n_view_frames=2, relax_steps=200)
    finally:
        md.PLATFORM = None
    d = md.to_dict(res)
    for ch in (mdcharts.size_chart(d), mdcharts.shape_chart(d), mdcharts.free_chart(d)):
        assert ch.to_dict()["mark"]
    assert not mdcharts.summary_table({"x": d}).empty and mdcharts.bead_table("capb").shape[0] == len(md.coarse_grain("capb").beads)
    assert mdcharts.interaction_table().shape == (6, 6)


def test_a_molecule_longer_than_half_the_box_is_made_whole_along_its_bonds():
    L = 3.9
    chain = [0.47 * np.array([i, 0.0, 0.0]) for i in range(12)]  # 5.2 nm long: longer than the box itself
    pos = np.mod(np.array(chain) + 0.3, L)
    adj = {i: [j for j in (i - 1, i + 1) if 0 <= j < 12] for i in range(12)}
    whole = md._whole(pos, list(range(12)), adj, L)
    steps = np.linalg.norm(np.diff(whole, axis=0), axis=1)
    assert steps == pytest.approx(0.47, abs=1e-9)


def test_the_ester_quat_box_carries_the_bond_lists():
    box = md.build_box({"eq_b": 4}, 8, seed=2)
    assert set(box.adj) == {i for idx in box.mols for i in idx}
    assert sum(len(v) for v in box.adj.values()) == 2 * len(box.bonds)
