# Created by Muhammad Talaat, Faculty of Pharmacy, Ain Shams University
# SPDX-FileCopyrightText: 2026 Muhammad Talaat
# SPDX-License-Identifier: MIT

import json
import re
from pathlib import Path

import numpy as np
import pytest
from scipy.spatial import cKDTree

from stepan_lab import card, molecules, physchem, viewer
from stepan_lab.provenance import CREDIT_LINE

ROOT = Path(__file__).resolve().parents[1]
CARD = ROOT / "docs" / "card"


@pytest.fixture(scope="module")
def loaded():
    return card.load_data()


def test_the_monomer_count_follows_the_packing_model():
    n, p, want = card.plan({"sls": 1.0}, "sphere")
    assert n == want == round(physchem.aggregation_number_sphere(12, molecules.REGISTRY["sls"].head_a0))
    n_rod, p_rod, _ = card.plan({"sls": 1.0}, "rod")
    assert n_rod > 3 * n * 0.95 and p_rod == pytest.approx(p / card.SALT_A0_FACTOR)  # a smaller head group: higher P, a longer rod
    assert card.plan({"eq_b": 0.5, "cetylalcohol": 0.5}, "bilayer")[0] == card.BILAYER_MONOMERS
    with pytest.raises(ValueError):
        card.plan({"sls": 1.0}, "cube")


def test_the_monomer_count_is_capped():
    n, _, want = card.plan({"btac": 1.0}, "rod")
    assert n <= card.MAX_MONOMERS and want >= n


def test_the_card_systems_and_shapes_are_all_present(loaded):
    assert [s["id"] for s in loaded["systems"]] == ["sls", "aos_betaine", "ester_quat"]
    shapes = {s["id"]: set(s["shapes"]) for s in loaded["systems"]}
    assert shapes == {"sls": {"sphere", "rod"}, "aos_betaine": {"sphere", "rod"}, "ester_quat": {"bilayer"}}
    for s in loaded["systems"]:
        assert s["svg"].lstrip().startswith("<svg") or "<svg" in s["svg"]
        assert all(re.fullmatch(r"#[0-9a-f]{6}", x["colour"]) for x in s["species"])
        for v in s["shapes"].values():
            assert v["pdb"].rstrip().endswith("END") and v["contacts"] == 0


def test_the_stored_models_have_no_close_contacts_and_match_the_manifest():
    man = json.loads((CARD / "models" / "manifest.json").read_text(encoding="utf-8"))
    for s in man["systems"]:
        for shape, fn in s["files"].items():
            atoms = [ln for ln in (CARD / "models" / fn).read_text(encoding="utf-8").splitlines() if ln.startswith("HETATM")]
            assert len(atoms) == s["shapes"][shape]["atoms"]
            xyz = np.array([[float(ln[30:38]), float(ln[38:46]), float(ln[46:54])] for ln in atoms])
            resid = np.array([int(ln[22:26]) for ln in atoms])
            assert len(set(resid)) == s["shapes"][shape]["monomers"]
            close = [(i, j) for i, j in cKDTree(xyz).query_pairs(2.0) if resid[i] != resid[j]]
            assert not close, (fn, len(close))


def test_the_aos_betaine_system_carries_the_unknown_renewable_flag_as_zero():
    atoms = [ln for ln in (CARD / "models" / "aos_betaine_sphere.pdb").read_text(encoding="utf-8").splitlines() if ln.startswith("HETATM")]
    by_res = {}
    for ln in atoms:
        by_res.setdefault(ln[17:20], []).append(float(ln[60:66]))
    assert set(by_res) == {"AOS", "COC"}
    assert sum(by_res["AOS"]) == 0.0  # the renewable share of the olefin sulfonates is not derived, so none is claimed
    assert sum(by_res["COC"]) > 0.0


def test_every_structure_has_a_3d_record(loaded):
    recs = {r["key"]: r for r in loaded["molecules"]}
    assert set(recs) == set(molecules.REGISTRY)
    for key, r in recs.items():
        assert "V2000" in r["sdf"] or "V3000" in r["sdf"]
        assert r["rg"] > 1.5 and 0 <= r["npr1"] <= r["npr2"] <= 1.0
        assert r["descriptors3d"]["shown_above_minimum_kcal"] <= 12.0 + 1e-6
    assert recs["sls"]["renewable"] and len(recs["sls"]["renewable"]) == 12
    assert recs["aos_ene"]["renewable"] == [] and recs["aos_ene"]["renew"] == "not derived"


