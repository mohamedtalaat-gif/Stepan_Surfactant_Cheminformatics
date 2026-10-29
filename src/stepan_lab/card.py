# Created by Muhammad Talaat, Faculty of Pharmacy, Ain Shams University
# SPDX-FileCopyrightText: 2026 Muhammad Talaat
# SPDX-License-Identifier: MIT
"""The 3D systems of the card and of the molecules lab: build them once, read them back, or build one on request.

``build_all`` (run by scripts/build_card.py) writes the aggregate models to docs/card/models; ``load_data`` reads them back in the
form that viewer.page expects; ``build_custom`` builds one aggregate of any two structures from the registry.
"""

from __future__ import annotations

import json
from functools import cache
from pathlib import Path

from rdkit import Chem

from . import data, molecules, physchem
from . import modelling3d as M

ROOT = Path(__file__).resolve().parents[2]
MODELS = ROOT / "docs" / "card" / "models"
MD_DIR = ROOT / "docs" / "card" / "md"

SPECIES = {"SLS": ("Sodium lauryl sulfate", "#35d0ba"), "AOS": ("Alpha olefin sulfonate", "#ff7a90"), "COC": ("Coco-betaine", "#35d0ba"),
           "EQ_": ("Ester quat", "#5b9dff"), "CET": ("Cetyl alcohol", "#b48cff")}
SYSTEMS = [
    dict(id="sls", name="Sodium lauryl sulfate", caption="the reference anionic", skeleton="sls", species=["SLS"],
         composition={"sls": 1.0}, shapes=["sphere", "rod"]),
    dict(id="aos_betaine", name="AOS with coco-betaine", caption="2 : 1, the seminar's core system", skeleton="aos_ene", species=["AOS", "COC"],
         composition={"aos_ene": 0.40, "aos_hydroxy": 0.27, "cocobetaine": 0.33}, shapes=["sphere", "rod"]),
    dict(id="ester_quat", name="Ester quat with cetyl alcohol", caption="1 : 1, the conditioner's lamellar phase", skeleton="eq_b", species=["EQ_", "CET"],
         composition={"eq_b": 0.5, "cetylalcohol": 0.5}, shapes=["bilayer"]),
]
SALT_A0_FACTOR = 0.80  # salt screening is represented by a head-group area 20% smaller (an assumption)
BILAYER_MONOMERS = 80
MAX_MONOMERS = 400
SHAPE_LABEL = {"sphere": "spherical micelle", "rod": "rod-like micelle, salt added", "bilayer": "bilayer patch"}
CUSTOM_COLOURS = ("#35d0ba", "#ff7a90")
BUILDABLE = tuple(k for k in molecules.REGISTRY if k != "steareth20")  # a 20-unit ethoxylate chain has no compact head to place outward


def skeleton(key: str) -> str:
    """Structure drawing as inline SVG that takes the colour of the page text."""
    svg = molecules.draw_svg(key, size=(300, 130))
    return svg.replace("#000000", "currentColor").split("?>", 1)[-1]


def plan(comp: dict[str, float], shape: str) -> tuple[int, float, int]:
    """(monomers used, packing parameter, monomers the packing model asks for) for a shape of the mixture."""
    if shape == "sphere":
        n_mean, a_mean, p = M.packing_for(comp)
        want = physchem.aggregation_number_sphere(n_mean, a_mean)
    elif shape == "rod":
        n_mean, a_mean, p = M.packing_for(comp, SALT_A0_FACTOR)
        want = 3 * physchem.aggregation_number_sphere(n_mean, a_mean)
    elif shape == "bilayer":
        _, _, p = M.packing_for(comp)
        want = BILAYER_MONOMERS
    else:
        raise ValueError(shape)
    return max(12, min(int(round(want)), MAX_MONOMERS)), p, int(round(want))


