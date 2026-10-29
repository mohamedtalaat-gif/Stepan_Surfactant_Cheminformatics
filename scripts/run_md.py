# Created by Muhammad Talaat, Faculty of Pharmacy, Ain Shams University
# SPDX-FileCopyrightText: 2026 Muhammad Talaat
# SPDX-License-Identifier: MIT
"""Run the coarse-grained molecular dynamics of the three systems of the card and store the results in docs/card/md/.

    python scripts/run_md.py                 # all three systems
    python scripts/run_md.py sls --ns 20     # one system, shorter

The runs start from random chains on a lattice, so every micelle or bilayer in the results formed during the simulation.
A GPU (CUDA or OpenCL) makes the full runs take minutes; on a CPU they take hours.
"""

from __future__ import annotations

import argparse
import json
import platform
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import openmm

from stepan_lab import md

OUT = ROOT / "docs" / "card" / "md"

# id: (composition in molecules, lattice sites per edge, nanoseconds, seed, description, picoseconds between analyses)
SYSTEMS = {
    "sls": ({"sls": 100}, 16, 60.0, 1, "100 sodium lauryl sulfate", 100.0),
    "aos_betaine": ({"aos_ene": 40, "aos_hydroxy": 27, "cocobetaine": 33}, 16, 60.0, 2, "AOS (40 + 27) with 33 coco-betaine", 100.0),
    "ester_quat": ({"eq_b": 75, "cetylalcohol": 75}, 12, 100.0, 3, "75 ester quat with 75 cetyl alcohol", 100.0),
}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("only", nargs="*", choices=list(SYSTEMS))
    ap.add_argument("--ns", type=float, default=None, help="override the length of every run")
    ap.add_argument("--platform", default=None)
    args = ap.parse_args()
    if args.platform:
        md.PLATFORM = args.platform
    OUT.mkdir(parents=True, exist_ok=True)
    todo = args.only or list(SYSTEMS)
    for sid in todo:
        comp, n_side, ns, seed, text, every = SYSTEMS[sid]
        ns = args.ns or ns
        t0 = time.time()
        last = [0.0]

        def progress(frac, fr):
            if frac - last[0] >= 0.05:
                last[0] = frac
                print(f"  {sid}: {100 * frac:3.0f}%  t={fr.t_ns:6.1f} ns  largest={fr.largest:3d}  aggregates={len(fr.sizes)}  free={fr.free_fraction:.2f}", flush=True)

        print(f"{sid}: {text}, {ns} ns, platform {md.platform_name()}", flush=True)
        res = md.run(sid, comp, ns=ns, n_side=n_side, seed=seed, sample_ps=every, progress=progress)
        meta = {"description": text, "platform": res.platform, "openmm": openmm.__version__, "python": platform.python_version(), "seed": seed,
                "time_step_fs": 20, "sample_ps": every, "wall_minutes": round((time.time() - t0) / 60, 1), "lattice_sites_per_edge": n_side}
        data = md.to_dict(res, {"meta": meta})
        (OUT / f"{sid}.json").write_text(json.dumps(data, separators=(",", ":")), encoding="utf-8")
        print(f"  summary: {data['summary']}  ({meta['wall_minutes']} min)", flush=True)


if __name__ == "__main__":
    main()