def test_a_custom_aggregate_can_be_built():
    system, info = card.build_custom("sls", "cocobetaine", 0.33, "sphere", n_confs=8)
    assert [x["resn"] for x in system["species"]] == ["PRI", "SEC"]
    assert info["monomers"] >= 12 and info["close_contacts"] == 0
    assert set(info["composition"]) == {"sls", "cocobetaine"}
    _, one = card.build_custom("sls", "sls", 0.5, "rod", n_confs=8)
    assert set(one["composition"]) == {"sls"}
    _, alone = card.build_custom("capb", None, 0.0, "bilayer", n_confs=8)
    assert set(alone["composition"]) == {"capb"}


def test_the_page_is_self_contained_and_carries_the_data(loaded):
    page = viewer.page(loaded)
    assert CREDIT_LINE in page and "<title>Stepan Surfactant Cheminformatics</title>" in page
    assert page.count("</script>") == 2  # the library and the page script; the data cannot close the tag
    assert not re.search(r"<script[^>]+src=|<link[^>]+href=|@import|url\(http", page)  # nothing is loaded from the network
    data = json.loads(re.search(r"const DATA=(\{.*?\});\s*\(function", page, re.DOTALL).group(1))
    assert len(data["systems"]) == 3 and len(data["molecules"]) == len(molecules.REGISTRY)


def test_the_compact_page_has_no_header(loaded):
    page = viewer.page(loaded, compact=True)
    assert "<header>" not in page and 'class="theme"' not in page and 'id="v"' in page


def test_the_committed_page_is_the_page_the_builder_writes(loaded):
    assert (CARD / "index.html").read_text(encoding="utf-8") == viewer.page(loaded)
    assert (ROOT / "docs" / ".nojekyll").exists()
    assert 'url=card/' in (ROOT / "docs" / "index.html").read_text(encoding="utf-8")  # the root of the Pages site leads to the card


def test_the_vendored_viewer_keeps_its_licence():
    assert "3Dmol" in (CARD / "vendor" / "3Dmol-min.js").read_text(encoding="utf-8")[:2000] or (CARD / "vendor" / "3Dmol-min.js").stat().st_size > 100_000
    assert "BSD" in (CARD / "vendor" / "3Dmol-LICENSE.txt").read_text(encoding="utf-8")


def test_the_images_the_readme_shows_exist():
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    paths = set(re.findall(r'(?:src|srcset)="(docs/[^"]+)"', text))
    assert {"docs/card/stepan_card_animated-dark.gif", "docs/card/stepan_card_animated-light.gif"} <= paths
    for p in paths:
        assert (ROOT / p).stat().st_size > 10_000, p


def test_the_stored_simulations_are_attached_to_every_card_system(loaded):
    for s in loaded["systems"]:
        m = s["md"]
        assert len(m["frames"]) == len(m["frame_t_ns"]) >= 20
        assert all(len(f) == 3 * len(m["beads"]) for f in m["frames"])
        assert {k: len(v) for k, v in m["series"].items()}.keys() == {"t_ns", "largest", "mean_agg", "aggregates", "free_fraction"}
        assert all(b["species"] in m["species_names"] for b in m["beads"])
        assert all(0 <= a < len(m["beads"]) and 0 <= b < len(m["beads"]) for a, b in m["bonds"])


def test_the_page_has_the_dynamics_controls(loaded):
    page = viewer.page(loaded)
    for needle in ('data-mode="md"', 'data-mode="model"', 'id="play"', 'id="tslider"', 'data-colour="bead"', 'id="spark"'):
        assert needle in page, needle


def test_the_notebook_count_on_the_page_matches_the_folder(loaded):
    n = len(list((ROOT / "notebooks").glob("*.py")))
    assert ("13" if n == 13 else str(n)) == dict((lab, num) for num, lab, _ in loaded["stats"])["notebooks"]
    assert n == 13
