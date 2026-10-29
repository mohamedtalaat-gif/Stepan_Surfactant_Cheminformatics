# Created by Muhammad Talaat, Faculty of Pharmacy, Ain Shams University
# SPDX-FileCopyrightText: 2026 Muhammad Talaat
# SPDX-License-Identifier: MIT
"""Build the 3D models and the interactive card in docs/card/.

    python scripts/build_card.py

Writes docs/card/index.html (one self-contained page), and in docs/card/models: the aggregates as PDB files (ready for PyMOL),
molecules.sdf, molecules.json, manifest.json (read by the notebooks and by scripts/render_card.py) and stepan_lab.pml.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from stepan_lab import card, viewer

CARD = ROOT / "docs" / "card"

PML = """# Created by Muhammad Talaat, Faculty of Pharmacy, Ain Shams University
# PyMOL script for the five aggregate models in this folder (geometric models; not molecular dynamics).
#   cd docs/card/models
#   pymol stepan_lab.pml
# Show another model with:  disable all  then  enable aos_betaine_rod
bg_color white
load sls_sphere.pdb
load sls_rod.pdb
load aos_betaine_sphere.pdb
load aos_betaine_rod.pdb
load ester_quat_bilayer.pdb
hide everything
show spheres
set sphere_scale, 0.6
set_color c_sls, [0.208, 0.816, 0.725]
set_color c_aos, [1.000, 0.478, 0.565]
set_color c_eq, [0.357, 0.616, 1.000]
set_color c_cet, [0.706, 0.549, 1.000]
set_color c_head, [1.000, 0.784, 0.239]
color c_sls, resn SLS and elem C
color c_aos, resn AOS and elem C
color c_sls, resn COC and elem C
color c_eq, resn EQ_ and elem C
color c_cet, resn CET and elem C
color c_head, not elem C
set ray_shadows, 1
set depth_cue, 1
disable all
enable aos_betaine_sphere
zoom
# The B-factor column marks the carbon atoms that come from renewable sources (1.0) or not (0.0):
# color grey60, elem C
# color green, elem C and b > 0.5
"""


def main() -> None:
    card.build_all()
    (card.MODELS / "stepan_lab.pml").write_text(PML, encoding="utf-8")
    (CARD / "index.html").write_text(viewer.page(card.load_data()), encoding="utf-8")
    (CARD.parent / ".nojekyll").write_text("", encoding="utf-8")
    print("card:", round((CARD / "index.html").stat().st_size / 1e6, 2), "MB")


if __name__ == "__main__":
    main()
