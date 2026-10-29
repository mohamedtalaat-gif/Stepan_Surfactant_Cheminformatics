# Created by Muhammad Talaat, Faculty of Pharmacy, Ain Shams University
# SPDX-FileCopyrightText: 2026 Muhammad Talaat
# SPDX-License-Identifier: MIT

import marimo

__generated_with = "0.25.2"
app = marimo.App(width="medium", app_title="Lab: molecular dynamics of self-assembly")


@app.cell(hide_code=True)
def _():
    import altair as alt
    import marimo as mo
    import numpy as np
    import pandas as pd

    from stepan_lab import card, md, mdcharts, molecules, physchem, ui, viewer

    try:
        import openmm

        openmm_version = openmm.__version__
    except ImportError:  # no wheel for this computer: the stored simulations can still be shown
        openmm_version = None

    return alt, card, md, mdcharts, mo, molecules, np, openmm_version, pd, physchem, ui, viewer


@app.cell(hide_code=True)
def _(mo, ui):
    mo.vstack([
        ui.nav("lab_dynamics"),
        ui.header("Molecular dynamics of self-assembly", "Lab: random surfactant chains in water, and the micelles and bilayers that form"),
        ui.byline(),
        mo.md(
            """
            In the molecules lab the shape of a micelle follows from a packing parameter. Here nothing is chosen. Surfactant chains are placed at random in water, a classical molecular
            dynamics simulation (OpenMM) runs, and the aggregates that form are measured on the trajectory: how many molecules they hold, how large and how round they are, and where the
            heads, the chains and the water sit. The simulation is **coarse-grained**: about four heavy atoms become one bead and four water molecules become one bead, which is what
            makes a hundred surfactants in explicit water a matter of minutes. The force field is a simplified version of the MARTINI scheme with my own assignment of bead types to the
            head groups, so the output is a model of how these structures assemble and not a measurement. Everything on this page is marked *modelled*.
            """
        ),
        mo.accordion({"How the numbers are labelled": ui.legend()}),
    ])
    return


@app.cell(hide_code=True)
def _(md, mdcharts, mo, openmm_version, ui):
    _t = mdcharts.interaction_table()
    force_field = mo.vstack([
        mo.md("### The model  " + ui.badge("modelled")),
        mo.md(
            f"""
            Six bead types: water **W** (four molecules), apolar chain **T** (four carbons), semi-polar **N**, polar **P**, anionic **A** and cationic **C**. A head bead carries a charge of
            plus or minus one when its atoms do; sodium and chloride counter-ions are beads of type C and A. Every bead has the mass of 72 u and the size 0.47 nm, except that the pairs of a
            chain with a polar or charged bead use 0.62 nm (the hydrophobic mismatch of the MARTINI scheme). The table gives the Lennard-Jones well depth of each pair in kJ/mol. Bonded
            beads are held at 0.47 nm by a harmonic spring (1250 kJ/mol/nm2), chains are kept straight by a weak angle term (25 kJ/mol), charges interact through a reaction field with a
            relative permittivity of 15, and the cut-off is {md.CUTOFF} nm. Dynamics: Langevin thermostat at 310 K, a Monte Carlo barostat at 1 bar, time step 20 fs.
            The coarse-graining of every structure is done by `stepan_lab.md.coarse_grain` from its SMILES, so the assignment of bead types is mine and has not been fitted or validated
            for each surfactant. OpenMM {openmm_version or '(not available for this computer: the stored simulations below can be viewed but a new one cannot be run)'}.
            """
        ),
        ui.table(_t.reset_index().rename(columns={"index": "bead"}), 6),
        mo.md("The method follows Marrink et al., *J. Phys. Chem. B* 111, 7812 (2007) for the bead sizes, the interaction levels and the electrostatics, and Eastman et al., *PLoS Comput. Biol.* 13, e1005659 (2017) for OpenMM."),
    ], gap=0.8)
    return (force_field,)


