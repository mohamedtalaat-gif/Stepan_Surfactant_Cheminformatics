# Created by Muhammad Talaat, Faculty of Pharmacy, Ain Shams University
# SPDX-FileCopyrightText: 2026 Muhammad Talaat
# SPDX-License-Identifier: MIT
"""One HTML page, used by the card in docs/ and by the notebooks, that shows the 3D models with 3Dmol.js.

3Dmol.js (BSD-3-Clause, University of Pittsburgh) is read from docs/card/vendor and inlined, so the page
needs no network.  The data are one JSON object: ``systems`` (aggregates) and ``molecules`` (single structures).
"""

from __future__ import annotations

import html
import json
from pathlib import Path

from .provenance import CREDIT_LINE

VENDOR = Path(__file__).resolve().parents[2] / "docs" / "card" / "vendor"

CSS = """
:root{--page:#0b1020;--ink:#eef2ff;--muted:#a5b1cf;--panel:#111a30;--line:#27355a;--accent:#ff7a90;--accent2:#35d0ba;--chip:rgba(255,122,144,.12)}
:root[data-theme=light]{--page:#f5f7fc;--ink:#14213d;--muted:#56648a;--panel:#fff;--line:#d6deef;--accent:#d6385a;--accent2:#0f9d8a;--chip:rgba(214,56,90,.09)}
*{box-sizing:border-box}html,body{margin:0}body{background:var(--page);color:var(--ink);font-family:'Avenir Next','Helvetica Neue',Arial,sans-serif}
.card{max-width:1400px;margin:0 auto;padding:26px 22px 34px;display:grid;gap:16px;grid-template-columns:minmax(0,5fr) minmax(0,7fr);grid-template-areas:"head view" "stats view" "strip strip" "note note"}
.compact{padding:8px;grid-template-columns:1fr;grid-template-areas:"view" "strip"}
@media(max-width:900px){.card{grid-template-columns:1fr;grid-template-areas:"head" "view" "stats" "strip" "note"}}
header{grid-area:head;min-width:0}.eyebrow{font-size:12px;letter-spacing:4px;font-weight:700;color:var(--accent)}
h1{margin:6px 0 0;font-size:clamp(34px,5.4vw,70px);line-height:1;font-weight:800;letter-spacing:-2px}
.lede{margin:12px 0 0;font-size:18px;line-height:1.45;color:var(--muted)}.by{margin-top:10px;font-size:13px;color:var(--muted)}
.chips{margin-top:14px;display:flex;flex-wrap:wrap;gap:8px}.chip{padding:6px 14px;border-radius:999px;background:var(--chip);border:1.5px solid var(--accent);font-size:14px;font-weight:700}
.stats{grid-area:stats;display:grid;gap:10px;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));align-content:start}
.stat{padding:10px 12px;border-radius:14px;border:1.5px solid var(--line);background:var(--panel);cursor:help}
.num{font-size:clamp(18px,2.2vw,26px);font-weight:800;color:var(--accent)}.lab{font-size:12.5px;line-height:1.3;color:var(--muted);margin-top:2px}
.view{grid-area:view;position:relative;border-radius:22px;overflow:hidden;border:1.5px solid var(--line);background:var(--panel);min-height:430px}
#v{width:100%;height:min(60vh,540px);min-height:380px;position:relative}
.bar{position:relative;padding:10px;display:flex;flex-wrap:wrap;gap:6px;z-index:5;border-bottom:1.5px solid var(--line)}
.bar .sep{width:8px}.bar button,.bar select{padding:6px 11px;border-radius:10px;border:1.5px solid var(--line);background:var(--panel);color:var(--ink);font:inherit;font-size:13px;font-weight:600;cursor:pointer}
.bar button[aria-pressed=true]{border-color:var(--accent);color:var(--accent)}.bar button:disabled{opacity:.4;cursor:default}
.mdbar{display:none;align-items:center;gap:12px;padding:8px 14px;border-top:1.5px solid var(--line);flex-wrap:wrap}.mdbar button{padding:6px 14px;border-radius:10px;border:1.5px solid var(--line);background:var(--panel);color:var(--ink);font:inherit;font-size:13px;font-weight:600;cursor:pointer}.mdbar input{flex:1 1 160px;accent-color:var(--accent)}.mdbar #tlabel{font-weight:700;min-width:64px;color:var(--accent2);font-size:13.5px}.mdbar svg{width:240px;height:46px;border:1.5px solid var(--line);border-radius:8px}
.foot{display:flex;flex-wrap:wrap;justify-content:space-between;gap:6px 18px;padding:9px 14px;border-top:1.5px solid var(--line)}
.reading{flex:1 1 320px;font-size:13.5px;font-weight:600;line-height:1.4}.reading span{color:var(--accent2)}
.legend{font-size:12.5px;text-align:right;color:var(--muted)}.legend i{display:inline-block;width:10px;height:10px;border-radius:50%;margin:0 5px 0 10px}
.strip{grid-area:strip;display:grid;gap:12px;grid-template-columns:repeat(auto-fill,minmax(210px,1fr))}
.tile{all:unset;box-sizing:border-box;cursor:pointer;border-radius:16px;border:1.5px solid var(--line);background:var(--panel);overflow:hidden;display:flex;flex-direction:column}
.tile[aria-pressed=true]{border-color:var(--accent);box-shadow:0 0 0 2px var(--accent)}.tile:hover{border-color:var(--accent)}.tile:focus-visible,.bar button:focus-visible{outline:3px solid var(--accent2);outline-offset:2px}
.tile .sk{height:120px;display:flex;align-items:center;justify-content:center;padding:6px;color:var(--ink)}.tile .sk svg{width:100%;height:100%}
.tile .cap{padding:8px 12px;border-top:1.5px solid var(--line);font-size:14px}.tile .cap b{display:block}.tile .cap span{color:var(--accent2);font-weight:700;font-size:13px}
.note{grid-area:note;font-size:13.5px;line-height:1.5;color:var(--muted)}.note a{color:var(--accent2)}
.theme{position:fixed;right:12px;top:10px;z-index:9;padding:6px 12px;border-radius:10px;border:1.5px solid var(--line);background:var(--panel);color:var(--ink);font:inherit;font-size:13px;font-weight:600;cursor:pointer}
"""

