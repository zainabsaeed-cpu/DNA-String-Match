"""GeneFlow web app with UI aligned to geneflow_v2.html and live DFA matching."""

from __future__ import annotations

import html
from textwrap import dedent
from typing import Dict, List, Tuple

import streamlit as st

try:
    from Bio import SeqIO

    HAS_BIO = True
except ImportError:
    HAS_BIO = False

from dfa import ALPHABET, get_transition_table
from matcher import find_matches
from genome_loader import load_genome_text, load_uploaded_genome

st.set_page_config(
    page_title="GeneFlow - DNA String Matching",
    page_icon=":dna:",
    layout="wide",
    initial_sidebar_state="collapsed",
)


def clean_dna(seq: str) -> str:
    return "".join(ch for ch in seq.upper() if ch in ALPHABET)


def parse_uploaded_fasta(uploaded_file) -> str:
    if not uploaded_file:
        raise ValueError("Select a FASTA file first.")
  if HAS_BIO:
    if hasattr(uploaded_file, "seek"):
      uploaded_file.seek(0)
    chunks: List[str] = []
    for rec in SeqIO.parse(uploaded_file, "fasta"):
      chunks.append(clean_dna(str(rec.seq)))
    merged = "".join(chunks)
    if merged:
      return merged

  # Fallback parser handles both FASTA and plain-text DNA uploads.
  try:
    return load_uploaded_genome(uploaded_file)
  except Exception:
    if hasattr(uploaded_file, "seek"):
      uploaded_file.seek(0)
    raw = uploaded_file.read()
    if isinstance(raw, bytes):
      text = raw.decode("utf-8", errors="ignore")
    else:
      text = str(raw)
    return load_genome_text(text)


def run_analysis(pattern: str, genome: str) -> Tuple[Dict[int, Dict[str, int]], int, List[int]]:
    delta, accept_state = get_transition_table(pattern)
    matches = find_matches(genome, delta, accept_state, len(pattern))
    return delta, accept_state, matches


def dfa_rows_html(delta: Dict[int, Dict[str, int]], accept_state: int) -> str:
    subs = str.maketrans("0123456789", "₀₁₂₃₄₅₆₇₈₉")

    def q_label(state: int) -> str:
        return "q" + str(state).translate(subs)

    rows: List[str] = []
    for state in range(len(delta)):
        label_class = "state-name accept" if state == accept_state else "state-name"
        cells = [f'<td class="{label_class}">{q_label(state)}</td>']
        for base in ALPHABET:
            next_state = q_label(delta[state][base])
            if state == accept_state and delta[state][base] == accept_state:
                cells.append(f'<td class="accept">{next_state} ✓</td>')
            else:
                cells.append(f"<td>{next_state}</td>")
        rows.append("<tr>" + "".join(cells) + "</tr>")
    return "\n".join(rows)


def genome_html(genome: str, pattern: str, matches: List[int], max_len: int = 420) -> str:
    snippet = genome[:max_len]
    mask = [False] * len(snippet)
    plen = len(pattern)

    for start in matches:
        s = start - 1
        e = min(s + plen, len(snippet))
        for idx in range(max(0, s), e):
            mask[idx] = True

    cls = {"A": "b-a", "T": "b-t", "C": "b-c", "G": "b-g"}
    out: List[str] = []
    for i, ch in enumerate(snippet):
        c = cls.get(ch, "")
        span_cls = f"b-match {c}" if mask[i] else c
        out.append(f'<span class="{span_cls}">{html.escape(ch)}</span>')
    return "".join(out)


def bars_html(matches: List[int], genome_len: int, bars: int = 18) -> str:
    if genome_len <= 0:
        return "".join('<div class="bar" style="height:18%"></div>' for _ in range(bars))

    buckets = [0] * bars
    for pos in matches:
        idx = min(bars - 1, int((pos / max(1, genome_len)) * bars))
        buckets[idx] += 1

    peak = max(buckets) if buckets else 1
    result: List[str] = []
    for count in buckets:
        height = 16 if peak == 0 else 16 + int((count / peak) * 84)
        hi = " hi" if count > 0 and count == peak else ""
        result.append(f'<div class="bar{hi}" style="height:{height}%"></div>')
    return "".join(result)


if "pattern" not in st.session_state:
    st.session_state.pattern = "ATCG"
if "genome" not in st.session_state:
    st.session_state.genome = "ATGCATGCTTAGCATCGATCTAGTACGTAATCGCATGATGCTTAATCG"
if "dfa" not in st.session_state:
    st.session_state.dfa = {}
if "accept_state" not in st.session_state:
    st.session_state.accept_state = 0
if "matches" not in st.session_state:
    st.session_state.matches = []
if "status" not in st.session_state:
    st.session_state.status = ""
if "hero_svg" not in st.session_state:
    from dna_visuals import generate_dna_helix_svg

    st.session_state.hero_svg = generate_dna_helix_svg()

