# Created by Muhammad Talaat, Faculty of Pharmacy, Ain Shams University
# SPDX-FileCopyrightText: 2026 Muhammad Talaat
# SPDX-License-Identifier: MIT
"""Change every control of every notebook, one at a time, and report the controls that change nothing.

    python scripts/audit_controls.py                      # all notebooks
    python scripts/audit_controls.py notebooks/lab_salt_curves.py

A notebook is run from top to bottom with the value of one control replaced; the rendered output of every cell is compared with the run
before. A control that changes no cell in any setting of the other dropdowns is dead; one that changes nothing under some setting of
another control (a slider that only matters for two of seven systems, say) is conditional. Both are listed so that they can be read.
"""

from __future__ import annotations

import contextlib
import importlib.util
import io
import re
import sys
from multiprocessing import Pool
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

NOISE = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}|[0-9a-f]{32}|object-id='[^']*'|data-cell-id='[^']*'")  # ids drawn at random on every render
SKIP = {"run_button", "button", "file", "form", "table", "altair_chart", "tabs", "refresh", "microphone", "code_editor"}


def load(path: Path):
    spec = importlib.util.spec_from_file_location("audited_" + path.stem, path)
    module = importlib.util.module_from_spec(spec)
    with contextlib.redirect_stdout(io.StringIO()):
        spec.loader.exec_module(module)
    return module


def audit(path_str: str) -> dict:
    from marimo._plugins.ui._core.ui_element import UIElement

    path = Path(path_str)
    overrides: dict[str, object] = {}
    original = UIElement.value.fget

    def key(el) -> str:
        return f"{type(el).__name__}|{re.sub(r'<[^>]+>', '', str(el._args.label or '')).strip()}"

    def patched(self):
        k = key(self)
        return overrides[k] if k in overrides else original(self)

    UIElement.value = property(patched)
    module = load(path)
    cache: dict[tuple, list[str]] = {}

    def run(over: dict) -> list[str]:
        sig = tuple(sorted((k, repr(v)) for k, v in over.items()))
        if sig not in cache:
            overrides.clear()
            overrides.update(over)
            with contextlib.redirect_stdout(io.StringIO()):
                outputs, defs = module.app.run()
            texts = []
            for o in outputs:
                try:
                    texts.append(NOISE.sub("", str(o._mime_()[1])) if o is not None else "")
                except Exception:
                    texts.append(NOISE.sub("", str(o)))
            cache[sig] = texts
            run.defs = defs
        return cache[sig]

    base = run({})
    again = run({"(repeat)": 0})  # the same notebook once more: what differs is noise, not the effect of a control
    unstable = {i for i, (x, y) in enumerate(zip(base, again)) if x != y}
    controls = {}
    for name, v in run.defs.items():
        if isinstance(v, UIElement) and type(v).__name__ not in SKIP:
            controls[key(v)] = (name, v)

    def alternatives(v, limit: int = 3) -> list:
        kind = type(v).__name__
        cur = original(v)  # the value the control has by itself, not an override left over from an earlier run
        if kind in ("slider", "number"):
            lo, hi = v.start, v.stop
            vals = [lo, hi] + ([(lo + hi) / 2] if hi - lo > 2 * (v.step or 1) else [])
            return [x for x in vals if x != cur][:limit]
        if kind in ("dropdown", "radio"):
            vals = list(dict.fromkeys(v.options.values()))
            pick = [vals[0], vals[len(vals) // 2], vals[-1]]
            return [x for x in dict.fromkeys(pick) if x != cur][:limit]
        if kind in ("checkbox", "switch"):
            return [not cur]
        if kind in ("text", "text_area"):
            return ["audit"]
        if kind == "multiselect":
            return [[], list(dict.fromkeys(v.options.values()))]
        if kind == "dictionary":  # a set of radio questions: answer every one with its first, then with its last option
            opts = {n: list(dict.fromkeys(e.options.values())) for n, e in v.elements.items() if hasattr(e, "options")}
            return [{n: o[0] for n, o in opts.items()}, {n: o[-1] for n, o in opts.items()}]
        return []

    contexts = [{}]
    for k, (name, v) in controls.items():
        kind = type(v).__name__
        if kind in ("dropdown", "radio", "checkbox", "switch"):
            for alt in alternatives(v, 2):
                contexts.append({k: alt})
        elif kind in ("slider", "number"):  # a slider at its top end, for controls that only act once another one is raised
            contexts.append({k: v.stop})
    report = {}
    for k, (name, v) in controls.items():
        alts = alternatives(v)
        per_context = []
        for ctx in contexts:
            if k in ctx:
                continue
            ref = run(ctx)
            changed = 0
            for a in alts:
                out = run({**ctx, k: a})
                changed = max(changed, sum(1 for i, (x, y) in enumerate(zip(ref, out)) if x != y and i not in unstable))
            per_context.append((", ".join(f"{c.split('|', 1)[1]}={val}" for c, val in ctx.items()) or "(defaults)", changed))
        report[k] = {"variable": name, "kind": type(v).__name__, "alternatives": len(alts), "contexts": per_context}
    return {"notebook": path.name, "runs": len(cache), "cells": len(base), "unstable": sorted(unstable), "controls": report}


def main() -> None:
    paths = [Path(a) for a in sys.argv[1:]] or sorted((ROOT / "notebooks").glob("*.py"))
    with Pool(min(len(paths), 8)) as pool:
        results = pool.map(audit, [str(p) for p in paths])
    dead, conditional = 0, 0
    for r in results:
        print(f"\n{r['notebook']}: {len(r['controls'])} controls, {r['runs']} runs" + (f", cells {r['unstable']} change between identical runs and are ignored" if r["unstable"] else ""))
        for k, c in r["controls"].items():
            label = k.split("|", 1)[1] or c["variable"]
            effect = [n for _, n in c["contexts"]]
            if not c["alternatives"]:
                print(f"  ?  {label}  (no alternative value to try)")
            elif max(effect, default=0) == 0:
                dead += 1
                print(f"  DEAD  {label}  [{c['kind']} {c['variable']}]  changes no cell in any setting")
            elif min(effect) == 0:
                conditional += 1
                where = [ctx for ctx, n in c["contexts"] if n == 0]
                print(f"  cond  {label}  [{c['kind']} {c['variable']}]  no effect when: {'; '.join(where)}")
    print(f"\n{dead} dead and {conditional} conditional controls")


if __name__ == "__main__":
    main()
