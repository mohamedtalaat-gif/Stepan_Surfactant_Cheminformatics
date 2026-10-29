# Created by Muhammad Talaat, Faculty of Pharmacy, Ain Shams University
# SPDX-FileCopyrightText: 2026 Muhammad Talaat
# SPDX-License-Identifier: MIT

import marimo

__generated_with = "0.25.2"
app = marimo.App(width="medium", app_title="Lab: molecules and physical chemistry")


@app.cell(hide_code=True)
def _():
    import altair as alt
    import marimo as mo
    import numpy as np
    import pandas as pd

    from stepan_lab import card, data, molecules, physchem, rheology, ui, viewer

    return alt, card, data, mo, molecules, np, pd, physchem, rheology, ui, viewer


@app.cell(hide_code=True)
def _(mo, ui):
    mo.vstack([
        ui.nav("lab_molecules"),
        ui.header("Molecules and physical chemistry", "Lab: every surfactant of the seminar as a structure, and the physical chemistry that connects structure to performance"),
        ui.byline(),
        mo.md(
            """
            The seminar shows chemical structures on a handful of identity cards and spends most of its time on bars and curves. This lab goes the other way: it starts from the
            structure. Each surfactant is a SMILES string that I wrote from its INCI name; RDKit gives the descriptors and the drawing, and a few textbook models (chain packing, critical
            micelle concentration, electrolyte screening) connect the structure to the salt curves and foam charts of the sessions. Everything computed here is marked *derived* or
            *modelled*; the assumptions are sliders you can move.
            """
        ),
        mo.accordion({"How the numbers are labelled": ui.legend()}),
    ])
    return


@app.cell(hide_code=True)
def _(mo, molecules):
    pick = mo.ui.dropdown({f"{s.name}  ({s.family})": k for k, s in molecules.REGISTRY.items()}, value=f"{molecules.REGISTRY['capb'].name}  ({molecules.REGISTRY['capb'].family})", label="Structure")
    n_c = mo.ui.slider(6, 24, value=12, step=1, label="Chain carbons n", show_value=True)
    a0 = mo.ui.slider(20, 140, value=62, step=1, label="Head-group area a0 (square angstrom)", show_value=True)
    x2 = mo.ui.slider(0.0, 1.0, value=0.3, step=0.05, label="Mole fraction of the second surfactant", show_value=True)
    n2 = mo.ui.slider(6, 24, value=12, step=1, label="Second surfactant: chain carbons", show_value=True)
    a2 = mo.ui.slider(20, 140, value=48, step=1, label="Second surfactant: head-group area", show_value=True)
    beta = mo.ui.slider(0.0, 1.0, value=0.7, step=0.05, label="Counter-ion binding beta (0 for non-ionic)", show_value=True)
    n_cmc = mo.ui.slider(6, 18, value=12, step=1, label="Chain carbons for the CMC estimate", show_value=True)
    salt = mo.ui.slider(0.0, 10.0, value=1.5, step=0.1, label="Salt added (% NaCl)", show_value=True)
    n_eo = mo.ui.slider(1, 60, value=20, step=1, label="Ethylene oxide units", show_value=True)
    return a0, a2, beta, n2, n_c, n_cmc, n_eo, pick, salt, x2


@app.cell(hide_code=True)
def _(mo, molecules, pd, pick, ui):
    _k = pick.value
    _s = molecules.REGISTRY[_k]
    _d = molecules.descriptors(_k)
    _r, _t = molecules.carbon_counts(molecules.mol(_k))
    atlas = mo.vstack([
        mo.md("### Structure atlas  " + ui.badge("derived")),
        pick,
        mo.hstack([ui.structure_card(_k, size=(520, 290)),
                   mo.vstack([mo.md(f"**{_s.name}**  \n{_s.family}, {_s.charge_class}  \n\n{_s.note}"),
                              mo.md("SMILES (atom maps `:1` mark renewable carbon):  \n`" + _s.smiles + "`"),
                              ui.table(pd.DataFrame([_d]).T.reset_index().rename(columns={"index": "descriptor", 0: "value"}).astype(str), 12)])],
                  justify="start", gap=2, align="start"),
        mo.md("Crippen logP is an atom-contribution estimate for the species as drawn; for charged surfactants it is only a rough ranking and not a partition coefficient."),
        mo.accordion({"All structures in one table": mo.vstack([ui.table(molecules.table(), 10), ui.csv_button(molecules.table(), "structures.csv")])}),
    ], gap=0.8)
    return (atlas,)


