# Created by Muhammad Talaat, Faculty of Pharmacy, Ain Shams University
# SPDX-FileCopyrightText: 2026 Muhammad Talaat
# SPDX-License-Identifier: MIT

"""Representative molecular structures for the surfactants of the seminar, built with RDKit.

Every commercial surfactant is a distribution of chain lengths, so each entry here is one
*representative* molecule (the modal chain length) written as a SMILES string.  Carbons that come from
a renewable feedstock in the usual route (fatty chains, glycerol, lactic acid, glucose) carry the atom
map number 1, which lets the renewable-carbon share be counted straight from the structure.  The
structures were drawn from the INCI names on the slides; the slides themselves show drawings only for
a few of them (S4 p04, p07, p11, p15, p16, S6 p03, p07).
"""

from __future__ import annotations

from dataclasses import dataclass

from rdkit import Chem
from rdkit.Chem import Descriptors, rdMolDescriptors
from rdkit.Chem.Draw import rdMolDraw2D
from rdkit.Chem.MolStandardize import rdMolStandardize

RENEWABLE = 1  # atom-map number that marks a renewable carbon


def alkyl(n: int) -> str:
    """Saturated n-carbon chain written from the methyl end; the last atom bonds to whatever follows."""
    return "[CH3:1]" if n == 1 else "[CH3:1]" + "[CH2:1]" * (n - 1)


def alkyl_back(n: int) -> str:
    """The same chain written from the head-group end (for a second chain in one molecule)."""
    return "[CH3:1]" if n == 1 else "[CH2:1]" * (n - 1) + "[CH3:1]"


OLEYL_FROM_METHYL = "[CH3:1]" + "[CH2:1]" * 7 + "[CH:1]=[CH:1]" + "[CH2:1]" * 7  # 17 carbons, then the carbonyl carbon
OLEYL_FROM_CARBONYL = "[CH2:1]" * 7 + "[CH:1]=[CH:1]" + "[CH2:1]" * 7 + "[CH3:1]"


@dataclass(frozen=True)
class Structure:
    key: str
    name: str
    smiles: str
    family: str
    charge_class: str
    chain_n: int | None  # carbons in the hydrophobic chain, for the packing and CMC models
    head_a0: float | None  # assumed head-group area in square angstrom (modelling assumption)
    products: tuple[str, ...] = ()
    note: str = ""
    renewable_known: bool = True


def _s(key, name, smiles, family, cc, n, a0, products=(), note="", renewable=True):
    return Structure(key, name, smiles, family, cc, n, a0, tuple(products), note, renewable)


