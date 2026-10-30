# Created by Muhammad Talaat, Faculty of Pharmacy, Ain Shams University
# SPDX-FileCopyrightText: 2026 Muhammad Talaat
# SPDX-License-Identifier: MIT
"""Ray-traced pictures of the aggregate models and of the simulations for the README, drawn with PyMOL.

    python scripts/build_card.py      # writes docs/card/models/*.pdb and manifest.json
    python scripts/run_md.py          # writes docs/card/md/*.json
    python scripts/render_card.py     # needs PyMOL on the PATH; writes the PNG files and the animated GIFs in docs/card/
    python scripts/render_card.py dark    # only one part: static, dark or light

Only needed to regenerate the pictures; the notebooks and the interactive page do not use PyMOL.
"""

from __future__ import annotations

import json
import math
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
CARD = ROOT / "docs" / "card"
MODELS = CARD / "models"
MDDIR = CARD / "md"
sys.path.insert(0, str(ROOT / "src"))
from stepan_lab.provenance import CREDIT_LINE

THEMES = {
    "dark": dict(page=(11, 16, 32), panel=(17, 26, 48), line=(39, 53, 90), ink=(238, 242, 255), muted=(165, 177, 207), accent=(255, 122, 144), accent2=(53, 208, 186)),
    "light": dict(page=(245, 247, 252), panel=(255, 255, 255), line=(214, 222, 239), ink=(20, 33, 61), muted=(86, 100, 138), accent=(214, 56, 90), accent2=(15, 157, 138)),
}
HEAD = (255, 200, 61)
BEAD = {"T": "#35d0ba", "N": "#b48cff", "P": "#ff9f43", "A": "#ff7a90", "C": "#5b9dff"}
# (system id, shape of the atomistic model, caption)
COLUMNS = [
    ("sls", "sphere", "Sodium lauryl sulfate"),
    ("aos_betaine", "rod", "AOS with coco-betaine"),
    ("ester_quat", "bilayer", "Ester quat with cetyl alcohol"),
]
ZOOM = {"sphere": 3.0, "rod": -14.0, "bilayer": 2.0}  # PyMOL zoom buffer (angstrom) per shape
ZOOM_MD = {"sls": 6.0, "aos_betaine": 3.0, "ester_quat": -6.0}  # PyMOL zoom buffer (angstrom) of the simulation pictures
PW, PH = 517, 300  # panel picture size in pixels


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    for path, idx in (("/System/Library/Fonts/Avenir Next.ttc", 0 if bold else 7), ("/System/Library/Fonts/HelveticaNeue.ttc", 1 if bold else 0),
                      ("C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf", 0),
                      ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 0)):
        if Path(path).exists():
            return ImageFont.truetype(path, size, index=idx)
    return ImageFont.load_default()


def read_pdb(path: Path):
    lines = [ln for ln in path.read_text(encoding="utf-8").splitlines() if ln.startswith("HETATM")]
    return lines_to_arrays(lines)


def lines_to_arrays(lines):
    xyz = np.array([[float(ln[30:38]), float(ln[38:46]), float(ln[46:54])] for ln in lines])
    resid = np.array([int(ln[22:26]) for ln in lines])
    return lines, xyz, resid


def md_frame_lines(d: dict, k: int) -> list[str]:
    """One frame of a simulation as PDB lines: a bead per atom, named by its type, one residue per molecule."""
    f = d["frames"][k]
    out = []
    for i, b in enumerate(d["beads"]):
        out.append("HETATM%5d %-4s BEA A%4d    %8.3f%8.3f%8.3f  1.00  0.00          %2s" % ((i + 1) % 100000, b["type"], (b["mol"] % 9999) + 1, f[3 * i], f[3 * i + 1], f[3 * i + 2], "C" if b["type"] == "T" else "O"))
    return out