@app.cell(hide_code=True)
def _(mo, molecules, pd, ui):
    _f = lambda k: molecules.renewable_fraction(k)  # noqa: E731
    # LSB/MB: carbon-weighted mix of sodium lauryl sulfoacetate (14 C, 12 renewable) and disodium laureth-3 sulfosuccinate (22 C, 12 renewable)
    _x = (22 - 12 / 0.64) / 8  # mole fraction of the sulfoacetate that reproduces 64
    _g = (0.88 - _f("soleil_eq")) / (1 - _f("soleil_eq"))
    _n_dm = 4 * 0.76 / (1 - 0.76)
    _n_cdb = 4 * 0.78 / (1 - 0.78)
    _x_mes = (12 / 0.94) - 12
    rows = [
        ("LATHANOL LAL COARSE/MB", "BCI 86 (S2 p16), 87 (S4 p6)", "sodium lauryl sulfoacetate", _f("slsa"), "matches within one point"),
        ("NINOL CAA", "ISO 16128 NOI 0.86 (S1 p19)", "dimethyl lauramide", _f("ninol"), "matches"),
        ("AMMONYX LO", "BCI 86 (S4 p15)", "lauramine oxide", _f("lauramineoxide"), "matches"),
        ("STEPAN-MILD GCC, L3", "BCI 100, NOI 1 (S1 p33, p34)", "glyceryl caprylate, lauryl lactyl lactate", min(_f("gcc_c8"), _f("l3")), "matches"),
        ("AMPHOSOL DM/MB", "BCI 76 (S4 p11), 78 (S1 p15)", "coco-betaine, C12 only", _f("cocobetaine"), f"a mean chain of C{_n_dm:.1f} gives 76 (R is C12/C14)"),
        ("AMPHOSOL CDB-HP-E", "BCI 78 (S1 p15)", "cetyl betaine, C16", _f("cetylbetaine"), f"78 would need a mean chain of C{_n_cdb:.1f}, not C16"),
        ("STEPAN-MILD LSB/MB", "BCI 64 (S4 p4)", "sulfoacetate + laureth-3 sulfosuccinate", _f("slsa"), f"64 needs {100 * _x:.0f} mol% sulfoacetate in the pair"),
        ("STEPANQUAT Soleil", "ISO 16128 score 0.88 (S7 p12)", "dioleoyl ester quat", _f("soleil_eq"), f"0.88 implies {100 * _g:.0f}% glyceride carbon in the blend"),
        ("ALPHA-STEP PC-48", "94% bio-based (S2 p9)", "methyl 2-sulfolaurate (92%) with the disodium salt (100%)", _f("mes"), f"94 implies {100 * _x_mes:.0f} mol% methyl ester"),
    ]
    _t = pd.DataFrame([{"product": a, "printed on the slide": b, "structure used": c, "share from the structure": round(d, 3), "reading": e} for a, b, c, d, e in rows])
    cross = mo.vstack([
        mo.md("### Does the printed bio-based index follow from the structure?  " + ui.badge("derived")),
        mo.md(
            "Several cards print a 'BCI' (not defined on the slides) next to the ISO 16128 index, and Stepan's footnote says the natural-origin index is calculated on a biorenewable-carbon basis. "
            "If that is right, the index of a single molecule is the share of its carbon that comes from renewable feedstock, and I can count it from the structure: "
            "fatty chains, glycerol, lactic acid and glucose are renewable; methyl groups on nitrogen, acetate, ethylene oxide and succinate are not. "
            "The count reproduces the printed values of LATHANOL LAL, NINOL CAA, AMMONYX LO, the GCC and L3 cards and (for a C12 chain) AMPHOSOL DM/MB to within about a point. Where it does not, the table says what composition would be needed instead; those are inferences, "
            "because the slides give no compositions."
        ),
        ui.table(_t, 9),
    ], gap=0.7)
    return (cross,)