def build_shape(comp: dict[str, float], shape: str, units: dict[str, M.Unit], seed: int = 5,
                resnames: dict[str, str] | None = None) -> tuple[M.Aggregate, dict]:
    n, p, want = plan(comp, shape)
    _, a_mean, _ = M.packing_for(comp)
    chain_len = sum(units[k].length * x for k, x in comp.items()) / sum(comp.values())
    agg = M.build_aggregate(units, comp, shape, n, a_mean, chain_len, seed=seed, resnames=resnames)
    summ = M.aggregate_summary(agg, p)
    summ["model_monomers"] = want
    return agg, summ


def _shape_entry(agg: M.Aggregate, summ: dict, shape: str) -> dict:
    return {"pdb": agg.pdb(), "label": SHAPE_LABEL[shape], "monomers": summ["monomers"], "atoms": summ["atoms"], "radius": summ["radius_A"],
            "p": f"{summ['packing_parameter']:.2f}", "contacts": summ["close_contacts"]}


def build_custom(primary: str, secondary: str | None, x_secondary: float, shape: str, n_confs: int = 30) -> tuple[dict, dict]:
    """One aggregate of two registry structures; returns the viewer entry (``system``) and the summary of the build."""
    comp = {primary: 1.0 - x_secondary} if not secondary or x_secondary <= 0 else {primary: 1.0 - x_secondary, secondary: x_secondary}
    if secondary == primary:
        comp = {primary: 1.0}
    units = {k: M.make_unit(k, n_confs=n_confs) for k in comp}
    names = dict(zip(comp, ("PRI", "SEC")))
    agg, summ = build_shape(comp, shape, units, resnames=names)
    species = [{"resn": names[k], "name": molecules.REGISTRY[k].name, "colour": c} for k, c in zip(comp, CUSTOM_COLOURS)]
    system = {"id": "custom", "name": " with ".join(molecules.REGISTRY[k].name for k in comp), "caption": "", "svg": "", "species": species,
              "shapes": {shape: _shape_entry(agg, summ, shape)}}
    return system, {**summ, "pdb": agg.pdb(), "composition": comp}


@cache
def molecule_record(key: str, n_confs: int = 30) -> dict:
    """The most extended MMFF94 conformer within 12 kcal/mol of the lowest, with its 3D descriptors, in the form viewer.page expects.

    In vacuum the lowest conformer of a surfactant folds its chain over on itself; the extended one is the shape the chain takes at an interface."""
    s = molecules.REGISTRY[key]
    m = M.embed(key, n_confs=n_confs)
    cid = M.extended_conformer(m, window_kcal=12.0, compact=1.0)
    d3 = M.descriptors3d(m, cid)
    d2 = molecules.descriptors(key)
    flags = {a.GetIdx(): a.GetAtomMapNum() == molecules.RENEWABLE for a in molecules.mol(key).GetAtoms()}
    ren = [i for i in range(m.GetNumAtoms()) if m.GetAtomWithIdx(i).GetAtomicNum() > 1 and flags.get(i, False)] if s.renewable_known else []
    rc, tc = molecules.carbon_counts(molecules.mol(key))
    m.SetProp("_Name", s.name)
    return {"key": key, "name": s.name, "family": s.family, "formula": d2["formula"], "mw": d2["mw_amphiphile"], "rg": d3["radius_of_gyration_A"],
            "npr1": d3["npr1"], "npr2": d3["npr2"], "renew": f"{rc}/{tc}" if s.renewable_known else "not derived",
            "sdf": Chem.MolToMolBlock(m, confId=cid), "renewable": ren, "descriptors3d": d3}


def stats() -> list[tuple[str, str, str]]:
    return [(str(len(data.slides())), "slides recorded", "Every slide of the six decks has a line in the ledger"),
            (str(len(data.chart_index())), "charts rebuilt", "Read from the drawing inside each slide"),
            (str(len(data.formula_index())), "formulas", "Transcribed with deck and page"),
            (str(len(data.products())), "products", "With INCI name, class and printed properties"),
            (str(len(molecules.REGISTRY)), "structures", "Drawn from INCI names; shown here in 3D"),
            ("13", "notebooks", "A start page, six sessions and six labs")]