def write_cut(lines, xyz, resid, angle: float, cut: bool, out: Path) -> None:
    """Rotate about the vertical axis and drop the monomers whose centre is in front of the middle plane."""
    c, s = math.cos(angle), math.sin(angle)
    rot = np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])
    p = xyz @ rot.T
    keep = np.ones(len(p), bool)
    if cut:
        centre_z = {r: p[resid == r, 2].mean() for r in np.unique(resid)}
        keep = np.array([centre_z[r] <= 0.0 for r in resid])
    rows = [ln[:30] + "%8.2f%8.2f%8.2f" % tuple(q) + ln[54:] for ln, q, k in zip(lines, p, keep) if k]
    out.write_text("\n".join(rows) + "\nEND\n", encoding="utf-8")


def pml_for(jobs: list[dict], ray_size: tuple[int, int]) -> str:
    """Commands for PyMOL: every job is one picture; ``kind`` is 'atoms' (coloured by species) or 'beads' (coloured by bead type)."""
    out = ["set ray_opaque_background, on", "set antialias, 2", "set ray_shadows, 1", "set ray_shadow_decay_factor, 0.25", "set specular, 0.35", "set spec_power, 120",
           "set ambient, 0.38", "set light_count, 2", "set depth_cue, 1", "set ray_trace_fog, 1", "set ray_trace_mode, 0",
           f"set_color c_head, [{HEAD[0] / 255:.3f}, {HEAD[1] / 255:.3f}, {HEAD[2] / 255:.3f}]"]
    for name, hexcol in BEAD.items():
        r, g, b = (int(hexcol[i:i + 2], 16) / 255 for i in (1, 3, 5))
        out.append(f"set_color cb_{name}, [{r:.3f}, {g:.3f}, {b:.3f}]")
    for j in jobs:
        bg = j["bg"]
        out += ["delete all", f"load {j['pdb']}, m", f"load {j['ref']}, ref", f"bg_color [{bg[0] / 255:.3f}, {bg[1] / 255:.3f}, {bg[2] / 255:.3f}]", "hide everything", "show spheres, m"]
        if j["kind"] == "beads":
            out += ["alter all, vdw=2.3", "rebuild", "set sphere_scale, 1.0"] + [f"color cb_{n}, m and name {n}" for n in BEAD]
        else:
            out.append("set sphere_scale, 0.62")
            for resn, hexcol in j["species"].items():
                r, g, b = (int(hexcol[i:i + 2], 16) / 255 for i in (1, 3, 5))
                out += [f"set_color c_{resn}, [{r:.3f}, {g:.3f}, {b:.3f}]", f"color c_{resn}, m and resn {resn} and elem C"]
            out.append("color c_head, m and not elem C")
        out += [f"zoom ref, {j['buf']}", "delete ref", f"png {j['png']}, {ray_size[0]}, {ray_size[1]}, dpi=150, ray=1"]
    return "\n".join(out) + "\nquit\n"