JS = r"""
(function(){
const D = DATA, root = document.documentElement;
const th = matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark'; if(!root.dataset.theme) root.dataset.theme = th;
document.getElementById('theme') && (document.getElementById('theme').onclick = () => { root.dataset.theme = root.dataset.theme === 'dark' ? 'light' : 'dark'; });
const el = document.getElementById('v'), reading = document.getElementById('reading'), legend = document.getElementById('legend');
const viewer = $3Dmol.createViewer(el, {backgroundAlpha: 0});
const ELEM = {C:0x9aa5b1,H:0xe6ecf5,N:0x4f86ff,O:0xff5252,S:0xffd23f,P:0xff9f43,Na:0xb48cff,Cl:0x59d97a};
let st = {kind:'system', mode:'model', sys:D.systems.length ? D.systems[0].id : null, mol:D.molecules.length ? D.molecules[0].key : null, shape:null, style:'spheres', colour:'species', spin:false, cut:false, frame:0};
const q = id => document.getElementById(id);
const TCOL = {T:0x35d0ba, N:0xb48cff, P:0xff9f43, A:0xff7a90, C:0x5b9dff}, TNAME = {T:'chain', N:'semi-polar head', P:'polar head', A:'anionic head', C:'cationic head'};
const SPC = [0x35d0ba, 0xff7a90, 0x5b9dff, 0xb48cff, 0xffc83d, 0x6fd14d];
const hexs = c => '#' + c.toString(16).padStart(6,'0');
let timer = null;
function sysObj(){ return D.systems.find(s => s.id === st.sys); }
function molObj(){ return D.molecules.find(m => m.key === st.mol); }
function hasMd(S){ return !!(S && S.md); }
function hasShapes(S){ return !!(S && S.shapes && Object.keys(S.shapes).length); }
function mode(){ if (st.kind !== 'system') return 'model'; const S = sysObj(); if (!hasMd(S)) return 'model'; if (!hasShapes(S)) return 'md'; return st.mode; }
function stopPlay(){ if (timer) { clearInterval(timer); timer = null; } q('play').textContent = 'Play'; }
function colorFor(a, ren, species){
  if (st.colour === 'species' && species) return a.elem === 'C' ? (species[a.resn] || 0x9aa5b1) : 0xffc83d;
  if (st.colour === 'renewable') { const r = ren ? ren.has(a.index) : a.b > 0.5; return r ? 0x6fd14d : (a.elem === 'C' ? 0x56627a : (ELEM[a.elem] || 0xcccccc)); }
  return ELEM[a.elem] || 0xcccccc;
}
function cutAway(){
  const at = viewer.selectedAtoms({}); let cz = 0; at.forEach(a => cz += a.z); cz /= at.length;
  const ids = at.filter(a => a.z > cz).map(a => a.serial); if (ids.length) viewer.setStyle({serial: ids}, {});
}
function apply(ren, species, big){
  const f = a => colorFor(a, ren, species);
  let s = st.style;
  if (s === 'surface' && big) s = 'spheres';
  viewer.removeAllSurfaces();
  if (s === 'sticks') viewer.setStyle({}, {stick:{colorfunc:f, radius:0.16}, sphere:{colorfunc:f, scale:0.22}});
  else viewer.setStyle({}, {sphere:{colorfunc:f, scale: big ? 0.55 : 0.34}, stick:{colorfunc:f, radius:0.12}});
  if (s === 'surface' && !st.cut) { viewer.setStyle({}, {stick:{colorfunc:f, radius:0.1}}); viewer.addSurface($3Dmol.SurfaceType.SAS, {opacity:0.78, colorfunc:f}); }
  if (st.cut && !ren) cutAway();
}
function mdPdb(M, k){
  const f = M.frames[k], b = M.beads, out = [];
  for (let i = 0; i < b.length; i++) {
    out.push('HETATM' + String(i + 1).padStart(5) + ' ' + (b[i].type + '   ').slice(0, 4) + ' BEA A' + String((b[i].mol % 9999) + 1).padStart(4) + '    ' + f[3*i].toFixed(3).padStart(8) + f[3*i+1].toFixed(3).padStart(8) + f[3*i+2].toFixed(3).padStart(8) + '  1.00  0.00          ' + (b[i].type === 'T' ? ' C' : ' O'));
  }
  M.bonds.forEach(e => out.push('CONECT' + String(e[0] + 1).padStart(5) + String(e[1] + 1).padStart(5)));
  return out.join('\n');
}
function spark(M, t){
  const s = M.series, n = s.t_ns.length, T = s.t_ns[n - 1], mx = Math.max(...s.largest, 1);
  const pts = arr => arr.map((v, i) => (s.t_ns[i] / T * 236 + 2).toFixed(1) + ',' + (44 - v / mx * 40).toFixed(1)).join(' ');
  const x = (t / T * 236 + 2).toFixed(1);
  q('spark').innerHTML = `<polyline points="${pts(s.largest)}" fill="none" stroke="var(--accent2)" stroke-width="1.6"/><polyline points="${pts(s.mean_agg)}" fill="none" stroke="var(--accent)" stroke-width="1.6"/><line x1="${x}" x2="${x}" y1="0" y2="46" stroke="var(--ink)" stroke-width="1" opacity=".6"/>`;
}
function showMd(S, fit){
  const M = S.md; st.frame = Math.max(0, Math.min(st.frame, M.frames.length - 1));
  viewer.clear(); viewer.addModel(mdPdb(M, st.frame), 'pdb');
  const names = [...new Set(M.beads.map(b => b.species))];
  const f = a => { const b = M.beads[a.serial - 1]; return st.colour === 'bead' ? (TCOL[b.type] || 0xcccccc) : SPC[names.indexOf(b.species) % SPC.length]; };
  viewer.removeAllSurfaces();
  if (st.style === 'sticks') viewer.setStyle({}, {stick:{colorfunc:f, radius:0.45}, sphere:{colorfunc:f, radius:0.9}});
  else viewer.setStyle({}, {sphere:{colorfunc:f, radius:2.1}, stick:{colorfunc:f, radius:0.35}});
  if (st.cut) cutAway();
  const t = M.frame_t_ns[st.frame], ser = M.series, i = Math.max(0, Math.min(ser.t_ns.length - 1, Math.round(t / (ser.t_ns[1] - ser.t_ns[0]))));
  reading.innerHTML = `<b>${S.name}</b> &middot; coarse-grained molecular dynamics &middot; ${M.molecules} molecules in a ${M.box_nm} nm box &middot; t = <span>${t.toFixed(1)} ns</span> &middot; largest aggregate <span>${ser.largest[i]}</span> &middot; aggregates <span>${ser.aggregates[i]}</span> &middot; free molecules <span>${Math.round(ser.free_fraction[i] * 100)}%</span>`;
  legend.innerHTML = st.colour === 'bead' ? Object.keys(TNAME).filter(k => M.beads.some(b => b.type === k)).map(k => `<i style="background:${hexs(TCOL[k])}"></i>${TNAME[k]}`).join('') : names.map((n, j) => `<i style="background:${hexs(SPC[j % SPC.length])}"></i>${(M.species_names && M.species_names[n]) || n}`).join('');
  const sl = q('tslider'); sl.max = M.frames.length - 1; sl.value = st.frame; q('tlabel').textContent = t.toFixed(1) + ' ns'; spark(M, t);
  if (fit !== false) viewer.zoomTo(); viewer.render(); viewer.spin(st.spin ? 'y' : false, 0.7);
}
function show(fit){
  const S = st.kind === 'system' ? sysObj() : null;
  if (mode() === 'md' && S) { showMd(S, fit); return; }
  stopPlay(); viewer.clear();
  let ren = null, species = null, big = false, text = '', leg = '';
  if (st.kind === 'system') {
    if (!S) return; const sh = S.shapes[st.shape] ? st.shape : Object.keys(S.shapes)[0]; st.shape = sh; const A = S.shapes[sh];
    viewer.addModel(A.pdb, 'pdb'); species = {}; S.species.forEach(x => species[x.resn] = parseInt(x.colour.slice(1), 16)); big = true;
    text = `<b>${S.name}</b> &middot; ${A.label} &middot; <span>${A.monomers}</span> monomers &middot; packing parameter <span>${A.p}</span> &middot; radius about <span>${A.radius} &Aring;</span> &middot; ${A.atoms} heavy atoms`;
    if (st.colour === 'species') leg = S.species.map(x => `<i style="background:${x.colour}"></i>${x.name}`).join('') + '<i style="background:#ffc83d"></i>head atoms (O, N, S)';
    else if (st.colour === 'renewable') leg = '<i style="background:#6fd14d"></i>renewable carbon<i style="background:#56627a"></i>other carbon';
  } else {
    const M = molObj(); if (!M) return; viewer.addModel(M.sdf, 'sdf'); ren = new Set(M.renewable);
    text = `<b>${M.name}</b> &middot; ${M.family} &middot; ${M.formula} &middot; M <span>${M.mw}</span> &middot; radius of gyration <span>${M.rg} &Aring;</span> &middot; shape NPR1/NPR2 <span>${M.npr1}/${M.npr2}</span> &middot; renewable carbon <span>${M.renew}</span>`;
    leg = st.colour === 'renewable' ? '<i style="background:#6fd14d"></i>renewable carbon<i style="background:#56627a"></i>other carbon' : '';
  }
  apply(ren, species, big); reading.innerHTML = text; legend.innerHTML = leg;
  if (fit !== false) viewer.zoomTo(); viewer.render(); viewer.spin(st.spin ? 'y' : false, 0.7);
}
function marks(){
  const md = mode() === 'md', S = st.kind === 'system' ? sysObj() : null;
  document.querySelectorAll('[data-style]').forEach(b => { b.setAttribute('aria-pressed', b.dataset.style === st.style); if (b.dataset.style === 'surface') b.disabled = md; });
  document.querySelectorAll('[data-colour]').forEach(b => { b.setAttribute('aria-pressed', b.dataset.colour === st.colour); const k = b.dataset.colour; b.style.display = md ? (k === 'species' || k === 'bead' ? '' : 'none') : (k === 'bead' ? 'none' : ''); });
  document.querySelectorAll('[data-shape]').forEach(b => { b.setAttribute('aria-pressed', b.dataset.shape === st.shape && st.kind === 'system'); b.disabled = md || st.kind !== 'system' || !(S && hasShapes(S) && S.shapes[b.dataset.shape]); });
  document.querySelectorAll('[data-mode]').forEach(b => { b.style.display = (S && hasMd(S) && hasShapes(S)) ? '' : 'none'; b.setAttribute('aria-pressed', b.dataset.mode === mode()); });
  document.querySelectorAll('.tile').forEach(t => t.setAttribute('aria-pressed', (st.kind === 'system' && t.dataset.sys === st.sys) || (st.kind === 'molecule' && t.dataset.sys === 'mol')));
  q('spin').setAttribute('aria-pressed', st.spin); q('cut').setAttribute('aria-pressed', st.cut); q('cut').disabled = st.kind !== 'system';
  q('mdbar').style.display = md ? 'flex' : 'none';
  const ms = q('molpick'); if (ms) ms.style.display = st.kind === 'molecule' && D.molecules.length > 1 ? '' : 'none';
}
document.querySelectorAll('[data-style]').forEach(b => b.onclick = () => { st.style = b.dataset.style; marks(); show(false); });
document.querySelectorAll('[data-colour]').forEach(b => b.onclick = () => { st.colour = b.dataset.colour; marks(); show(false); });
document.querySelectorAll('[data-shape]').forEach(b => b.onclick = () => { st.shape = b.dataset.shape; st.kind = 'system'; st.mode = 'model'; marks(); show(); });
document.querySelectorAll('[data-mode]').forEach(b => b.onclick = () => { st.mode = b.dataset.mode; st.colour = st.mode === 'md' ? 'bead' : 'species'; st.frame = st.mode === 'md' ? Math.max(0, (sysObj().md.frames.length - 1)) : st.frame; marks(); show(); });
q('spin').onclick = () => { st.spin = !st.spin; marks(); viewer.spin(st.spin ? 'y' : false, 0.7); };
q('cut').onclick = () => { st.cut = !st.cut; marks(); show(false); };
q('reset').onclick = () => { viewer.zoomTo(); viewer.render(); };
q('play').onclick = () => {
  if (timer) { stopPlay(); return; }
  const S = sysObj(); if (!S || !hasMd(S)) return; q('play').textContent = 'Pause';
  timer = setInterval(() => { st.frame = (st.frame + 1) % S.md.frames.length; showMd(S, false); }, 140);
};
q('tslider').oninput = e => { stopPlay(); st.frame = parseInt(e.target.value, 10); const S = sysObj(); if (S && hasMd(S)) showMd(S, false); };
document.querySelectorAll('.tile').forEach(t => t.onclick = () => {
  if (t.dataset.sys === 'mol') { stopPlay(); st.kind = 'molecule'; st.style = 'sticks'; if (st.colour === 'species' || st.colour === 'bead') st.colour = 'element'; }
  else { stopPlay(); st.kind = 'system'; st.sys = t.dataset.sys; st.shape = null; st.style = 'spheres'; const S = sysObj(); st.mode = 'model'; st.colour = (hasMd(S) && !hasShapes(S)) ? 'bead' : 'species'; st.frame = hasMd(S) ? S.md.frames.length - 1 : 0; }
  marks(); show();
});
const mp = q('molpick'); if (mp) { D.molecules.forEach(m => { const o = document.createElement('option'); o.value = m.key; o.textContent = m.name; mp.appendChild(o); }); mp.onchange = () => { st.mol = mp.value; st.kind = 'molecule'; stopPlay(); marks(); show(); }; }
const first = D.systems.length ? D.systems[0] : null; if (!first) { st.kind = 'molecule'; }
else if (hasMd(first) && !hasShapes(first)) { st.colour = 'bead'; st.frame = first.md.frames.length - 1; }
marks(); show();
})();
"""