@app.cell(hide_code=True)
def _(mo, molecules):
    cg_pick = mo.ui.dropdown({f"{s.name}  ({s.family})": k for k, s in molecules.REGISTRY.items()},
                             value=f"{molecules.REGISTRY['capb'].name}  ({molecules.REGISTRY['capb'].family})", label="Structure")
    return (cg_pick,)


@app.cell(hide_code=True)
def _(cg_pick, md, mdcharts, mo, ui):
    _cg = md.coarse_grain(cg_pick.value)
    mapping = mo.vstack([
        mo.md("### From a structure to beads  " + ui.badge("derived")),
        mo.md(
            """
            The alkyl chain is cut into beads of about four carbons from its free end. The head group is cut into pieces of up to four heavy atoms, keeping a sulfate, a carboxylate or an
            ammonium together; a piece is anionic or cationic if its atoms carry a net charge, polar or semi-polar by its share of oxygen and nitrogen. The drawing colours the atoms of
            each bead with the colour of its type.
            """
        ),
        cg_pick,
        mo.hstack([mo.Html(md.draw_mapping(cg_pick.value)),
                   mo.vstack([mo.md(f"**{len(_cg.beads)} beads** from {_cg.heavy_atoms} heavy atoms: `{_cg.sequence}`  \n" + (f"Counter-ions needed: {_cg.ions[1]} x {'Na+' if _cg.ions[0] == 'NA' else 'Cl-'}." if _cg.ions else "Neutral molecule: no counter-ion.")),
                              mo.Html("".join(f'<span style="display:inline-block;margin:2px 10px 2px 0"><span style="display:inline-block;width:11px;height:11px;border-radius:50%;background:{md.COLOUR[t]};margin-right:5px"></span>{t} {md.LONG[t]}</span>' for t in "TNPAC"))])],
                  justify="start", gap=2, align="start", wrap=True),
        ui.table(mdcharts.bead_table(cg_pick.value), 10),
    ], gap=0.8)
    return (mapping,)


@app.cell(hide_code=True)
def _(card, mo):
    _systems = {"sls": "Sodium lauryl sulfate", "aos_betaine": "AOS with coco-betaine", "ester_quat": "Ester quat with cetyl alcohol"}
    stored = {k: d for k in _systems if (d := card.load_md(k)) is not None}
    stored_pick = mo.ui.dropdown({v: k for k, v in _systems.items() if k in stored}, value=next((v for k, v in _systems.items() if k in stored), None), label="Simulation")
    return stored, stored_pick