@app.cell(hide_code=True)
def _(a0, a2, alt, mo, molecules, n2, n_c, np, pd, physchem, ui, x2):
    _p1 = physchem.packing_parameter(n_c.value, a0.value)
    _p = physchem.mixed_packing_parameter([(1 - x2.value, n_c.value, a0.value), (x2.value, n2.value, a2.value)])
    _grid = np.linspace(25, 140, 60)
    _df = pd.DataFrame({"a0": _grid, "P": [physchem.packing_parameter(n_c.value, a) for a in _grid]})
    _ln = alt.Chart(_df).mark_line(color="#1b7f8c", strokeWidth=2.4).encode(x=alt.X("a0:Q", title="Head-group area a0 (square angstrom)"), y=alt.Y("P:Q", scale=alt.Scale(domain=[0, 1.4])))
    _rules = alt.Chart(pd.DataFrame({"y": [1 / 3, 0.5, 1.0]})).mark_rule(strokeDash=[4, 4], color="#999").encode(y="y:Q")
    _pt = alt.Chart(pd.DataFrame({"a0": [a0.value], "P": [_p1]})).mark_point(filled=True, size=120, color="#d1495b").encode(x="a0:Q", y="P:Q")
    _reg = pd.DataFrame([{"structure": s.name, "chain n": s.chain_n, "assumed a0": s.head_a0, "P": round(physchem.packing_parameter(s.chain_n, s.head_a0), 2)}
                         for s in molecules.REGISTRY.values() if s.chain_n and s.head_a0 and s.family not in ("ester quat",)])
    packing = mo.vstack([
        mo.md("### Chain packing and the shape of the micelle  " + ui.badge("modelled")),
        mo.md(
            "A surfactant of chain volume v, chain length l and head-group area a0 has the critical packing parameter P = v / (a0 l) (Israelachvili, Mitchell and Ninham, 1976; chain geometry from Tanford, 1972). "
            "Spheres form below 1/3, rods between 1/3 and 1/2, bilayers above. Adding a co-surfactant with a smaller head group (the secondary surfactant of every thickening hack) "
            "raises P, which pushes a spherical micelle toward rods, and entangled rods are what make a surfactant solution viscous. Salt does the same by screening charge repulsion, "
            "which lowers the effective a0."
        ),
        mo.hstack([mo.vstack([n_c, a0]), mo.vstack([x2, n2, a2])], justify="start", gap=3),
        mo.md("The two sliders under the mole fraction describe the second surfactant; they change the result only while its share is above zero."),
        mo.md(f"Primary surfactant alone: **P = {_p1:.2f}**, {physchem.aggregate_shape(_p1)}.  \nWith {x2.value:.0%} of the second surfactant: **P = {_p:.2f}**, {physchem.aggregate_shape(_p)}.  \n"
              f"Chain volume {physchem.chain_volume_A3(n_c.value):.0f} cubic angstrom, extended length {physchem.chain_length_A(n_c.value):.1f} angstrom; "
              f"second surfactant {physchem.chain_volume_A3(n2.value):.0f} cubic angstrom and {physchem.chain_length_A(n2.value):.1f} angstrom. Chain length alone moves P very little, because the volume and the length of a chain grow together; "
              "the head-group area is what moves it."),
        mo.ui.altair_chart((_ln + _rules + _pt).properties(width=520, height=260)),
        mo.accordion({"P for every structure with my assumed head-group areas": ui.table(_reg, 12)}),
        mo.md("Sodium dodecyl sulfate with a0 of 62 square angstrom gives P of 0.34, the textbook value at the sphere-to-rod boundary. The head-group areas of the other surfactants are my assumptions, "
              "chosen from typical values, so the list is a starting point and not a measurement."),
    ], gap=0.7)
    return (packing,)