def _tile(system) -> str:
    return (f'<button class="tile" data-sys="{html.escape(system["id"])}" aria-pressed="false" aria-label="{html.escape(system["name"])}">'
            f'<div class="sk">{system["svg"]}</div><div class="cap"><b>{html.escape(system["name"])}</b><span>{html.escape(system["caption"])}</span></div></button>')


def page(data: dict, compact: bool = False, title: str = "Stepan Surfactant Chemistry: a Cheminformatics Dry Lab") -> str:
    """Self-contained HTML page for the given data (``systems``, ``molecules``, ``stats``, ``tile_mol_svg``)."""
    lib = (VENDOR / "3Dmol-min.js").read_text(encoding="utf-8")
    tiles = "".join(_tile(s) for s in data["systems"])
    if data.get("tile_mol_svg"):
        tiles += (f'<button class="tile" data-sys="mol" aria-pressed="false"><div class="sk">{data["tile_mol_svg"]}</div>'
                  f'<div class="cap"><b>Any molecule</b><span>{len(data["molecules"])} structures in 3D</span></div></button>')
    stats = "".join(f'<div class="stat" title="{html.escape(t)}"><div class="num">{html.escape(n)}</div><div class="lab">{html.escape(l)}</div></div>' for n, l, t in data.get("stats", []))
    head = "" if compact else (
        '<header><div class="eyebrow">PERSONAL CARE SEMINAR &middot; OCTOBER 2026 &middot; CHEMINFORMATICS DRY LAB</div><h1>Stepan Surfactant Chemistry</h1>'
        '<p class="lede">Every chart of six seminar decks rebuilt from the slides, every formula transcribed, every surfactant as a structure. '
        'Below, the same structures as three-dimensional models and as the aggregates they form.</p>'
        f'<div class="by">{html.escape(CREDIT_LINE)}</div>'
        '</header>'
        f'<div class="stats">{stats}</div>')
    note = "" if compact else (
        '<div class="note">The molecules are embedded with ETKDG and relaxed with MMFF94 (RDKit); the most extended conformer within 12 kcal/mol of the lowest is shown. '
        'The atomistic micelles and bilayers (<b>Model</b>) are geometric: relaxed monomers placed tail-in on a sphere, a capsule or two sheets, with the number of monomers taken from the packing model. '
        'The <b>Dynamics</b> view is a coarse-grained molecular dynamics simulation (OpenMM, explicit water, a MARTINI-style bead model with my own bead assignment, 20 fs steps, 310 K) '
        'that started from random chains, so every aggregate in it formed during the run; it is a model, not a measurement. The notebooks recompute every number; to run them, follow the instructions in the README. '
        '3D view: 3Dmol.js (BSD-3-Clause).</div>')
    body = f"""<main class="card{' compact' if compact else ''}">{head}
<section class="view"><div class="bar" role="toolbar" aria-label="Viewer controls">
<button data-mode="model">Model</button><button data-mode="md">Dynamics</button><span class="sep"></span><button id="spin" aria-pressed="false">Spin</button><button id="cut" aria-pressed="false" title="Hide the front half to see the inside">Cut away</button><button id="reset">Reset view</button><span class="sep"></span>
<button data-shape="sphere">Sphere</button><button data-shape="rod">Rod</button><button data-shape="bilayer">Bilayer</button><span class="sep"></span>
<button data-style="spheres">Spheres</button><button data-style="sticks">Sticks</button><button data-style="surface">Surface</button><span class="sep"></span>
<button data-colour="species">By species</button><button data-colour="bead">By bead type</button><button data-colour="element">By element</button><button data-colour="renewable">Renewable carbon</button>
<select id="molpick" aria-label="Molecule" style="display:none"></select></div>
<div id="v" role="img" aria-label="Interactive three-dimensional model"></div>
<div class="mdbar" id="mdbar"><button id="play">Play</button><input id="tslider" type="range" min="0" max="0" value="0" aria-label="Simulation time"><span id="tlabel"></span><svg id="spark" viewBox="0 0 240 46" preserveAspectRatio="none" role="img" aria-label="Largest aggregate (teal) and mean aggregate size (pink) against time"></svg></div><div class="foot"><div class="reading" id="reading"></div><div class="legend" id="legend"></div></div></section>
<section class="strip">{tiles}</section>{note}</main>"""
    theme = "" if compact else '<button class="theme" id="theme" aria-label="Switch between the dark and the light theme">Theme</button>'
    return (f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{html.escape(title)}</title>'
            f'<style>{CSS}</style></head><body>{theme}{body}<script>{lib}</script><script>const DATA={json.dumps(data, separators=(",", ":"))};{JS}</script></body></html>')