@app.cell(hide_code=True)
def _(card, mdcharts, mo, np, physchem, stored, stored_pick, ui, viewer):
    if not stored:
        stored_view = mo.md("The stored simulations are not in this copy of the lab (`docs/card/md/`). Run `python scripts/run_md.py` to create them.")
    else:
        _d = stored[stored_pick.value]
        _s = _d["summary"]
        _names = {"sls": "SLS", "aos_betaine": "AOS and coco-betaine", "ester_quat": "ester quat and cetyl alcohol"}
        _page = viewer.page(card.load_data(), compact=True)
        _plan = ""
        if _d["system"] == "sls":
            _n, _p, _ = card.plan({"sls": 1.0}, "sphere")
            _plan = f" The packing model of the molecules lab gives a spherical micelle of {_n} monomers (P = {_p:.2f})."
        _prof = mdcharts.profile_chart(_d)
        _pr = _d.get("profile") or {}
        if _pr:
            _r = np.array(_pr["r"])
            _rt, _rh = float(_r[int(np.argmax(_pr["tail"]))]), float(_r[int(np.argmax(_pr["head"]))])
            _layers = (f"In the radial density the chain beads peak {_rt:.1f} nm from the centre of the largest aggregate and the head beads {_rh:.1f} nm from it"
                       + (", so the chains fill the core and the heads form a shell around it with the water outside, the layering that the packing model assumes." if _rt < _rh
                          else ": the chains are not concentrated at the centre, as expected for an aggregate that is not a compact micelle."))
        else:
            _layers = "No radial profile was recorded for this run."
        stored_view = mo.vstack([
            mo.md("### Simulations that were run for this lab  " + ui.badge("modelled")),
            mo.md(
                f"""
                Each simulation started from random chains on a lattice in a periodic box of water, so every aggregate in it formed during the run. They were run with `scripts/run_md.py`
                ({_d['meta']['platform']} platform, OpenMM {_d['meta']['openmm']}, seed {_d['meta']['seed']}, {_d['meta']['wall_minutes']} min). In the viewer press *Dynamics*, then *Play*, or move
                the time slider; *Cut away* shows the inside.
                """
            ),
            mo.iframe(_page, height="880px"),
            stored_pick,
            mo.md(
                f"""
                **{_d['molecules']} molecules, {_s['ns']:g} ns, {_d['box_nm']:.1f} nm box.** In the second half of the run the molecules were in {_s['aggregates']:.1f} aggregate(s) of {_s['aggregation_number']:.0f} molecules on average,
                the largest holding {_s['largest_aggregate']:.0f}; {100 * _s['free_fraction']:.0f}% of the molecules were free. The largest aggregate has a radius of gyration of {_s['rg_nm']:.2f} nm, an asphericity of
                {_s['asphericity']:.2f} (0 for a sphere, 1 for a rod) and a relative shape anisotropy of {_s['kappa2']:.2f}.{_plan}
                """
            ),
            mo.hstack([mdcharts.size_chart(_d), mdcharts.shape_chart(_d)], justify="start", gap=1, wrap=True),
            mo.hstack([c for c in (mdcharts.free_chart(_d), _prof) if c is not None], justify="start", gap=1, wrap=True),
            mo.md(_layers),
            ui.table(mdcharts.summary_table({_names[k]: v for k, v in stored.items()}), 6),
            mo.md("A single run in a box of a hundred molecules cannot give a distribution of aggregation numbers: when the box holds fewer molecules than one equilibrium aggregate, all of them join it. Read the sizes as what this model does in this box."),
        ], gap=0.8)
    return (stored_view,)


@app.cell(hide_code=True)
def _(md, mo, molecules):
    _names = {f"{s.name}  ({s.family})": k for k, s in molecules.REGISTRY.items()}
    _first = f"{molecules.REGISTRY['sls'].name}  ({molecules.REGISTRY['sls'].family})"
    run_a = mo.ui.dropdown(_names, value=_first, label="Surfactant")
    run_b = mo.ui.dropdown({"(none)": "", **_names}, value="(none)", label="Second structure")
    run_x = mo.ui.slider(0.0, 0.8, value=0.33, step=0.01, label="Mole fraction of the second", show_value=True)
    run_n = mo.ui.slider(12, 60, value=30, step=2, label="Molecules", show_value=True)
    run_ns = mo.ui.slider(0.5, 5.0, value=1.0, step=0.5, label="Nanoseconds", show_value=True)
    run_seed = mo.ui.number(1, 99, value=1, label="Random seed")
    run_go = mo.ui.run_button(label="Run the simulation")
    return run_a, run_b, run_go, run_n, run_ns, run_seed, run_x