@app.cell(hide_code=True)
def _(alt, beta, mo, n_cmc, np, pd, physchem, ui):
    _a, _b = physchem.klevens_fit()
    _obs = pd.DataFrame([{"n": n, "CMC (mM)": v} for n, v in physchem.SODIUM_ALKYL_SULFATE_CMC_MM.items()])
    _ns = np.arange(6, 19)
    _fit = pd.DataFrame({"n": _ns, "CMC (mM)": [physchem.klevens_cmc_mM(n, _a, _b) for n in _ns]})
    _y = alt.Y("CMC (mM):Q", scale=alt.Scale(type="log"))
    _c = alt.Chart(_fit).mark_line(color="#1b7f8c", strokeWidth=2.2).encode(x=alt.X("n:Q", title="Chain carbons n"), y=_y) + \
        alt.Chart(_obs).mark_point(filled=True, size=90, color="#d1495b").encode(x="n:Q", y=_y) + \
        alt.Chart(pd.DataFrame({"n": [n_cmc.value], "CMC (mM)": [physchem.klevens_cmc_mM(n_cmc.value, _a, _b)]})).mark_point(shape="diamond", size=200, color="#e1a22c", filled=True).encode(x="n:Q", y=_y)
    _cm = physchem.klevens_cmc_mM(n_cmc.value, _a, _b)
    _dg = physchem.delta_g_micellisation_kJ(_cm / 1000.0, beta.value)
    cmc = mo.vstack([
        mo.md("### Critical micelle concentration against chain length  " + ui.badge("modelled")),
        mo.md(
            "The CMC falls by a constant factor for every carbon added to the chain (Klevens, 1953): log10 CMC = A - B n. I fitted the four textbook points for sodium alkyl sulfates in water at 25 C "
            f"(Mukerjee and Mysels, 1971), which give A = {_a:.2f} and B = {_b:.2f}: each extra carbon lowers the CMC by a factor of {10 ** _b:.1f}. "
            "The same chain-length rule explains why the longer-chain secondary surfactants of the sessions (cetyl betaine, C16) act at lower concentration than coco-betaine."
        ),
        mo.hstack([n_cmc, beta], justify="start", gap=2),
        mo.ui.altair_chart(_c.properties(width=520, height=260)),
        mo.md(f"For n = {n_cmc.value}: CMC about **{_cm:.3g} mM**, and the free energy of micellisation per monomer **{_dg:.1f} kJ/mol** "
              f"(dG = (1 + beta) R T ln X_cmc, with X_cmc = CMC / 55.5). Every red point is a literature value; the line is the fit."),
    ], gap=0.7)
    return (cmc,)


@app.cell(hide_code=True)
def _(alt, data, mo, np, pd, physchem, rheology, salt, ui):
    _s = np.linspace(0.0, 10.0, 101)
    _d = pd.DataFrame({"salt (% NaCl)": _s, "Debye length (nm)": [physchem.debye_length_nm(max(physchem.salt_wt_pct_to_molar(x), 1e-6)) for x in _s]})
    _ln = alt.Chart(_d).mark_line(color="#1b7f8c", strokeWidth=2.4).encode(x="salt (% NaCl):Q", y=alt.Y("Debye length (nm):Q", scale=alt.Scale(type="log")))
    _pt = alt.Chart(pd.DataFrame({"salt (% NaCl)": [salt.value], "Debye length (nm)": [physchem.debye_length_nm(max(physchem.salt_wt_pct_to_molar(salt.value), 1e-6))]})).mark_point(filled=True, size=140, color="#d1495b").encode(x="salt (% NaCl):Q", y="Debye length (nm):Q")
    _df = data.chart("s3_p10_salt_curves")
    _df = _df[_df["x"].astype(str).str.match(r"^[0-9.]+$")]
    _m = rheology.metrics_table(_df)
    _m["molar NaCl at the peak"] = _m["salt_at_peak_pct"].map(physchem.salt_wt_pct_to_molar).round(3)
    _m["Debye length at the peak (nm)"] = _m["molar NaCl at the peak"].map(lambda c: round(physchem.debye_length_nm(max(c, 1e-6)), 2))
    _t = _m[["series", "salt_at_peak_pct", "molar NaCl at the peak", "Debye length at the peak (nm)", "peak_cP"]].round(2)
    screening = mo.vstack([
        mo.md("### How salt screens the head groups  " + ui.badge("modelled") + " " + ui.badge("derived")),
        mo.md(
            "Every salt curve of the seminar has the x axis in percent NaCl. One percent is 0.17 mol/L, and the Debye length of a 1:1 electrolyte is 0.304 nm divided by the square root of "
            "the ionic strength in mol/L, so the electrostatic repulsion between head groups is screened over about 0.7 nm at 1% salt and 0.3 nm at 6%. The head-group repulsion is "
            "what keeps micelles small; once it is screened, the head groups pack closer, P rises and the micelles grow into rods until the network collapses at higher salt."
        ),
        salt,
        mo.ui.altair_chart((_ln + _pt).properties(width=520, height=240)),
        mo.md(f"At {salt.value:.1f}% NaCl the ionic strength is {physchem.salt_wt_pct_to_molar(salt.value):.2f} mol/L and the screening length **{physchem.debye_length_nm(max(physchem.salt_wt_pct_to_molar(salt.value), 1e-6)):.2f} nm**."),
        mo.md("Applied to the S3 p10 curves (salt at the viscosity peak of each):"),
        ui.table(_t, 5),
    ], gap=0.7)
    return (screening,)