def build_all(out: Path = MODELS) -> dict:
    """Build the aggregates and the molecule records and write them to ``out``; returns the manifest."""
    out.mkdir(parents=True, exist_ok=True)
    units: dict[str, M.Unit] = {}
    manifest: dict = {"systems": []}
    for S in SYSTEMS:
        for k in S["composition"]:
            if k not in units:
                units[k] = M.make_unit(k, n_confs=40)
        files, shapes = {}, {}
        for shape in S["shapes"]:
            agg, summ = build_shape(S["composition"], shape, units)
            fn = f"{S['id']}_{shape}.pdb"
            (out / fn).write_text(agg.pdb() + "\n", encoding="utf-8")
            files[shape] = fn
            shapes[shape] = {k: summ[k] for k in ("monomers", "atoms", "radius_A", "packing_parameter", "close_contacts")}
            print(f"{S['id']:12s} {shape:8s} {summ}")
        manifest["systems"].append({"id": S["id"], "name": S["name"], "caption": S["caption"], "skeleton": S["skeleton"], "files": files,
                                    "species": {r: SPECIES[r][1] for r in S["species"]}, "species_names": {r: SPECIES[r][0] for r in S["species"]}, "shapes": shapes})
    records, sdf = [], Chem.SDWriter(str(out / "molecules.sdf"))
    for key in molecules.REGISTRY:
        rec = molecule_record(key)
        records.append(rec)
        sdf.write(Chem.MolFromMolBlock(rec["sdf"], removeHs=False))
    sdf.close()
    (out / "molecules.json").write_text(json.dumps(records, separators=(",", ":")), encoding="utf-8")
    manifest["stats"] = [[n, l] for n, l, _ in stats()]
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    return manifest


def load_md(system_id: str, folder: Path = MD_DIR) -> dict | None:
    """The stored molecular-dynamics result of a system (written by scripts/run_md.py), or None."""
    f = folder / f"{system_id}.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else None


def md_view(d: dict) -> dict:
    """The part of a molecular-dynamics result that the 3D viewer needs: the beads, the bonds, the frames and the time series."""
    s = d["series"]
    names = {b["species"] for b in d["beads"]}
    return {"molecules": d["molecules"], "box_nm": d["box_nm"], "beads": d["beads"], "bonds": d["bonds"], "frames": d["frames"], "frame_t_ns": d["frame_t_ns"],
            "series": {k: s[k] for k in ("t_ns", "largest", "mean_agg", "aggregates", "free_fraction")},
            "species_names": {k: molecules.REGISTRY[k].name for k in sorted(names) if k in molecules.REGISTRY}}


def load_data(models: Path = MODELS, md_folder: Path = MD_DIR) -> dict:
    """Read the models written by ``build_all`` in the form that viewer.page expects."""
    man = json.loads((models / "manifest.json").read_text(encoding="utf-8"))
    systems = []
    for s in man["systems"]:
        shapes = {}
        for shape, fn in s["files"].items():
            v = s["shapes"][shape]
            shapes[shape] = {"pdb": (models / fn).read_text(encoding="utf-8"), "label": SHAPE_LABEL[shape], "monomers": v["monomers"], "atoms": v["atoms"],
                             "radius": v["radius_A"], "p": f"{v['packing_parameter']:.2f}", "contacts": v["close_contacts"]}
        entry = {"id": s["id"], "name": s["name"], "caption": s["caption"], "svg": skeleton(s["skeleton"]), "shapes": shapes,
                 "species": [{"resn": r, "name": s["species_names"][r], "colour": c} for r, c in s["species"].items()]}
        run = load_md(s["id"], md_folder)
        if run:
            entry["md"] = md_view(run)
        systems.append(entry)
    mols = json.loads((models / "molecules.json").read_text(encoding="utf-8"))
    return {"systems": systems, "molecules": mols, "stats": stats(), "tile_mol_svg": skeleton("capb")}