HELIX_COMPONENT_HTML = """
<canvas id="helix-canvas" style="display:block;width:100%;height:500px;background:transparent;"></canvas>
<script>
const canvas = document.getElementById('helix-canvas');
const ctx = canvas.getContext('2d');

function resize() {
  canvas.width = canvas.offsetWidth * devicePixelRatio;
  canvas.height = canvas.offsetHeight * devicePixelRatio;
  ctx.setTransform(1,0,0,1,0,0);
  ctx.scale(devicePixelRatio, devicePixelRatio);
}
resize();
window.addEventListener('resize', resize);

const W = () => canvas.offsetWidth;
const H = () => canvas.offsetHeight;
const BASES = ['A','T','C','G'];
const PERIOD = 90;
const AMPLITUDE = 110;
const STEP_Y = 13;
const N = 52;
let t = 0;

const COLORS = {
  strand1: '#2e4a6e',
  strand2: '#7a9ec0',
  A: '#9060c0',
  T: '#b08020',
  C: '#1a8870',
  G: '#c04040',
  rung: 'rgba(60,100,150,0.10)',
  fade: 'rgba(232,238,245,'
};

function pt(i, phase, time) {
  const cx = W() / 2;
  const totalH = N * STEP_Y;
  const startY = (H() - totalH) / 2;
  const x = cx + Math.sin((i * Math.PI * 2 / PERIOD) + time + phase) * AMPLITUDE;
  const y = startY + i * STEP_Y;
  return { x, y, z: Math.sin((i * Math.PI * 2 / PERIOD) + time + phase) };
}

function drawStrand(phase, color, dash) {
  ctx.beginPath();
  ctx.setLineDash(dash || []);
  ctx.strokeStyle = color;
  ctx.lineWidth = 2;
  for (let i = 0; i < N; i++) {
    const p = pt(i, phase, t);
    if (i === 0) { ctx.moveTo(p.x, p.y); continue; }
    const prev = pt(i - 1, phase, t);
    ctx.quadraticCurveTo(prev.x, prev.y, (prev.x + p.x) / 2, (prev.y + p.y) / 2);
  }
  ctx.stroke();
  ctx.setLineDash([]);
}

function draw() {
  ctx.clearRect(0, 0, W(), H());
  const BASE_COLORS = [COLORS.A, COLORS.T, COLORS.C, COLORS.G];
  const BASE_COLORS2 = [COLORS.C, COLORS.G, COLORS.A, COLORS.T];

  for (let i = 0; i < N; i++) {
    const p1 = pt(i, 0, t);
    const p2 = pt(i, Math.PI, t);
    ctx.beginPath(); ctx.moveTo(p1.x, p1.y); ctx.lineTo(p2.x, p2.y);
    ctx.strokeStyle = COLORS.rung; ctx.lineWidth = 1; ctx.stroke();

    const lx = p1.x + (p2.x - p1.x) * 0.35;
    const ly = p1.y + (p2.y - p1.y) * 0.35;
    const rx = p1.x + (p2.x - p1.x) * 0.65;
    const ry = p1.y + (p2.y - p1.y) * 0.65;
    ctx.beginPath(); ctx.arc(lx, ly, 3.5, 0, Math.PI * 2); ctx.fillStyle = BASE_COLORS[i % 4] + 'aa'; ctx.fill();
    ctx.beginPath(); ctx.arc(rx, ry, 3.5, 0, Math.PI * 2); ctx.fillStyle = BASE_COLORS2[i % 4] + 'aa'; ctx.fill();
  }

  drawStrand(0, COLORS.strand1);
  drawStrand(Math.PI, COLORS.strand2, [5, 4]);

  for (let i = 0; i < N; i += 2) {
    const p1 = pt(i, 0, t);
    const p2 = pt(i, Math.PI, t);
    const r1 = Math.max(1.5, 3.5 + p1.z * 2.5);
    const r2 = Math.max(1.5, 3.5 - p1.z * 2.5);
    ctx.beginPath(); ctx.arc(p1.x, p1.y, r1, 0, Math.PI * 2); ctx.fillStyle = COLORS.strand1; ctx.fill();
    ctx.beginPath(); ctx.arc(p2.x, p2.y, r2, 0, Math.PI * 2); ctx.fillStyle = COLORS.strand2; ctx.fill();

    if (p1.z > 0.5 && i % 8 === 0) {
      ctx.font = '500 11px monospace';
      ctx.fillStyle = BASE_COLORS[i % 4];
      ctx.fillText(BASES[i % 4], p1.x + 9, p1.y + 4);
    }
  }

  const totalH = N * STEP_Y;
  const startY = (H() - totalH) / 2;
  const fade = 64;
  const gT = ctx.createLinearGradient(0, startY, 0, startY + fade);
  gT.addColorStop(0, COLORS.fade + '1)'); gT.addColorStop(1, COLORS.fade + '0)');
  ctx.fillStyle = gT; ctx.fillRect(0, 0, W(), startY + fade);

  const gB = ctx.createLinearGradient(0, startY + totalH - fade, 0, startY + totalH);
  gB.addColorStop(0, COLORS.fade + '0)'); gB.addColorStop(1, COLORS.fade + '1)');
  ctx.fillStyle = gB; ctx.fillRect(0, startY + totalH - fade, W(), H());

  t += 0.009;
  requestAnimationFrame(draw);
}
draw();
</script>
"""


st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;0,400;0,600;1,300;1,400&family=Outfit:wght@200;300;400;500;600&family=JetBrains+Mono:wght@300;400;500&display=swap');

:root {
  --ink:#0b1220; --ink2:#1a2640; --mid:#2e4a6e; --slate:#4a6a8e; --mist:#a8bdd4;
  --pearl:#e8f0f7; --white:#f5f8fc; --accent:#c8a96e; --accent2:#e2c98a; --rose:#b07b8c;
  --bg:#f0f4f8; --surface:#ffffff; --border:rgba(11,18,32,0.08); --border2:rgba(11,18,32,0.05);
}
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
html { scroll-behavior: smooth; }
body, .stApp { background: var(--bg); color: var(--ink); font-family: 'Outfit', sans-serif; font-weight: 300; overflow-x: hidden; }
header, [data-testid='stToolbar'], [data-testid='stDecoration'], #MainMenu { display:none !important; }
section.main > div { padding-top: 0 !important; }

::-webkit-scrollbar { width: 4px; }
::-webkit-scrollbar-track { background: var(--bg); }
::-webkit-scrollbar-thumb { background: var(--accent); border-radius: 2px; }

.container { max-width: 1200px; margin: 0 auto; padding: 0 48px; }
section { padding: 120px 0; }

nav {
  position: fixed; top: 0; left: 0; right: 0; z-index: 100;
  background: rgba(240,244,248,0.85); backdrop-filter: blur(24px);
  border-bottom: 1px solid var(--border); height: 64px; display: flex; align-items: center;
}
.nav-inner { max-width: 1200px; margin: 0 auto; padding: 0 48px; width: 100%; display: flex; align-items: center; justify-content: space-between; }
.nav-logo { display: flex; align-items: baseline; gap: 3px; text-decoration: none; }
.nav-logo-primary { font-family: 'Cormorant Garamond', serif; font-size: 22px; font-weight: 600; font-style: italic; color: var(--ink); }
.nav-logo-secondary { font-family: 'JetBrains Mono', monospace; font-size: 9px; color: var(--accent); letter-spacing: 0.2em; text-transform: uppercase; margin-left: 4px; }
.nav-links { display: flex; align-items: center; gap: 36px; list-style: none; }
.nav-links a { color: var(--slate); text-decoration: none; font-size: 13px; }
.nav-links a:hover { color: var(--ink); }
.nav-cta { background: var(--ink); color: var(--white) !important; padding: 8px 22px; border-radius: 2px; font-size: 12px !important; letter-spacing: 0.08em; text-transform: uppercase; }
.nav-cta:hover { background: var(--ink2); }