@app.cell(hide_code=True)
def _(mo, molecules, n_eo, physchem, ui):
    _mw = molecules.descriptors("steareth20")["mw_formula_unit"] + (n_eo.value - 20) * 44.053
    hlb = mo.vstack([
        mo.md("### HLB of an ethoxylated emulsifier  " + ui.badge("modelled")),
        mo.md("The conditioner of S6 p10 uses Steareth-20 next to the fatty alcohols. Griffin's rule for ethoxylates, HLB = 20 x (mass of oxyethylene) / M, gives the balance directly from the structure."),
        n_eo,
        mo.md(f"Steareth-{n_eo.value}: M = {_mw:.0f} g/mol, **HLB = {physchem.hlb_griffin_ethoxylate(n_eo.value, _mw):.1f}** (Steareth-20 gives 15.3, a value in the oil-in-water emulsifier range)."),
    ], gap=0.6)
    return (hlb,)


@app.cell(hide_code=True)
def _(card, mo, molecules):
    _names = {f"{s.name}  ({s.family})": k for k, s in molecules.REGISTRY.items()}
    _first = f"{molecules.REGISTRY['sls'].name}  ({molecules.REGISTRY['sls'].family})"
    _second = f"{molecules.REGISTRY['cocobetaine'].name}  ({molecules.REGISTRY['cocobetaine'].family})"
    pick3d = mo.ui.dropdown(_names, value=_first, label="Structure")
    _build = {n: k for n, k in _names.items() if k in card.BUILDABLE}
    b1 = mo.ui.dropdown(_build, value=_first, label="Primary surfactant")
    b2 = mo.ui.dropdown(_build, value=_second, label="Second structure")
    bx = mo.ui.slider(0.0, 0.9, value=0.33, step=0.01, label="Mole fraction of the second", show_value=True)
    bshape = mo.ui.dropdown({"Spherical micelle": "sphere", "Rod-like micelle (salt added)": "rod", "Bilayer patch": "bilayer"}, value="Spherical micelle", label="Shape")
    go = mo.ui.run_button(label="Build the aggregate")
    return b1, b2, bshape, bx, go, pick3d


@app.cell(hide_code=True)
def _(card, mo, pd, pick3d, ui, viewer):
    _rec = card.molecule_record(pick3d.value)
    _page = viewer.page({"systems": [], "molecules": [_rec], "stats": []}, compact=True)
    _d3 = pd.DataFrame([_rec["descriptors3d"]]).T.reset_index().rename(columns={"index": "descriptor", 0: "value"}).astype(str)
    threed = mo.vstack([
        mo.md("### The structure in three dimensions  " + ui.badge("derived")),
        mo.md(
            """
            RDKit embeds the molecule with ETKDG (30 starting conformers) and relaxes each one with the MMFF94 force field. In vacuum the lowest conformer of a surfactant folds its chain over on itself, which an interface does not allow, so the view shows the most extended conformer within 12 kcal/mol of the lowest. Drag to turn it, scroll to zoom,
            and switch the colours to *Renewable carbon* to see which carbons come from the renewable feedstock (the atom maps of the SMILES). The shape descriptors come from the same
            coordinates: the radius of gyration, and the two normalised principal moments NPR1 and NPR2 that place the molecule between a rod, a disc and a sphere.
            """
        ),
        pick3d,
        mo.iframe(_page, height="540px"),
        mo.hstack([ui.table(_d3, 10), mo.download(data=_rec["sdf"].encode(), filename=f"{pick3d.value}.sdf", label="Download the SDF file (opens in PyMOL)")], justify="start", gap=2, align="start"),
    ], gap=0.8)
    return (threed,)