@app.cell(hide_code=True)
def _(card, md, mdcharts, mo, molecules, openmm_version, run_a, run_b, run_go, run_n, run_ns, run_seed, run_x, ui, viewer):
    _controls = mo.vstack([mo.hstack([run_a, run_b], justify="start", gap=1.5, wrap=True),
                           mo.hstack([run_x, run_n, run_ns, run_seed], justify="start", gap=1.5, wrap=True), run_go], gap=0.6)
    _head = [mo.md("### Run a simulation of your own  " + ui.badge("modelled")),
             mo.md(
                 "Pick a surfactant, optionally a second structure and its share, the number of molecules and the length. The box is sized for about 0.25 mol/L of surfactant. On a computer without a graphics "
                 "card one nanosecond takes a minute or two; with a CUDA or OpenCL card it takes seconds. Micelles of a short-chain surfactant form within a nanosecond or two; bilayers and "
                 "long-chain systems need much longer runs than this page allows (see the stored simulations)."
             ),
             _controls]
    if openmm_version is None:
        _body = [mo.md("OpenMM is not installed for this computer, so a new simulation cannot be run here.")]
    elif not run_go.value:
        _body = [mo.md("Choose the system and press the button.")]
    else:
        _a, _b = run_a.value, run_b.value
        _n = int(run_n.value)
        _nb = 0 if (not _b or _b == _a) else int(round(_n * run_x.value))
        _comp = {_a: _n - _nb} if _nb == 0 else {_a: _n - _nb, _b: _nb}
        _side = md.box_size_for(_comp)
        with mo.status.spinner(title=f"Simulating {_n} molecules for {run_ns.value:g} ns on the {md.platform_name()} platform"):
            _res = md.run("run", _comp, ns=float(run_ns.value), n_side=_side, seed=int(run_seed.value), sample_ps=float(run_ns.value) * 1000 / 50, n_view_frames=30)
        _d = md.to_dict(_res)
        _s = _d["summary"]
        _system = {"id": "run", "name": " with ".join(molecules.REGISTRY[k].name for k in _comp), "caption": "", "svg": "", "shapes": {}, "species": [], "md": card.md_view(_d)}
        _page = viewer.page({"systems": [_system], "molecules": [], "stats": []}, compact=True)
        _body = [
            mo.iframe(_page, height="760px"),
            mo.md(
                f"{_d['molecules']} molecules in a {_d['box_nm']:.1f} nm box for {_s['ns']:g} ns: in the second half of the run, {_s['aggregates']:.1f} aggregate(s) of {_s['aggregation_number']:.0f} molecules on average, "
                f"the largest holding {_s['largest_aggregate']:.0f}, {100 * _s['free_fraction']:.0f}% of the molecules free; radius of gyration of the largest {_s['rg_nm']:.2f} nm, asphericity {_s['asphericity']:.2f}. "
                "A run this short shows the first stage of the assembly; the stored simulations ran for much longer."
            ),
            mo.hstack([mdcharts.size_chart(_d, 200), mdcharts.shape_chart(_d, 200)], justify="start", gap=1, wrap=True),
            mo.download(data=__import__("json").dumps(_d, separators=(",", ":")).encode(), filename="simulation.json", label="Download the result as JSON"),
        ]
    own_run = mo.vstack(_head + _body, gap=0.8)
    return (own_run,)


@app.cell(hide_code=True)
def _(mo):
    limits = mo.md(
        """
        ### What this is, and what it is not

        * A coarse-grained model with a simplified MARTINI-style force field. Water is one bead for four molecules and has no hydrogen bonds; the head-group beads are assigned by a rule and
          were not fitted to any surfactant.
        * Aggregation numbers, shapes and the order in which things form depend on the box size, the concentration, the run length and the random seed. A hundred molecules in a box of 8 nm
          is a small system: the sizes it gives are not equilibrium aggregation numbers.
        * Bilayers and vesicles of dialkyl surfactants form slowly. The ester quat box is dense (about two thirds of its beads are surfactant, far more than in a conditioner) so its chains start in contact
          and the simulation shows how they rearrange, not how they gather from a dilute solution; it is not a prediction of the lamellar phase of a conditioner.
        * The atoms of the molecules lab and the beads of this lab are two different pictures of the same structures: the first is geometric and detailed, the second is dynamic and coarse.
        """
    )
    return (limits,)


@app.cell(hide_code=True)
def _(force_field, limits, mapping, mo, own_run, stored_view):
    mo.vstack([force_field, mapping, stored_view, own_run, limits], gap=2)
    return


@app.cell(hide_code=True)
def _(ui):
    ui.footer()
    return


if __name__ == "__main__":
    app.run()