def run_pymol(pml: str, work: Path) -> None:
    exe = shutil.which("pymol")
    if exe is None:
        sys.exit("PyMOL is not on the PATH; it is only needed to regenerate the pictures")
    f = work / "render.pml"
    f.write_text(pml, encoding="utf-8")
    subprocess.run([exe, "-cq", str(f)], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def pill(d: ImageDraw.ImageDraw, xy, text: str, sub: str, t: dict, f1, f2) -> int:
    x, y = xy
    w1 = d.textlength(text, font=f1)
    w2 = d.textlength(sub, font=f2)
    w = int(w1 + w2 + 46)
    d.rounded_rectangle([x, y, x + w, y + 46], 23, fill=t["panel"], outline=t["accent"], width=2)
    d.text((x + 18, y + 7), text, font=f1, fill=t["accent"])
    d.text((x + 28 + w1, y + 13), sub, font=f2, fill=t["muted"])
    return w


def draw_card(theme: str, atom_png: list[Path], md_png: list[Path], captions: list[tuple[str, str, str]], stats: list[list[str]], times: list[float] | None = None) -> Image.Image:
    t = THEMES[theme]
    W, H = 1800, 1350
    im = Image.new("RGB", (W, H), t["page"])
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([6, 6, W - 7, H - 7], 36, outline=t["line"], width=3)
    d.text((70, 62), "   ".join(" ".join(w) for w in "PERSONAL CARE SEMINAR".split()) + "   ·   O C T O B E R   2 0 2 6   ·   D R Y   L A B", font=font(21, True), fill=t["accent"])
    d.text((66, 96), "Stepan Surfactant Cheminformatics", font=font(92, True), fill=t["ink"])
    d.text((70, 214), "Six seminar decks as one interactive cheminformatics dry lab: every chart rebuilt, every formula", font=font(30), fill=t["muted"])
    d.text((70, 254), "transcribed, every surfactant as a structure, and the micelles and bilayers they form, simulated.", font=font(30), fill=t["muted"])
    d.text((70, 306), CREDIT_LINE, font=font(24), fill=t["muted"])
    x = 70
    for num, lab in stats[:6]:
        x += pill(d, (x, 362), num, lab, t, font(26, True), font(22)) + 14
    top = 450
    colw = 537
    gx = 70
    for k, (cap, sub1, sub2) in enumerate(captions):
        d.rounded_rectangle([gx, top, gx + colw, top + 2 * PH + 190], 26, fill=t["panel"], outline=t["line"], width=2)
        d.text((gx + 20, top + 12), "ATOMISTIC MODEL, GEOMETRIC", font=font(15, True), fill=t["muted"])
        im.paste(Image.open(atom_png[k]).convert("RGB"), (gx + 10, top + 34))
        d.text((gx + 20, top + PH + 44), "COARSE-GRAINED MOLECULAR DYNAMICS" + (f"   ·   t = {times[k]:.1f} ns" if times else ""), font=font(15, True), fill=t["muted"] if not times else t["accent2"])
        im.paste(Image.open(md_png[k]).convert("RGB"), (gx + 10, top + PH + 66))
        d.text((gx + 20, top + 2 * PH + 84), cap, font=font(30, True), fill=t["ink"])
        d.text((gx + 20, top + 2 * PH + 122), sub1, font=font(22), fill=t["accent2"])
        d.text((gx + 20, top + 2 * PH + 152), sub2, font=font(20), fill=t["muted"])
        gx += colw + 24
    d.text((70, H - 78), "Half of each picture is cut away. The simulations start from random chains in water; the force field is a simplified MARTINI-style model.", font=font(21), fill=t["muted"])
    d.text((70, H - 46), "Drawn with PyMOL. The results are modelled, not measured.", font=font(21), fill=t["muted"])
    return im


def compose(theme: str, atom_png: list[Path], md_png: list[Path], captions: list[tuple[str, str, str]], stats: list[list[str]], out: Path) -> None:
    draw_card(theme, atom_png, md_png, captions, stats).save(out, optimize=True)


HOLD = 8  # extra frames at the end of the animation, in which the simulations rest on their last frame and the models keep turning


def save_gif(frames: list[Image.Image], out: Path, duration: int = 120, colours: int = 128) -> None:
    pal = frames[len(frames) // 2].quantize(colors=colours, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    q = [f.quantize(palette=pal, dither=Image.Dither.NONE) for f in frames]
    q[0].save(out, save_all=True, append_images=q[1:], duration=duration, loop=0, optimize=True, disposal=1)


def animate(theme: str, man: dict, systems: dict, runs: dict, atoms: dict, captions: list, work: Path, width: int = 1350) -> Path:
    """The README figure as an animation: the atomistic models turn about a vertical axis and the simulations play from the random start to the end."""
    t = THEMES[theme]
    n = min(len(r["frames"]) for r in runs.values())
    total = n + HOLD
    jobs = []
    for k in range(total):
        angle = 2 * math.pi * k / total
        for sid, shape, _ in COLUMNS:
            tmp, ref = work / f"{theme}_{sid}_a_{k:02d}.pdb", work / f"{sid}_a_full.pdb"
            write_cut(*atoms[sid], angle, True, tmp)
            if not ref.exists():
                write_cut(*atoms[sid], 0.0, False, ref)
            jobs.append(dict(pdb=tmp, ref=ref, png=work / f"{theme}_{sid}_a_{k:02d}.png", bg=t["panel"], buf=ZOOM[shape], kind="atoms", species=systems[sid]["species"]))
            if k < n:
                lines, xyz, resid = lines_to_arrays(md_frame_lines(runs[sid], k))
                tmp2, ref2 = work / f"{theme}_{sid}_m_{k:02d}.pdb", work / f"{sid}_m_full.pdb"
                write_cut(lines, xyz, resid, 0.0, True, tmp2)
                if not ref2.exists():
                    lines2, xyz2, resid2 = lines_to_arrays(md_frame_lines(runs[sid], len(runs[sid]["frames"]) - 1))
                    write_cut(lines2, xyz2, resid2, 0.0, False, ref2)
                jobs.append(dict(pdb=tmp2, ref=ref2, png=work / f"{theme}_{sid}_m_{k:02d}.png", bg=t["panel"], buf=ZOOM_MD[sid], kind="beads", species={}))
    run_pymol(pml_for(jobs, (PW, PH)), work)
    frames = []
    for k in range(total):
        kk = min(k, n - 1)
        im = draw_card(theme, [work / f"{theme}_{sid}_a_{k:02d}.png" for sid, _, _ in COLUMNS], [work / f"{theme}_{sid}_m_{kk:02d}.png" for sid, _, _ in COLUMNS],
                       captions, man["stats"], [runs[sid]["frame_t_ns"][kk] for sid, _, _ in COLUMNS])
        frames.append(im.resize((width, round(im.height * width / im.width)), Image.Resampling.LANCZOS))
    out = CARD / f"stepan_card_animated-{theme}.gif"
    save_gif(frames, out)
    print("wrote", out, round(out.stat().st_size / 1e6, 2), "MB", len(frames), "frames")
    return out


def main() -> None:
    man = json.loads((MODELS / "manifest.json").read_text(encoding="utf-8"))
    systems = {s["id"]: s for s in man["systems"]}
    runs = {sid: json.loads((MDDIR / f"{sid}.json").read_text(encoding="utf-8")) for sid, _, _ in COLUMNS}
    work = Path(tempfile.mkdtemp(prefix="stepan_card_"))
    try:
        atoms = {sid: read_pdb(MODELS / systems[sid]["files"][shape]) for sid, shape, _ in COLUMNS}
        captions = []
        for sid, shape, cap in COLUMNS:
            r = runs[sid]
            s = r["summary"]
            n_atoms = len(atoms[sid][0])
            mono = len(np.unique(atoms[sid][2]))
            captions.append((cap, f"{mono}-monomer {shape} model, {n_atoms:,} atoms", f"MD: {r['molecules']} molecules, {r['ns']:g} ns, largest aggregate {s['largest_aggregate']:.0f}"))
        want = set(sys.argv[1:]) or {"static", "dark", "light"}
        for theme in [x for x in ("dark", "light") if x in want]:
            animate(theme, man, systems, runs, atoms, captions, work)
        for theme, t in THEMES.items():
            if "static" not in want:
                continue
            jobs, ap, mp = [], [], []
            for sid, shape, _ in COLUMNS:
                tmp, ref = work / f"{sid}_a_cut.pdb", work / f"{sid}_a_full.pdb"
                write_cut(*atoms[sid], 0.0, True, tmp)
                write_cut(*atoms[sid], 0.0, False, ref)
                png = work / f"{theme}_{sid}_a.png"
                jobs.append(dict(pdb=tmp, ref=ref, png=png, bg=t["panel"], buf=ZOOM[shape], kind="atoms", species=systems[sid]["species"]))
                ap.append(png)
                last = len(runs[sid]["frames"]) - 1
                lines, xyz, resid = lines_to_arrays(md_frame_lines(runs[sid], last))
                tmp2, ref2 = work / f"{sid}_m_cut.pdb", work / f"{sid}_m_full.pdb"
                write_cut(lines, xyz, resid, 0.0, True, tmp2)
                write_cut(lines, xyz, resid, 0.0, False, ref2)
                png2 = work / f"{theme}_{sid}_m.png"
                jobs.append(dict(pdb=tmp2, ref=ref2, png=png2, bg=t["panel"], buf=ZOOM_MD[sid], kind="beads", species={}))
                mp.append(png2)
            run_pymol(pml_for(jobs, (PW, PH)), work)
            compose(theme, ap, mp, captions, man["stats"], CARD / f"stepan_card-{theme}.png")
            print("wrote", CARD / f"stepan_card-{theme}.png")
    finally:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    main()