REGISTRY: dict[str, Structure] = {s.key: s for s in [
    _s("sls", "Sodium lauryl sulfate", alkyl(12) + "OS(=O)(=O)[O-].[Na+]", "alkyl sulfate", "anionic", 12, 62, ("sls",),
       "Reference surfactant: the Zein scale is normalised to it."),
    _s("sles2", "Sodium laureth sulfate, 2 EO", alkyl(12) + "OCCOCCOS(=O)(=O)[O-].[Na+]", "alkyl ether sulfate", "anionic", 12, 68, ("sles2",),
       "The benchmark primary surfactant of the seminar. The two ethylene-oxide units are not counted as renewable carbon."),
    _s("aos_ene", "Sodium C14 alkene sulfonate (AOS component)", "CCCCCCCCCCCC=CCS(=O)(=O)[O-].[Na+]", "alpha olefin sulfonate", "anionic", 14, 56, ("as40hasb", "as40hp"),
       "About two thirds of an AOS is alkene sulfonate; this is the 2-ene isomer of the C14 cut.", renewable=False),
    _s("aos_hydroxy", "Sodium 3-hydroxytetradecane sulfonate (AOS component)", "CCCCCCCCCCCC(O)CCS(=O)(=O)[O-].[Na+]", "alpha olefin sulfonate", "anionic", 14, 58, ("as40hasb", "as40hp"),
       "The hydroxyalkane sulfonate fraction of an AOS.", renewable=False),
    _s("mes", "Sodium methyl 2-sulfolaurate", alkyl(10) + "[CH:1](S(=O)(=O)[O-])[C:1](=O)OC.[Na+]", "methyl ester sulfonate", "anionic", 12, 60, ("pc48",),
       "Ester group next to the sulfonate; the slide credits steric hindrance for the hard-water tolerance."),
    _s("mes_di", "Disodium 2-sulfolaurate", alkyl(10) + "[CH:1](S(=O)(=O)[O-])[C:1](=O)[O-].[Na+].[Na+]", "methyl ester sulfonate", "anionic", 12, 75, ("pc48",),
       "Hydrolysis product that accompanies the methyl ester in ALPHA-STEP PC-48."),
    _s("slsa", "Sodium lauryl sulfoacetate", alkyl(12) + "OC(=O)CS(=O)(=O)[O-].[Na+]", "sulfoacetate", "anionic", 12, 62, ("lal", "lalpowder", "lsb", "pclba"),
       "LATHANOL LAL; also one component of STEPAN-MILD LSB/MB and PCL-BA."),
    _s("dsls", "Disodium laureth-3 sulfosuccinate", alkyl(12) + "OCCOCCOCCOC(=O)C(S(=O)(=O)[O-])CC(=O)[O-].[Na+].[Na+]", "sulfosuccinate", "anionic", 12, 85, ("lsb",),
       "Second component of STEPAN-MILD LSB/MB; three ethylene-oxide units as drawn on S4 p04."),
    _s("sci", "Sodium cocoyl isethionate", alkyl(11) + "[C:1](=O)OCCS(=O)(=O)[O-].[Na+]", "isethionate", "anionic", 12, 55, (),
       "Used at 3.82% in the prestige body wash (S1 p28)."),
    _s("cocobetaine", "Coco-betaine", alkyl(12) + "[N+](C)(C)CC(=O)[O-]", "alkyl betaine", "amphoteric", 12, 48, ("dm",),
       "AMPHOSOL DM/MB; R is mostly C12 and C14 (S4 p11)."),
    _s("cetylbetaine", "Cetyl betaine", alkyl(16) + "[N+](C)(C)CC(=O)[O-]", "alkyl betaine", "amphoteric", 16, 48, ("cdbhpe",),
       "AMPHOSOL CDB-HP-E; drawn here with a straight C16 chain."),
    _s("capb", "Cocamidopropyl betaine", alkyl(11) + "[C:1](=O)NCCC[N+](C)(C)CC(=O)[O-]", "amidopropyl betaine", "amphoteric", 12, 52, ("capb", "cgun", "hcghp"),
       "The standard secondary surfactant against which the slides compare."),
    _s("lauramineoxide", "Lauramine oxide", alkyl(12) + "[N+](C)(C)[O-]", "amine oxide", "nonionic / cationic below pH 6.5", 12, 45, ("ammlo", "ammcso"),
       "AMMONYX LO. The N-O bond is strongly polar; below about pH 6.5 the oxygen is protonated and the head group is cationic (S4 p16)."),
    _s("ninol", "Dimethyl lauramide", alkyl(11) + "[C:1](=O)N(C)C", "fatty acid amide", "nonionic", 12, 38, ("ninol",),
       "NINOL CAA, with the myristamide homologue."),
    _s("cocamidemea", "Cocamide MEA", alkyl(11) + "[C:1](=O)NCCO", "fatty acid amide", "nonionic", 12, 38, (),
       "The thickener that NINOL CAA replaces on S1 p20."),
    _s("cocamidemipa", "Cocamide MIPA", alkyl(11) + "[C:1](=O)NC(C)CO", "fatty acid amide", "nonionic", 12, 38, (),
       "Used at 0.8% in the cleansing conditioner (S4 p24)."),
    _s("decylglucoside", "Decyl glucoside", alkyl(10) + "O[CH:1]1O[CH:1]([CH2:1]O)[CH:1](O)[CH:1](O)[CH:1]1O", "alkyl polyglucoside", "nonionic", 10, 55, ("decylglc",),
       "Drawn as the monoglucoside; commercial grades are a distribution of glucose units."),
    _s("gcc_c8", "Glyceryl caprylate", alkyl(7) + "[C:1](=O)O[CH2:1][CH:1](O)[CH2:1]O", "monoglyceride", "nonionic", 8, 25, ("gcc", "gccfl"),
       "STEPAN-MILD GCC is a caprylate/caprate mixture; the caprylate is shown."),
    _s("gcc_c10", "Glyceryl caprate", alkyl(9) + "[C:1](=O)O[CH2:1][CH:1](O)[CH2:1]O", "monoglyceride", "nonionic", 10, 25, ("gcc", "gccfl"), ""),
    _s("l3", "Lauryl lactyl lactate", alkyl(12) + "O[C:1](=O)[CH:1]([CH3:1])O[C:1](=O)[CH:1]([CH3:1])O", "lactylate ester", "nonionic", 12, 30, ("l3",),
       "STEPAN-MILD L3-G/MB."),
    _s("btac", "Behentrimonium chloride", alkyl(22) + "[N+](C)(C)C.[Cl-]", "quaternary ammonium", "cationic", 22, 60, ("btac",), "Conventional conditioning active."),
    _s("ctac", "Cetrimonium chloride", alkyl(16) + "[N+](C)(C)C.[Cl-]", "quaternary ammonium", "cationic", 16, 60, ("ctac",), "Conventional conditioning active (CETAC)."),
    _s("eq_b", "Dipalmitoylethyl hydroxyethylammonium methosulfate",
       alkyl(15) + "[C:1](=O)OCC[N+](C)(CCO)CCO[C:1](=O)" + alkyl_back(15) + ".COS(=O)(=O)[O-]", "ester quat", "cationic", 16, 65, ("gamma90", "pa85g"),
       "The ester quat of STEPANQUAT GA 90 and STEPANTEX PA 85-G (S6 p03). Two C16 acyl chains give a head group that packs into bilayers."),
    _s("soleil_eq", "Dioleoylethyl hydroxyethylmonium methosulfate",
       OLEYL_FROM_METHYL + "[C:1](=O)OCC[N+](C)(CCO)CCO[C:1](=O)" + OLEYL_FROM_CARBONYL + ".COS(=O)(=O)[O-]",
       "ester quat", "cationic", 18, 65, ("soleil",),
       "The quat part of STEPANQUAT Soleil, which is sold blended with sunflower seed oil glycerides (S7 p12)."),
    _s("cetylalcohol", "Cetyl alcohol", alkyl(16) + "O", "fatty alcohol", "nonionic", 16, 20, (), "Structuring co-emulsifier in conditioners."),
    _s("stearylalcohol", "Stearyl alcohol", alkyl(18) + "O", "fatty alcohol", "nonionic", 18, 20, (), "Structuring co-emulsifier in conditioners."),
    _s("steareth20", "Steareth-20", alkyl(18) + "O" + "CCO" * 20, "ethoxylated alcohol", "nonionic", 18, 190, (), "Emulsifier of the S6 conditioner."),
]}