@app.cell(hide_code=True)
def _(card, mo, ui, viewer):
    _page = viewer.page(card.load_data(), compact=True)
    _files = {f.name: f for f in sorted(card.MODELS.glob("*.pdb"))}
    aggregates = mo.vstack([
        mo.md("### Micelles and bilayers as three-dimensional models  " + ui.badge("modelled")),
        mo.md(
            """
            The packing parameter above says which shape a mixture prefers; here the shape is built. Each model places relaxed monomers tail-in on a sphere, a capsule or two sheets,
            with the number of monomers taken from the packing model (a rod is three times the aggregation number of a sphere with a head-group area 20% smaller, my way of representing
            salt). Atoms of different monomers that overlap are pushed apart, and none of the models has two heavy atoms closer than 2 angstrom. This is a **geometric model**: it shows how a mixture of structures fills space, with the sulfate and ammonium heads outside and the chains forming the core; it predicts no aggregation number. In the [molecular dynamics lab](/lab_dynamics) random chains assemble on their own in explicit water.
            *Cut away* hides the front half to show the chains inside.
            """
        ),
        mo.iframe(_page, height="780px"),
        mo.accordion({"Open the same models in PyMOL": mo.vstack([
            mo.md("The PDB files carry the renewable-carbon flag in the B-factor column. Download one, or open `docs/card/models/stepan_lab.pml` in PyMOL to load all five coloured as above."),
            mo.hstack([mo.download(data=f.read_bytes(), filename=f.name, label=f.name) for f in _files.values()], wrap=True, justify="start"),
        ])}),
    ], gap=0.8)
    return (aggregates,)


@app.cell(hide_code=True)
def _(b1, b2, bshape, bx, card, go, mo, molecules, ui, viewer):
    _controls = mo.vstack([mo.hstack([b1, b2], justify="start", gap=1.5, wrap=True), mo.hstack([bx, bshape, go], justify="start", gap=1.5, wrap=True, align="end")], gap=0.6)
    _head = [mo.md("### Build an aggregate of your own  " + ui.badge("modelled")),
             mo.md("Pick any two structures of the registry, the share of the second, and a shape; the monomers are embedded and relaxed here, then placed as above. The first build of a structure takes a few seconds."),
             _controls]
    if go.value:
        _system, _info = card.build_custom(b1.value, b2.value, bx.value, bshape.value)
        _page = viewer.page({"systems": [_system], "molecules": [], "stats": []}, compact=True)
        _comp = " and ".join(f"{molecules.REGISTRY[k].name} {x:.0%}" for k, x in _info["composition"].items())
        _note = ""
        if _info["monomers"] < _info["model_monomers"]:
            _note = f" The packing model asks for {_info['model_monomers']} monomers; the build stops at {_info['monomers']} to keep the page responsive."
        _body = [
            mo.iframe(_page, height="620px"),
            mo.md(f"{_comp}: **{_info['monomers']} monomers**, packing parameter **{_info['packing_parameter']:.2f}**, radius about **{_info['radius_A']:.0f} angstrom**, "
                  f"{_info['close_contacts']} atom pairs closer than 2 angstrom.{_note}"),
            mo.download(data=_info["pdb"].encode(), filename="aggregate.pdb", label="Download the PDB file"),
        ]
    else:
        _body = [mo.md("Choose the structures and press the button.")]
    builder = mo.vstack(_head + _body, gap=0.8)
    return (builder,)


@app.cell(hide_code=True)
def _(aggregates, atlas, builder, cmc, cross, hlb, mo, packing, screening, threed):
    mo.vstack([atlas, threed, cross, packing, aggregates, builder, cmc, screening, hlb], gap=2)
    return


@app.cell(hide_code=True)
def _(ui):
    ui.footer()
    return


if __name__ == "__main__":
    app.run()