.hero {
  min-height: 100vh; display:flex; align-items:center; padding:100px 0 60px; position:relative; overflow:hidden;
  background: linear-gradient(145deg, #e8eef5 0%, #f0f4f8 40%, #edf2f7 100%);
}
.hero::before {
  content:''; position:absolute; inset:0;
  background-image: linear-gradient(rgba(11,18,32,0.025) 1px, transparent 1px), linear-gradient(90deg, rgba(11,18,32,0.025) 1px, transparent 1px);
  background-size: 60px 60px;
}
#helix-canvas { position:absolute; right:30px; top:50%; transform:translateY(-50%); width:520px; height:620px; opacity:0.95; z-index:1; pointer-events:none; }
#helix-canvas svg { width: 100%; height: 100%; }
#helix-canvas img { width: 100%; height: 100%; object-fit: contain; opacity: 0.92; }
.helix-component-wrap { max-width: 1200px; margin: -640px auto 120px auto; padding: 0 48px; position: relative; z-index: 4; pointer-events: none; }
.helix-component-wrap > div { width: 560px; margin-left: auto; border: none !important; }
.hero-mobile-dna { display:none; margin: 24px 0 8px; padding: 10px; border: 1px solid var(--border); border-radius: 4px; background: rgba(255,255,255,0.6); }
.hero-mobile-dna svg { width: 100%; max-height: 320px; }
.hero-mobile-dna img { width: 100%; max-height: 320px; object-fit: contain; }
.hero-content { position: relative; z-index: 2; max-width: 580px; }
.hero-grid { position: relative; z-index: 2; display: grid; grid-template-columns: 1.05fr 0.95fr; gap: 36px; align-items: center; }
.hero-visual { display: flex; justify-content: flex-end; }
.hero-visual-card { width: 100%; max-width: 420px; border: 1px solid var(--border); border-radius: 4px; background: rgba(255,255,255,0.72); padding: 12px; }
.hero-visual-card svg { width: 100%; height: auto; max-height: 470px; display: block; }
.design-ref-banner { background: rgba(200,169,110,0.08); border: 1px solid rgba(200,169,110,0.25); border-radius: 4px; padding: 14px 24px; margin-bottom: 72px; font-family: 'JetBrains Mono', monospace; font-size: 10px; color: var(--slate); }
.hero-eyebrow { display:flex; align-items:center; gap:12px; margin-bottom:32px; }
.eyebrow-line { width:32px; height:1px; background: var(--accent); }
.eyebrow-text { font-family:'JetBrains Mono', monospace; font-size:10px; color:var(--accent); letter-spacing:0.18em; text-transform:uppercase; }
.hero-title { font-family:'Cormorant Garamond', serif; font-size: clamp(52px, 6vw, 84px); font-weight: 300; line-height:1.05; margin-bottom:8px; }
.hero-subtitle { font-family:'Cormorant Garamond', serif; font-size: clamp(28px, 3vw, 38px); font-weight:300; font-style:italic; color:var(--slate); margin-bottom:36px; }
.hero-desc { font-size:15px; color:var(--slate); line-height:1.8; max-width: 480px; margin-bottom:48px; }
.hero-desc strong { color: var(--ink); font-weight: 500; }
.hero-actions { display:flex; align-items:center; gap:20px; }
.btn-primary { background: var(--ink); color: var(--white) !important; padding: 14px 32px; border-radius: 2px; text-decoration:none; font-size:12px; letter-spacing:0.12em; text-transform:uppercase; }
.btn-ghost { background: transparent; color: var(--slate) !important; padding: 13px 24px; border:1px solid var(--border); border-radius:2px; text-decoration:none; font-family:'JetBrains Mono', monospace; font-size:11px; }
.hero-chips { display:flex; gap:16px; margin-top:56px; padding-top:40px; border-top:1px solid var(--border); }
.chip { flex:1; }
.chip-val { font-family:'Cormorant Garamond', serif; font-size:32px; font-weight:600; }
.chip-val span { font-size:18px; font-weight:300; color:var(--accent); }
.chip-lbl { font-family:'JetBrains Mono', monospace; font-size:9px; color:var(--mist); letter-spacing:0.14em; text-transform:uppercase; margin-top:5px; }
.hero-annotation { position:absolute; z-index:3; background:rgba(255,255,255,0.92); border:1px solid var(--border); border-radius:4px; padding:14px 18px; box-shadow:0 8px 32px rgba(11,18,32,0.08); }
.annotation-1 { right:400px; top:28%; }
.annotation-2 { right:80px; bottom:32%; }
.ann-label { font-family:'JetBrains Mono', monospace; font-size:9px; color:var(--accent); letter-spacing:0.16em; text-transform:uppercase; margin-bottom:4px; }
.ann-title { font-size:13px; font-weight:500; }
.ann-desc { font-size:11px; color:var(--slate); margin-top:2px; max-width:200px; line-height:1.5; }

.marquee-section { background: var(--ink); padding: 20px 0; overflow: hidden; }
.marquee-track { display:flex; gap:64px; animation: marquee 28s linear infinite; width:max-content; }
.marquee-item { font-family:'JetBrains Mono', monospace; font-size:11px; color:rgba(255,255,255,0.25); letter-spacing:0.15em; text-transform:uppercase; white-space:nowrap; }
.marquee-item::before { content:''; display:block; width:4px; height:4px; background:var(--accent); border-radius:50%; margin-right: 12px; }
@keyframes marquee { from { transform: translateX(0);} to { transform: translateX(-50%);} }

.section-eyebrow { display:flex; align-items:center; gap:12px; margin-bottom:20px; }
.section-eyebrow .line { width:24px; height:1px; background:var(--accent); }
.section-eyebrow .text { font-family:'JetBrains Mono', monospace; font-size:9px; color:var(--accent); letter-spacing:0.2em; text-transform:uppercase; }
.section-title { font-family:'Cormorant Garamond', serif; font-size: clamp(36px, 4vw, 56px); font-weight:300; line-height:1.1; }
.section-title em { color: var(--mid); font-style: italic; }
.section-desc { font-size:15px; color:var(--slate); line-height:1.8; }

.pipeline-section, .match-section { background: var(--ink); }
.pipeline-section .section-title, .match-section .section-title { color:var(--pearl); }
.pipeline-section .section-title em, .match-section .section-title em { color:var(--accent2); }
.pipeline-section .section-desc, .match-section .section-desc { color:var(--mist); }
.pipeline-header { display:grid; grid-template-columns:1fr 1fr; gap:64px; align-items:center; margin-bottom:80px; }
.pipeline-steps { display:grid; grid-template-columns: repeat(5, 1fr); position:relative; }
.pipeline-steps::before { content:''; position:absolute; top:28px; left:28px; right:28px; height:1px; background:linear-gradient(90deg, var(--accent2), rgba(200,169,110,0.2), transparent); }
.p-step { padding: 0 12px; }
.p-step-num { width:56px; height:56px; border:1px solid rgba(200,169,110,0.3); border-radius:50%; display:flex; align-items:center; justify-content:center; margin-bottom:20px; background:var(--ink); color:var(--accent2); font-family:'Cormorant Garamond', serif; font-size:20px; }
.p-step-title { color:var(--pearl); font-size:13px; font-weight:500; margin-bottom:6px; }
.p-step-desc { color:var(--mist); font-size:12px; line-height:1.65; }

.features-grid, .deliv-grid { display:grid; grid-template-columns:repeat(3, 1fr); gap:1px; background:var(--border); border:1px solid var(--border); margin-top:64px; }
.feat-card, .deliv-card { background:var(--white); padding:40px 36px; }
.feat-num, .deliv-num { font-family:'Cormorant Garamond', serif; font-size:48px; color:rgba(11,18,32,0.06); margin-bottom:20px; }
.deliv-num { font-size:64px; }
.feat-title, .deliv-title { font-size:16px; font-weight:500; margin-bottom:12px; }
.feat-desc, .deliv-desc { font-size:13px; color:var(--slate); line-height:1.75; }
.feat-tag, .deliv-tag { display:inline-block; margin-top:20px; font-family:'JetBrains Mono', monospace; font-size:9px; color:var(--accent); letter-spacing:0.14em; text-transform:uppercase; border-bottom:1px solid rgba(200,169,110,0.3); padding-bottom:2px; }

.control-panel { margin: 0 auto 40px; max-width:1200px; padding: 0 48px; }
.control-box { background: var(--white); border: 1px solid var(--border); border-radius: 4px; padding: 24px; box-shadow: 0 20px 60px rgba(11,18,32,0.08); }
.control-title { font-family:'Cormorant Garamond', serif; font-size:34px; margin-bottom:8px; }
.control-sub { color: var(--slate); font-size:13px; margin-bottom: 16px; }

.stTextInput input, .stTextArea textarea {
  background: #fff !important; border:1px solid var(--border) !important; border-radius:2px !important; font-family:'JetBrains Mono', monospace !important; font-size:12px !important;
}
.stFileUploader section { background: #fff; border:1px dashed var(--border) !important; border-radius:2px; }
.stButton > button { background: var(--ink) !important; color: var(--white) !important; border:none !important; border-radius:2px !important; font-size:11px !important; letter-spacing:0.08em !important; text-transform:uppercase !important; }

.status-ok, .status-err { margin-top: 12px; padding: 12px 14px; border-radius: 2px; font-family:'JetBrains Mono', monospace; font-size:10px; letter-spacing:0.04em; }
.status-ok { background: rgba(109,201,142,0.1); border: 1px solid rgba(109,201,142,0.4); color:#3f8258; }
.status-err { background: rgba(240,128,128,0.1); border: 1px solid rgba(240,128,128,0.45); color:#8b4f4f; }

.dfa-section { background: var(--bg); }
.dfa-grid, .match-grid, .desktop-grid { display:grid; grid-template-columns:1fr 1fr; gap:80px; align-items:center; }
.dfa-visual-wrap, .match-vis { background: var(--white); border:1px solid var(--border); border-radius:4px; overflow:hidden; box-shadow:0 20px 60px rgba(11,18,32,0.08); }
.match-vis { background: rgba(255,255,255,0.04); border-color: rgba(255,255,255,0.08); box-shadow:none; }
.dfa-visual-header, .match-vis-header { background: var(--ink); padding:14px 24px; display:flex; align-items:center; justify-content:space-between; }
.dfa-header-label, .mh-label { font-family:'JetBrains Mono', monospace; font-size:10px; color:rgba(255,255,255,0.4); letter-spacing:0.1em; text-transform:uppercase; }
.dfa-header-badge { font-family:'JetBrains Mono', monospace; font-size:9px; color:var(--accent2); border:1px solid rgba(200,169,110,0.3); border-radius:2px; padding:3px 10px; }
.mh-live { font-family:'JetBrains Mono', monospace; font-size:9px; color:#6dc98e; letter-spacing:0.1em; text-transform:uppercase; }
.dfa-visual-body { padding: 32px; }
.dfa-diagram { background: var(--bg); border-radius:4px; padding:24px; margin-bottom:24px; }
.dfa-table { width:100%; border-collapse:collapse; font-family:'JetBrains Mono', monospace; font-size:11px; }
.dfa-table th { background:var(--bg); padding:9px 14px; border:1px solid var(--border2); color:var(--mist); font-size:10px; }
.dfa-table td { padding:9px 14px; border:1px solid var(--border2); text-align:center; color:var(--slate); }
.dfa-table .state-name { color:var(--ink); font-weight:500; }
.dfa-table .accept { color:var(--accent); font-weight:500; }

.complexity-row, .match-stats-grid { display:grid; grid-template-columns:1fr 1fr; gap:16px; margin:36px 0; }
.c-card, .ms-card { background: var(--white); border:1px solid var(--border); padding:22px 24px; border-radius:4px; }
.ms-card { background: rgba(255,255,255,0.04); border:1px solid rgba(255,255,255,0.08); }
.c-val, .ms-val { font-family:'Cormorant Garamond', serif; font-size:32px; font-weight:600; line-height:1; }
.ms-val { color: var(--pearl); }
.c-key, .ms-lbl { font-family:'JetBrains Mono', monospace; font-size:9px; color:var(--mist); letter-spacing:0.14em; text-transform:uppercase; margin-top:6px; }
.ms-lbl { color: rgba(255,255,255,0.25); }

.base-legend { display:flex; gap:20px; flex-wrap:wrap; padding:18px 22px; background:var(--white); border:1px solid var(--border); border-radius:4px; }
.bl-item { display:flex; align-items:center; gap:10px; }
.bl-dot { width:8px; height:8px; border-radius:50%; }
.bl-base { font-family:'Cormorant Garamond', serif; font-size:16px; font-weight:600; }
.bl-name { font-size:11px; color:var(--mist); }

.libs-section { background: var(--white); border-top:1px solid var(--border); }
.libs-header { display:grid; grid-template-columns:1fr 1fr; gap:64px; align-items:center; margin-bottom:64px; }
.libs-grid { display:grid; grid-template-columns:repeat(3, 1fr); gap:24px; }
.lib-card { background: var(--bg); border:1px solid var(--border); border-radius:4px; padding:36px 32px; }
.lib-name { font-family:'Cormorant Garamond', serif; font-size:24px; font-weight:600; margin-bottom:4px; }
.lib-install { font-family:'JetBrains Mono', monospace; font-size:10px; color:var(--mist); margin-bottom:18px; background:var(--white); border:1px solid var(--border); border-radius:2px; padding:5px 10px; display:inline-block; }
.lib-desc { font-size:13px; color:var(--slate); line-height:1.75; margin-bottom:22px; }
.lib-tag { font-family:'JetBrains Mono', monospace; font-size:9px; letter-spacing:0.14em; text-transform:uppercase; border-bottom:1px solid; padding-bottom:2px; }
.lib-tag.bio { color:#7b8fcf; border-color: rgba(123,143,207,0.4); }
.lib-tag.viz { color:var(--rose); border-color: rgba(176,123,140,0.4); }
.lib-tag.plot { color:var(--accent); border-color: rgba(200,169,110,0.4); }

.genome-display { padding:24px; font-family:'JetBrains Mono', monospace; font-size:11px; line-height:2.2; letter-spacing:0.12em; word-break:break-all; border-bottom:1px solid rgba(255,255,255,0.06); color: rgba(255,255,255,0.35); }
.b-a { color:#c9a6ff; } .b-t { color:#f5c842; } .b-c { color:#7bcfb5; } .b-g { color:#f08080; }
.b-match { background: rgba(200,169,110,0.2); border-bottom:1px solid var(--accent2); }
.b-match.b-a { color: #e2c9ff; }
.b-match.b-t { color: var(--accent2); }
.b-match.b-c { color: #a0e4d0; }
.b-match.b-g { color: #f8b0b0; }
.match-chart-wrap { padding:24px; }
.mc-title { font-family:'JetBrains Mono', monospace; font-size:9px; color:rgba(255,255,255,0.25); letter-spacing:0.14em; text-transform:uppercase; margin-bottom:18px; }
.bar-chart { display:flex; align-items:flex-end; gap:4px; height:72px; }
.bar { flex:1; border-radius:2px 2px 0 0; background: rgba(200,169,110,0.12); border-top:1px solid rgba(200,169,110,0.25); }
.bar.hi { background: rgba(200,169,110,0.3); border-color: var(--accent2); }
.match-positions { padding:16px 24px; display:flex; flex-wrap:wrap; gap:8px; border-top:1px solid rgba(255,255,255,0.06); }
.pos-tag { font-family:'JetBrains Mono', monospace; font-size:10px; color:var(--accent2); border:1px solid rgba(200,169,110,0.2); background:rgba(200,169,110,0.05); border-radius:2px; padding:4px 10px; }

.desktop-section, .team-section { background: var(--bg); border-top:1px solid var(--border); }
.desktop-mockup { background:#1a1a1e; border-radius:8px; overflow:hidden; border:1px solid rgba(255,255,255,0.08); box-shadow:0 40px 80px rgba(11,18,32,0.2); }
.dm-titlebar { background:#2a2a2e; padding:12px 16px; display:flex; align-items:center; gap:7px; }
.dm-dot { width:11px; height:11px; border-radius:50%; }
.dm-dot.r { background:#ff5f57; } .dm-dot.y { background:#febc2e; } .dm-dot.g { background:#28c840; }
.dm-title { flex:1; text-align:center; font-family:'JetBrains Mono', monospace; font-size:10px; color:#555; }
.dm-body { display:grid; grid-template-columns:180px 1fr; min-height:320px; }
.dm-sidebar { background:#141418; padding:16px 0; border-right:1px solid rgba(255,255,255,0.05); }
.dm-sidebar-label { font-family:'JetBrains Mono', monospace; font-size:8px; color:#3a3a4a; letter-spacing:0.18em; text-transform:uppercase; padding:10px 16px 4px; }
.dm-sidebar-item { padding:9px 16px; font-size:12px; color:#555; border-left:2px solid transparent; }
.dm-sidebar-item.active { color:#c8a96e; border-left-color:#c8a96e; background: rgba(200,169,110,0.05); }
.dm-main { padding:18px; }
.dm-console { background:#0d0d11; border:1px solid rgba(255,255,255,0.05); border-radius:4px; padding:14px; font-family:'JetBrains Mono', monospace; font-size:10px; line-height:1.9; color:#777; }

.team-inner { text-align:center; max-width:640px; margin:0 auto; }
.team-cards { display:grid; grid-template-columns:1fr 1fr; gap:20px; margin-top:48px; }
.team-card { background: var(--white); border:1px solid var(--border); border-radius:4px; padding:40px 32px; }
.team-initials { width:64px; height:64px; border-radius:50%; background:var(--ink); border:2px solid rgba(200,169,110,0.3); display:flex; align-items:center; justify-content:center; margin:0 auto 20px; font-family:'Cormorant Garamond', serif; font-size:22px; font-weight:600; color:var(--accent2); }
.team-name { font-family:'Cormorant Garamond', serif; font-size:22px; font-weight:600; }
.team-id { font-family:'JetBrains Mono', monospace; font-size:10px; color:var(--mist); }
.team-dept { font-size:12px; color:var(--accent); margin-top:12px; }

footer { background: var(--ink); padding:48px 0; }
.footer-inner { max-width:1200px; margin:0 auto; padding:0 48px; display:flex; align-items:center; justify-content:space-between; }
.footer-logo-text { font-family:'Cormorant Garamond', serif; font-size:20px; font-weight:600; color:var(--pearl); }
.footer-links { display:flex; gap:32px; }
.footer-links a { font-family:'JetBrains Mono', monospace; font-size:10px; color:rgba(255,255,255,0.3); text-decoration:none; letter-spacing:0.1em; }
.footer-copy { font-family:'JetBrains Mono', monospace; font-size:10px; color:rgba(255,255,255,0.2); letter-spacing:0.08em; }

@keyframes fadeUp {
  from { opacity: 0; transform: translateY(28px); }
  to { opacity: 1; transform: translateY(0); }
}
.fu { animation: fadeUp 0.8s cubic-bezier(0.22,1,0.36,1) both; }
.fu-1 { animation-delay: 0.05s; }
.fu-2 { animation-delay: 0.15s; }
.fu-3 { animation-delay: 0.28s; }
.fu-4 { animation-delay: 0.44s; }

@media (max-width: 1100px) {
  .container, .control-panel { padding:0 20px; }
  .nav-inner { padding:0 20px; }
  .nav-links { gap: 12px; }
  .hero-annotation, #helix-canvas { display:none; }
  .hero-grid { grid-template-columns: 1fr; gap: 20px; }
  .hero-visual { justify-content: flex-start; }
  .hero-visual-card { max-width: 320px; }
  .helix-component-wrap { margin: 8px auto 16px auto; padding: 0 20px; }
  .helix-component-wrap > div { width: 100%; }
  .hero-mobile-dna { display:block; }
  .pipeline-header, .dfa-grid, .match-grid, .desktop-grid, .libs-header { grid-template-columns:1fr; gap:28px; }
  .pipeline-steps { grid-template-columns:1fr 1fr; }
  .features-grid, .deliv-grid, .libs-grid, .team-cards { grid-template-columns:1fr; }
}
</style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
<nav>
  <div class="nav-inner">
    <a href="#" class="nav-logo"><span class="nav-logo-primary">GeneFlow</span><span class="nav-logo-secondary">v2.0</span></a>
    <ul class="nav-links">
      <li><a href="#pipeline">Pipeline</a></li>
      <li><a href="#dfa">DFA Viewer</a></li>
      <li><a href="#matcher">Matcher</a></li>
      <li><a href="#desktop">Desktop App</a></li>
      <li><a href="#team">Team</a></li>
      <li><a href="#controls" class="nav-cta">Run Analysis</a></li>
    </ul>
  </div>
</nav>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    dedent(f"""
<section class="hero" id="home">
  <div class="container">
    <div class="hero-grid">
      <div class="hero-content">
        <div class="design-ref-banner"><strong>DESIGN REFERENCE</strong> - UI mapped section-by-section from geneflow_v2.html.</div>
        <div class="hero-eyebrow fu fu-1"><div class="eyebrow-line"></div><span class="eyebrow-text">TAFL Project - NUST SEECS - 2026</span></div>
        <h1 class="hero-title fu fu-2">DNA Pattern</h1>
        <p class="hero-subtitle fu fu-2">via Finite Automata</p>
        <p class="hero-desc fu fu-3">A <strong>deterministic finite automaton</strong> that reads FASTA genome sequences in a single O(n) pass, auto-generates state transitions, and charts every match position.</p>
        <div class="hero-actions fu fu-4"><a class="btn-primary" href="#pipeline">View Pipeline</a><a class="btn-ghost" href="#dfa">Explore the DFA</a></div>
        <div class="hero-chips fu fu-4">
          <div class="chip"><div class="chip-val">O<span>(n)</span></div><div class="chip-lbl">Time Complexity</div></div>
          <div class="chip"><div class="chip-val">4</div><div class="chip-lbl">Alphabet Sigma</div></div>
          <div class="chip"><div class="chip-val">3</div><div class="chip-lbl">Libraries</div></div>
          <div class="chip"><div class="chip-val">Real</div><div class="chip-lbl">FASTA Genome</div></div>
        </div>
      </div>

      <div class="hero-visual fu fu-3">
        <div class="hero-visual-card">
          {st.session_state.hero_svg}
        </div>
      </div>
    </div>
  </div>
</section>

<div class="marquee-section"><div class="marquee-track">
  <span class="marquee-item">Hopcroft Motwani Ullman 2006</span>
  <span class="marquee-item">Knuth Morris Pratt 1977</span>
  <span class="marquee-item">Aho Corasick 1975</span>
  <span class="marquee-item">NCBI BLAST 1990</span>
  <span class="marquee-item">BioPython FASTA Format</span>
  <span class="marquee-item">Graphviz State Diagrams</span>
  <span class="marquee-item">Sipser 2012 Formal Languages</span>
  <span class="marquee-item">Gusfield 1997 Algorithms on Strings</span>
  <span class="marquee-item">DFA O(n) Single Pass</span>
  <span class="marquee-item">Hopcroft Motwani Ullman 2006</span>
  <span class="marquee-item">Knuth Morris Pratt 1977</span>
  <span class="marquee-item">Aho Corasick 1975</span>
</div></div>

<section class="pipeline-section" id="pipeline">
  <div class="container">
    <div class="pipeline-header">
      <div><div class="section-eyebrow"><div class="line"></div><span class="text">Methodology</span></div><h2 class="section-title">Step-by-Step<br><em>Implementation</em></h2></div>
      <p class="section-desc">Every analysis follows the same five-stage pipeline from raw genome input to match position visualization.</p>
    </div>
    <div class="pipeline-steps">
      <div class="p-step"><div class="p-step-num">01</div><div class="p-step-title">Input Encoding</div><div class="p-step-desc">Define Sigma = {{A,T,C,G}} and validate pattern/genome.</div></div>
      <div class="p-step"><div class="p-step-num">02</div><div class="p-step-title">Build DFA</div><div class="p-step-desc">Construct delta(q,a) for all states and symbols.</div></div>
      <div class="p-step"><div class="p-step-num">03</div><div class="p-step-title">Run Matcher</div><div class="p-step-desc">Scan text and record each accept-state hit.</div></div>
      <div class="p-step"><div class="p-step-num">04</div><div class="p-step-title">Load FASTA</div><div class="p-step-desc">Parse authentic FASTA genome data with BioPython.</div></div>
      <div class="p-step"><div class="p-step-num">05</div><div class="p-step-title">Visualize</div><div class="p-step-desc">Render transition table and position histogram.</div></div>
    </div>
  </div>
</section>

<section class="features-section" id="features">
  <div class="container">
    <div class="section-eyebrow"><div class="line"></div><span class="text">Key Features</span></div>
    <h2 class="section-title">What Makes Our<br><em>Implementation Unique</em></h2>
    <div class="features-grid">
      <div class="feat-card"><div class="feat-num">01</div><div class="feat-title">Real Genomic Data</div><div class="feat-desc">Loads authentic FASTA data used in bioinformatics workflows.</div><span class="feat-tag">BioPython - FASTA</span></div>
      <div class="feat-card"><div class="feat-num">02</div><div class="feat-title">Auto-Generated DFA</div><div class="feat-desc">Transition table is computed directly from the pattern.</div><span class="feat-tag">Graphviz - SVG / PNG</span></div>
      <div class="feat-card"><div class="feat-num">03</div><div class="feat-title">Annotated Match Plot</div><div class="feat-desc">Match positions are visualized with distribution bars.</div><span class="feat-tag">Matplotlib - Plotly</span></div>
      <div class="feat-card"><div class="feat-num">04</div><div class="feat-title">O(n) Single Pass</div><div class="feat-desc">Deterministic scanning with no backtracking.</div><span class="feat-tag">O(n) - No Backtracking</span></div>
      <div class="feat-card"><div class="feat-num">05</div><div class="feat-title">Modular Python</div><div class="feat-desc">Reusable matcher and DFA modules with clear interfaces.</div><span class="feat-tag">GitHub - Documented</span></div>
      <div class="feat-card"><div class="feat-num">06</div><div class="feat-title">BLAST Foundation</div><div class="feat-desc">Grounded in formal language theory and practical genomics.</div><span class="feat-tag">NCBI BLAST - Theory</span></div>
    </div>
  </div>
</section>
    """),
    unsafe_allow_html=True,
)


st.markdown('<div id="controls" class="control-panel"><div class="control-box"><div class="control-title">Run Live Analysis</div><div class="control-sub">Enter pattern and genome, or upload FASTA, then run the DFA scan.</div>', unsafe_allow_html=True)

col_a, col_b = st.columns([1, 1], gap="large")
with col_a:
    input_pattern = st.text_input("Pattern", value=st.session_state.pattern, help="A/T/C/G only")
with col_b:
    uploaded_fasta = st.file_uploader("Upload FASTA (.fa/.fasta)", type=["fa", "fasta"])

st.session_state.pattern = clean_dna(input_pattern)
st.session_state.genome = clean_dna(
    st.text_area("Genome Sequence", value=st.session_state.genome, height=180, help="Paste sequence or load FASTA")
)

b1, b2, b3 = st.columns(3)
with b1:
    run_clicked = st.button("Run Analysis", use_container_width=True)
with b2:
    load_clicked = st.button("Load FASTA", use_container_width=True)
with b3:
    clear_clicked = st.button("Clear", use_container_width=True)

status_kind = ""
if load_clicked:
    try:
        st.session_state.genome = parse_uploaded_fasta(uploaded_fasta)
        st.session_state.status = f"Loaded FASTA: {len(st.session_state.genome)} bases"
        status_kind = "ok"
    except Exception as exc:  # pragma: no cover
        st.session_state.status = f"FASTA error: {exc}"
        status_kind = "err"

if clear_clicked:
    st.session_state.pattern = ""
    st.session_state.genome = ""
    st.session_state.matches = []
    st.session_state.dfa = {}
    st.session_state.accept_state = 0
    st.session_state.status = "Cleared all inputs and results"
    status_kind = "ok"

if run_clicked:
    try:
        if not st.session_state.pattern:
            raise ValueError("Pattern must contain A/T/C/G")
        if not st.session_state.genome:
            raise ValueError("Genome must contain A/T/C/G")
        dfa, accept, matches = run_analysis(st.session_state.pattern, st.session_state.genome)
        st.session_state.dfa = dfa
        st.session_state.accept_state = accept
        st.session_state.matches = matches
        st.session_state.status = f"Analysis complete: {len(matches)} matches found"
        status_kind = "ok"
    except Exception as exc:  # pragma: no cover
        st.session_state.status = f"Analysis error: {exc}"
        status_kind = "err"

if st.session_state.status:
    klass = "status-ok" if status_kind != "err" else "status-err"
    st.markdown(f'<div class="{klass}">{html.escape(st.session_state.status)}</div>', unsafe_allow_html=True)

st.markdown("</div></div>", unsafe_allow_html=True)

pattern = st.session_state.pattern or "ATCG"
if st.session_state.dfa:
    dfa = st.session_state.dfa
    accept_state = st.session_state.accept_state
else:
    dfa, accept_state = get_transition_table(pattern)

matches = st.session_state.matches
genome = st.session_state.genome
match_density = (len(matches) / len(genome) * 100) if genome else 0.0
match_tags = "".join(f'<span class="pos-tag">pos {m}</span>' for m in matches[:24]) or '<span class="pos-tag">No matches</span>'

st.markdown(
    dedent(f"""
<section class="dfa-section" id="dfa">
  <div class="container">
    <div class="dfa-grid">
      <div>
        <div class="dfa-visual-wrap">
          <div class="dfa-visual-header"><span class="dfa-header-label">Transition Diagram - Pattern: \"{html.escape(pattern)}\"</span><span class="dfa-header-badge">Graphviz Output</span></div>
          <div class="dfa-visual-body">
            <div class="dfa-diagram">
              <svg viewBox="0 0 480 130" xmlns="http://www.w3.org/2000/svg">
                <defs><marker id="arr" markerWidth="7" markerHeight="7" refX="5" refY="2.5" orient="auto"><path d="M0,0 L0,5 L7,2.5z" fill="rgba(74,106,142,0.6)"/></marker></defs>
                <line x1="18" y1="65" x2="44" y2="65" stroke="rgba(74,106,142,0.4)" stroke-width="1.5" marker-end="url(#arr)"/>
                <text x="8" y="55" fill="rgba(74,106,142,0.4)" font-family="JetBrains Mono,monospace" font-size="7">start</text>
                <circle cx="64" cy="65" r="20" fill="#f0f4f8" stroke="rgba(74,106,142,0.4)" stroke-width="1.2"/>
                <text x="64" y="69" fill="#2e4a6e" font-size="10" text-anchor="middle">q₀</text>
                <line x1="84" y1="65" x2="140" y2="65" stroke="#b07b8c" stroke-width="1.2" marker-end="url(#arr)"/>
                <text x="112" y="57" fill="#b07b8c" font-size="9" text-anchor="middle">A</text>
                <circle cx="160" cy="65" r="20" fill="#f0f4f8" stroke="rgba(74,106,142,0.4)" stroke-width="1.2"/>
                <text x="160" y="69" fill="#2e4a6e" font-size="10" text-anchor="middle">q₁</text>
                <line x1="180" y1="65" x2="236" y2="65" stroke="#c8a96e" stroke-width="1.2" marker-end="url(#arr)"/>
                <text x="208" y="57" fill="#c8a96e" font-size="9" text-anchor="middle">T</text>
                <circle cx="256" cy="65" r="20" fill="#f0f4f8" stroke="rgba(74,106,142,0.4)" stroke-width="1.2"/>
                <text x="256" y="69" fill="#2e4a6e" font-size="10" text-anchor="middle">q₂</text>
                <line x1="276" y1="65" x2="332" y2="65" stroke="#7bcfb5" stroke-width="1.2" marker-end="url(#arr)"/>
                <text x="304" y="57" fill="#7bcfb5" font-size="9" text-anchor="middle">C</text>
                <circle cx="352" cy="65" r="20" fill="#f0f4f8" stroke="rgba(74,106,142,0.4)" stroke-width="1.2"/>
                <text x="352" y="69" fill="#2e4a6e" font-size="10" text-anchor="middle">q₃</text>
                <line x1="372" y1="65" x2="428" y2="65" stroke="#c8a96e" stroke-width="2" marker-end="url(#arr)"/>
                <text x="400" y="57" fill="#c8a96e" font-size="9" text-anchor="middle">G</text>
                <circle cx="448" cy="65" r="20" fill="rgba(200,169,110,0.06)" stroke="#c8a96e" stroke-width="1.8"/>
                <circle cx="448" cy="65" r="15" fill="none" stroke="rgba(200,169,110,0.25)" stroke-width="1"/>
                <text x="448" y="69" fill="#c8a96e" font-size="10" text-anchor="middle">q₄</text>
                <path d="M52,46 Q64,20 76,46" fill="none" stroke="rgba(74,106,142,0.2)" stroke-width="1" marker-end="url(#arr)"/>
                <text x="64" y="14" fill="rgba(74,106,142,0.3)" font-size="7" text-anchor="middle">T,C,G</text>
                <text x="448" y="100" fill="#c8a96e" font-size="7" text-anchor="middle">ACCEPT</text>
              </svg>
            </div>
            <table class="dfa-table"><thead><tr><th>State</th><th style="color:#b07b8c">A</th><th style="color:#c8a96e">T</th><th style="color:#7bcfb5">C</th><th style="color:#f08080">G</th></tr></thead><tbody>{dfa_rows_html(dfa, accept_state)}</tbody></table>
          </div>
        </div>
      </div>

      <div>
        <div class="section-eyebrow"><div class="line"></div><span class="text">DFA Core</span></div>
        <h2 class="section-title" style="margin-bottom:20px;">Deterministic<br><em>Finite Automaton</em></h2>
        <p class="section-desc" style="margin-bottom:0;">For pattern length m, we build m+1 states and then scan genome length n in strict O(n) time with deterministic transitions over Sigma.</p>
        <div class="complexity-row">
          <div class="c-card"><div class="c-val">O(n)</div><div class="c-key">Scanning Time</div></div>
          <div class="c-card"><div class="c-val">O(m)</div><div class="c-key">Space - States</div></div>
          <div class="c-card"><div class="c-val">{len(dfa)}</div><div class="c-key">Total States</div></div>
          <div class="c-card"><div class="c-val">|Sigma| = 4</div><div class="c-key">Alphabet Size</div></div>
        </div>
        <div class="base-legend">
          <div class="bl-item"><div class="bl-dot" style="background:#b07b8c"></div><span class="bl-base" style="color:#b07b8c">A</span><span class="bl-name">Adenine</span></div>
          <div class="bl-item"><div class="bl-dot" style="background:#c8a96e"></div><span class="bl-base" style="color:#c8a96e">T</span><span class="bl-name">Thymine</span></div>
          <div class="bl-item"><div class="bl-dot" style="background:#7bcfb5"></div><span class="bl-base" style="color:#7bcfb5">C</span><span class="bl-name">Cytosine</span></div>
          <div class="bl-item"><div class="bl-dot" style="background:#f08080"></div><span class="bl-base" style="color:#f08080">G</span><span class="bl-name">Guanine</span></div>
        </div>
      </div>
    </div>
  </div>
</section>

<section class="libs-section" id="libs">
  <div class="container">
    <div class="libs-header">
      <div><div class="section-eyebrow"><div class="line"></div><span class="text">Tech Stack</span></div><h2 class="section-title">Three Libraries.<br><em>One Pipeline.</em></h2></div>
      <p class="section-desc">Each library has a clear role from FASTA parsing to transition visualization and match plotting.</p>
    </div>
    <div class="libs-grid">
      <div class="lib-card"><div class="lib-name">BioPython</div><div class="lib-install">pip install biopython</div><p class="lib-desc">Loads real FASTA-format genome sequences used by research workflows.</p><span class="lib-tag bio">Bioinformatics</span></div>
      <div class="lib-card"><div class="lib-name">Graphviz</div><div class="lib-install">pip install graphviz</div><p class="lib-desc">Used to render automata diagrams in desktop and support scripts.</p><span class="lib-tag viz">Visualization</span></div>
      <div class="lib-card"><div class="lib-name">Matplotlib</div><div class="lib-install">pip install matplotlib</div><p class="lib-desc">Standard plotting stack for match distribution and exported figures.</p><span class="lib-tag plot">Plotting</span></div>
    </div>
  </div>
</section>

<section class="match-section" id="matcher">
  <div class="container">
    <div class="section-eyebrow"><div class="line"></div><span class="text">Match Visualization</span></div>
    <h2 class="section-title">Every Match,<br><em>Instantly Visible</em></h2>
    <div class="match-grid" style="margin-top:64px;">
      <div class="match-vis">
        <div class="match-vis-header"><span class="mh-label">Genome Scan | P = \"{html.escape(pattern)}\"</span><span class="mh-live">Live</span></div>
        <div class="genome-display">{genome_html(genome, pattern, matches)}</div>
        <div class="match-chart-wrap"><div class="mc-title">Match Frequency - Position Distribution</div><div class="bar-chart">{bars_html(matches, len(genome))}</div></div>
        <div class="match-positions">{match_tags}</div>
      </div>
      <div>
        <p class="section-desc" style="color:var(--mist);">After the DFA scan, every position is surfaced as tags plus a compact distribution chart for quick interpretation.</p>
        <div class="match-stats-grid">
          <div class="ms-card"><div class="ms-val">{len(matches)}</div><div class="ms-lbl">Matches Found</div></div>
          <div class="ms-card"><div class="ms-val">{len(genome)}</div><div class="ms-lbl">Genome Length</div></div>
          <div class="ms-card"><div class="ms-val" style="color:var(--accent2);">{match_density:.2f}%</div><div class="ms-lbl">Match Density</div></div>
          <div class="ms-card"><div class="ms-val" style="color:#c9a6ff;">q{accept_state}</div><div class="ms-lbl">Accept State</div></div>
        </div>
      </div>
    </div>
  </div>
</section>

<section class="desktop-section" id="desktop">
  <div class="container">
    <div class="desktop-grid">
      <div>
        <div class="section-eyebrow"><div class="line"></div><span class="text">PyQt Desktop App</span></div>
        <h2 class="section-title" style="margin-bottom:24px;">Native<br><em>Desktop Interface</em></h2>
        <p class="section-desc" style="margin-bottom:40px;">The desktop app mirrors web functionality with native controls, FASTA file picker, and export workflow.</p>
      </div>
      <div class="desktop-mockup">
        <div class="dm-titlebar"><div class="dm-dot r"></div><div class="dm-dot y"></div><div class="dm-dot g"></div><div class="dm-title">GeneFlow Desktop - DNA Matcher</div></div>
        <div class="dm-body">
          <div class="dm-sidebar"><div class="dm-sidebar-label">Navigation</div><div class="dm-sidebar-item active">DFA Matcher</div><div class="dm-sidebar-item">FA Diagram</div><div class="dm-sidebar-item">Match Plot</div><div class="dm-sidebar-item">Load FASTA</div></div>
          <div class="dm-main"><div class="dm-console">[INFO] Loading FASTA\n[INFO] Genome loaded\n[DFA] Building transitions\n[SCAN] Running O(n) scan\n[DONE] Analysis complete</div></div>
        </div>
      </div>
    </div>
  </div>
</section>

<section class="deliv-section" id="deliverables">
  <div class="container">
    <div class="section-eyebrow"><div class="line"></div><span class="text">Deliverables</span></div>
    <h2 class="section-title">What We Submit</h2>
    <div class="deliv-grid">
      <div class="deliv-card"><div class="deliv-num">01</div><div class="deliv-title">Python DFA Matcher</div><div class="deliv-desc">Core DFA matching implementation.</div><span class="deliv-tag">Core Algorithm</span></div>
      <div class="deliv-card"><div class="deliv-num">02</div><div class="deliv-title">Graphviz FA Diagram</div><div class="deliv-desc">State transition diagram output.</div><span class="deliv-tag">Graphviz</span></div>
      <div class="deliv-card"><div class="deliv-num">03</div><div class="deliv-title">Match Plot</div><div class="deliv-desc">Position distribution visualization.</div><span class="deliv-tag">Matplotlib</span></div>
      <div class="deliv-card"><div class="deliv-num">04</div><div class="deliv-title">Streamlit Web App</div><div class="deliv-desc">Interactive real-time web interface.</div><span class="deliv-tag">Streamlit</span></div>
      <div class="deliv-card"><div class="deliv-num">05</div><div class="deliv-title">PyQt Desktop App</div><div class="deliv-desc">Native desktop interface and exports.</div><span class="deliv-tag">PyQt6</span></div>
      <div class="deliv-card"><div class="deliv-num">06</div><div class="deliv-title">GitHub Repository</div><div class="deliv-desc">Documented source and usage guide.</div><span class="deliv-tag">GitHub</span></div>
    </div>
  </div>
</section>

<section class="team-section" id="team">
  <div class="container">
    <div class="team-inner">
      <div class="section-eyebrow" style="justify-content:center;"><div class="line"></div><span class="text">Project Team</span></div>
      <h2 class="section-title">Automata Theory<br><em>NUST SEECS - 2026</em></h2>
      <div class="team-cards">
        <div class="team-card"><div class="team-initials">ZS</div><div class="team-name">Zainab Saeed</div><div class="team-id">CMS 509170</div><div class="team-dept">Computer Science</div></div>
        <div class="team-card"><div class="team-initials">MU</div><div class="team-name">Maryam Ubaid</div><div class="team-id">CMS 511128</div><div class="team-dept">Computer Science</div></div>
      </div>
    </div>
  </div>
</section>

<footer>
  <div class="footer-inner">
    <div class="footer-logo-text">GeneFlow</div>
    <div class="footer-links"><a href="https://biopython.org/docs" target="_blank">BioPython Docs</a><a href="https://blast.ncbi.nlm.nih.gov" target="_blank">NCBI BLAST</a><a href="https://graphviz.org/documentation" target="_blank">Graphviz Docs</a></div>
    <div class="footer-copy">DNA String Matching - TAFL - 2026</div>
  </div>
</footer>
    """),
    unsafe_allow_html=True,
)