def mol(key_or_smiles: str) -> Chem.Mol:
    smi = REGISTRY[key_or_smiles].smiles if key_or_smiles in REGISTRY else key_or_smiles
    m = Chem.MolFromSmiles(smi)
    if m is None:
        raise ValueError(f"cannot parse {smi!r}")
    return m


def _largest_fragment(m: Chem.Mol) -> Chem.Mol:
    return rdMolStandardize.LargestFragmentChooser().choose(m)


def carbon_counts(m: Chem.Mol) -> tuple[int, int]:
    """(renewable carbons, all carbons) over the whole formula unit, counter-ions included."""
    total = renewable = 0
    for a in m.GetAtoms():
        if a.GetSymbol() == "C":
            total += 1
            if a.GetAtomMapNum() == RENEWABLE:
                renewable += 1
    return renewable, total


def renewable_fraction(key_or_smiles: str) -> float:
    r, t = carbon_counts(mol(key_or_smiles))
    return r / t


def clean(m: Chem.Mol) -> Chem.Mol:
    m = Chem.Mol(m)
    for a in m.GetAtoms():
        a.SetAtomMapNum(0)
    return m


def descriptors(key_or_smiles: str) -> dict:
    """RDKit descriptors of the formula unit and of its largest (amphiphilic) fragment."""
    m = clean(mol(key_or_smiles))
    big = _largest_fragment(m)
    return {
        "formula": rdMolDescriptors.CalcMolFormula(m),
        "mw_formula_unit": round(Descriptors.MolWt(m), 2),
        "mw_amphiphile": round(Descriptors.MolWt(big), 2),
        "heavy_atoms": big.GetNumHeavyAtoms(),
        "rotatable_bonds": rdMolDescriptors.CalcNumRotatableBonds(big),
        "tpsa": round(rdMolDescriptors.CalcTPSA(big), 1),
        "crippen_logp": round(Descriptors.MolLogP(big), 2),
        "hbd": rdMolDescriptors.CalcNumHBD(big),
        "hba": rdMolDescriptors.CalcNumHBA(big),
        "net_charge": Chem.GetFormalCharge(big),
    }


def draw_svg(key_or_smiles: str, size=(460, 250), highlight_renewable=True, legend: str = "") -> str:
    """Structure as an SVG string; renewable carbons are shaded green when requested."""
    m = mol(key_or_smiles)
    hl = [a.GetIdx() for a in m.GetAtoms() if a.GetAtomMapNum() == RENEWABLE] if highlight_renewable else []
    m = clean(m)
    d = rdMolDraw2D.MolDraw2DSVG(size[0], size[1])
    opts = d.drawOptions()
    opts.clearBackground = False
    opts.legendFontSize = 15
    opts.bondLineWidth = 1.6
    colours = {i: (0.55, 0.80, 0.45, 0.55) for i in hl}
    d.DrawMolecule(m, legend=legend, highlightAtoms=hl, highlightAtomColors=colours,
                   highlightBonds=[b.GetIdx() for b in m.GetBonds() if b.GetBeginAtomIdx() in hl and b.GetEndAtomIdx() in hl],
                   highlightBondColors={b.GetIdx(): (0.55, 0.80, 0.45, 0.55) for b in m.GetBonds()
                                        if b.GetBeginAtomIdx() in hl and b.GetEndAtomIdx() in hl},
                   highlightAtomRadii={i: 0.28 for i in hl})
    d.FinishDrawing()
    return d.GetDrawingText()


def table():
    """One row per structure with descriptors and the renewable-carbon share."""
    import pandas as pd

    rows = []
    for k, s in REGISTRY.items():
        d = descriptors(k)
        r, t = carbon_counts(mol(k))
        rows.append({"key": k, "name": s.name, "family": s.family, "charge_class": s.charge_class, "chain_carbons": s.chain_n,
                     **d, "carbons": t, "renewable_carbons": r if s.renewable_known else None,
                     "renewable_share": round(r / t, 3) if s.renewable_known else None})
    return pd.DataFrame(rows)
