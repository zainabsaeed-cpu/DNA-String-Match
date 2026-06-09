"""
GeneFlow — DNA String Matcher (Streamlit App)
A DFA-powered genome scanner that visualizes DNA pattern matching with real FASTA sequences.
"""

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
import os
from pathlib import Path
import time

try:
    from Bio import SeqIO
    HAS_BIO = True
except ImportError:
    HAS_BIO = False

from dfa import get_transition_table, ALPHABET
from matcher import find_matches, trace_dfa
from genome_loader import load_uploaded_genome

# ─────────────────────────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="GeneFlow — DNA String Matcher",
    page_icon="⬡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─────────────────────────────────────────────────────────────────
# DESIGN SYSTEM CSS
# ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:ital,wght@0,300;0,400;0,500;1,400&family=Syne:wght@400;600;700;800&family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,400;0,9..40,500;1,9..40,300&display=swap');

:root {
    --bg: #070b12;
    --bg2: #0c1220;
    --surface: #111827;
    --surface2: #162033;
    --border: rgba(99,210,190,0.12);
    --border2: rgba(99,210,190,0.06);
    --accent: #3fffd2;
    --accent2: #63d2be;
    --accent3: #8affea;
    --amber: #f5c842;
    --rose: #ff6b8a;
    --text: #e8f0ee;
    --text2: #8fa8a0;
    --text3: #4a6a62;
    --glow: 0 0 40px rgba(63,255,210,0.18);
    --glow-sm: 0 0 16px rgba(63,255,210,0.22);
}

* { box-sizing: border-box; margin: 0; padding: 0; }

html { scroll-behavior: smooth; }

body, .main {
    background: var(--bg);
    color: var(--text);
}

.stApp {
    background: var(--bg);
}

header { display: none; }
[data-testid="stDecoration"] { display: none; }
[data-testid="stToolbar"] { display: none; }

/* Typography */
h1, h2, h3, h4, h5, h6 {
    font-family: 'Syne', sans-serif !important;
    font-weight: 700 !important;
    letter-spacing: -0.02em;
}

p, span, div {
    font-family: 'DM Sans', sans-serif !important;
}

code, pre {
    font-family: 'DM Mono', monospace !important;
}

/* Scrollbar */
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: var(--bg); }
::-webkit-scrollbar-thumb { background: var(--accent3); border-radius: 3px; opacity: 0.4; }

/* Tabs */
.stTabs [data-baseweb="tab-list"] {
    background: transparent;
    border-bottom: 1px solid var(--border2);
    gap: 24px;
}

.stTabs [data-baseweb="tab-list"] button {
    font-family: 'DM Mono', monospace !important;
    font-size: 12px;
    letter-spacing: 0.06em;
    color: var(--text2);
    border-bottom: 2px solid transparent;
}

.stTabs [aria-selected="true"] {
    color: var(--accent) !important;
    border-bottom: 2px solid var(--accent) !important;
}

/* Input fields */
.stTextInput input, .stNumberInput input, .stTextArea textarea {
    background: var(--surface) !important;
    border: 1px solid var(--border) !important;
    color: var(--text) !important;
    border-radius: 8px !important;
    font-family: 'DM Mono', monospace !important;
}

.stTextInput input::placeholder, .stTextArea textarea::placeholder {
    color: var(--text3) !important;
}

.stTextInput input:focus, .stTextArea textarea:focus {
    border-color: var(--accent2) !important;
    box-shadow: 0 0 16px rgba(63,255,210,0.2) !important;
}

/* Buttons */
.stButton button {
    background: linear-gradient(135deg, var(--accent), #1db89a) !important;
    color: var(--bg) !important;
    border: none !important;
    font-family: 'Syne', sans-serif !important;
    font-weight: 700 !important;
    font-size: 13px !important;
    letter-spacing: 0.04em;
    padding: 12px 28px !important;
    border-radius: 8px !important;
    transition: all 0.25s;
    box-shadow: 0 4px 24px rgba(63,255,210,0.25) !important;
}

.stButton button:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 32px rgba(63,255,210,0.35) !important;
}

/* Cards */
.card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 24px;
    box-shadow: 0 4px 24px rgba(0,0,0,0.4);
}

.card:hover {
    border-color: var(--accent2);
    background: var(--surface2);
}

/* Metrics */
.metric {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 20px;
}

.metric-value {
    font-family: 'Syne', sans-serif;
    font-size: 28px;
    font-weight: 800;
    color: var(--accent);
}

.metric-label {
    font-family: 'DM Mono', monospace;
    font-size: 10px;
    color: var(--text3);
    text-transform: uppercase;
    letter-spacing: 0.06em;
    margin-top: 6px;
}

/* Header */
.header-banner {
    background: rgba(7,11,18,0.95);
    backdrop-filter: blur(20px);
    border-bottom: 1px solid var(--border2);
    padding: 16px 32px;
    margin: -16px -16px 0 -16px;
}

.header-content {
    max-width: 1400px;
    margin: 0 auto;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 24px;
}

.logo {
    display: flex;
    align-items: center;
    gap: 10px;
}

.logo-mark {
    width: 32px;
    height: 32px;
    background: linear-gradient(135deg, var(--accent), #0a5c52);
    border-radius: 8px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 800;
    color: var(--bg);
    box-shadow: var(--glow-sm);
}

.logo-text {
    font-family: 'Syne', sans-serif;
    font-weight: 800;
    font-size: 18px;
    color: var(--accent);
}

/* Sections */
.section-label {
    font-family: 'DM Mono', monospace;
    font-size: 11px;
    letter-spacing: 0.12em;
    color: var(--accent2);
    text-transform: uppercase;
    margin-bottom: 16px;
}

.section-title {
    font-family: 'Syne', sans-serif;
    font-size: 28px;
    font-weight: 800;
    margin-bottom: 16px;
    letter-spacing: -0.02em;
}

.section-desc {
    color: var(--text2);
    font-size: 15px;
    font-weight: 300;
    line-height: 1.75;
}

/* Badge */
.badge {
    display: inline-block;
    background: rgba(63,255,210,0.06);
    border: 1px solid rgba(63,255,210,0.2);
    border-radius: 100px;
    padding: 6px 14px;
    font-family: 'DM Mono', monospace;
    font-size: 11px;
    color: var(--accent2);
    letter-spacing: 0.06em;
}

/* Feature grid */
.feature-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
    gap: 12px;
    margin-top: 24px;
}

.feature-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 24px;
    transition: all 0.3s;
}

.feature-card:hover {
    background: var(--surface2);
    border-color: var(--accent2);
}

.feature-icon {
    font-size: 20px;
    margin-bottom: 12px;
}

/* Match result styling */
.match-highlight {
    background: rgba(63,255,210,0.2);
    padding: 2px 4px;
    border-radius: 2px;
    box-shadow: 0 0 6px rgba(63,255,210,0.3);
    font-weight: 500;
}

.base-a { color: #ff6b8a; font-weight: 600; }
.base-t { color: #f5c842; font-weight: 600; }
.base-c { color: #3fffd2; font-weight: 600; }
.base-g { color: #a78bfa; font-weight: 600; }

/* Transition table */
.transition-table {
    width: 100%;
    border-collapse: collapse;
    font-family: 'DM Mono', monospace;
    font-size: 12px;
}

.transition-table thead {
    background: var(--bg);
    color: var(--text3);
}

.transition-table th {
    padding: 8px 12px;
    border: 1px solid var(--border2);
    text-align: center;
    font-weight: 500;
    font-size: 11px;
}

.transition-table td {
    padding: 8px 12px;
    border: 1px solid var(--border2);
    text-align: center;
    color: var(--text2);
}

.transition-table tbody tr:hover td {
    background: rgba(63,255,210,0.03);
}

.accept-state {
    color: var(--accent);
    font-weight: 600;
}

/* Layout containers */
.stContainer {
    max-width: 1400px;
    margin: 0 auto;
}

</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────
# SESSION STATE
# ─────────────────────────────────────────────────────────────────
if "pattern" not in st.session_state:
    st.session_state.pattern = "ATCG"
if "genome" not in st.session_state:
    st.session_state.genome = ""
if "matches" not in st.session_state:
    st.session_state.matches = []
if "delta" not in st.session_state:
    st.session_state.delta = None
if "accept_state" not in st.session_state:
    st.session_state.accept_state = None

# ─────────────────────────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────────────────────────
st.markdown("""
<div class="header-banner">
    <div class="header-content">
        <div class="logo">
            <div class="logo-mark">⬡</div>
            <div class="logo-text">GeneFlow</div>
        </div>
        <div style="font-family: 'DM Mono', monospace; font-size: 11px; color: var(--text2); letter-spacing: 0.06em; text-transform: uppercase;">
            DNA Pattern Matching via Finite Automata
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────
# MAIN CONTENT
# ─────────────────────────────────────────────────────────────────

# Tabs
tab1, tab2, tab3, tab4 = st.tabs(["🔤 Matcher", "⬡ DFA Viewer", "📈 Match Plot", "📊 Analysis"])

# ─────────────────────────────────────────────────────────────────
# TAB 1: MATCHER
# ─────────────────────────────────────────────────────────────────
with tab1:
    st.markdown('<div class="section-label">INPUT</div>', unsafe_allow_html=True)
    st.markdown('<h2 class="section-title">DNA Pattern Matcher</h2>', unsafe_allow_html=True)
    st.markdown('<p class="section-desc">Enter a DNA pattern and genome sequence. The matcher will find all occurrences using O(n) DFA scanning.</p>', unsafe_allow_html=True)

    col1, col2 = st.columns([1, 1])

    with col1:
        st.markdown("**Pattern (P)**", help="4-character DNA sequence: A, T, C, G")
        pattern = st.text_input("Pattern", value=st.session_state.pattern, key="pattern_input", max_chars=20).upper()
        if pattern != st.session_state.pattern:
            st.session_state.pattern = pattern

    with col2:
        st.markdown("**Genome Source**")
        input_method = st.radio("Load from:", ["Direct Input", "Example FASTA", "Upload File"], horizontal=True, label_visibility="collapsed")

    if input_method == "Direct Input":
        st.markdown("**Genome Sequence (T)**")
        genome = st.text_area("Genome", height=100, value=st.session_state.genome, key="genome_input")
        st.session_state.genome = genome.upper()
    elif input_method == "Example FASTA":
        example_genomes = {
            "Sample 1 (2048 bp)": "AATGCATGCTAGCTAGCTGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATC" * 32,
            "Sample 2 (Custom)": "ATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATC" * 30,
        }
        selected = st.selectbox("Example sequences", list(example_genomes.keys()))
        st.session_state.genome = example_genomes[selected]
        genome = st.session_state.genome
    else:
        uploaded = st.file_uploader("Upload FASTA file", type=["fasta", "fa", "faa"])
        if uploaded:
            try:
                if HAS_BIO:
                    if hasattr(uploaded, "seek"):
                        uploaded.seek(0)
                    records = list(SeqIO.parse(uploaded, "fasta"))
                    pieces = ["".join(ch for ch in str(rec.seq).upper() if ch in "ATCG") for rec in records]
                    genome = "".join(pieces)
                    if not genome:
                        raise ValueError("No valid A/T/C/G bases found in FASTA")
                else:
                    genome = load_uploaded_genome(uploaded)

                st.session_state.genome = genome
            except Exception as exc:
                st.error(f"FASTA load error: {exc}")
                genome = st.session_state.genome
        else:
            genome = st.session_state.genome

    # Validate input
    try:
        if not pattern:
            st.error("Pattern cannot be empty")
        elif not genome:
            st.error("Genome cannot be empty")
        elif set(pattern) - set("ATCG"):
            st.error(f"Pattern contains invalid characters. Use only A, T, C, G")
        elif set(genome) - set("ATCG"):
            st.error(f"Genome contains invalid characters. Use only A, T, C, G")
        else:
            # Run matching
            if st.button("🚀 Run Analysis", use_container_width=True, key="run_button"):
                with st.spinner("Building DFA and scanning genome..."):
                    start_time = time.time()
                    delta, accept_state = get_transition_table(pattern)
                    matches = find_matches(delta, accept_state, genome)
                    elapsed = time.time() - start_time

                    st.session_state.delta = delta
                    st.session_state.accept_state = accept_state
                    st.session_state.matches = matches

                    # Display results
                    st.success(f"✓ Scan complete in {elapsed*1000:.2f}ms")

                    # Results metrics
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.markdown(f'<div class="metric"><div class="metric-value">{len(matches)}</div><div class="metric-label">Matches Found</div></div>', unsafe_allow_html=True)
                    with col2:
                        st.markdown(f'<div class="metric"><div class="metric-value">{len(genome)}</div><div class="metric-label">Genome Length</div></div>', unsafe_allow_html=True)
                    with col3:
                        density = (len(matches) / len(genome) * 100) if genome else 0
                        st.markdown(f'<div class="metric"><div class="metric-value">{density:.2f}%</div><div class="metric-label">Match Density</div></div>', unsafe_allow_html=True)
                    with col4:
                        st.markdown(f'<div class="metric"><div class="metric-value">O(n)</div><div class="metric-label">Time Complexity</div></div>', unsafe_allow_html=True)

                    # Match positions
                    st.subheader("Match Positions")
                    if matches:
                        match_str = ", ".join([f"pos {m}" for m in matches[:20]])
                        if len(matches) > 20:
                            match_str += f", ... ({len(matches) - 20} more)"
                        st.markdown(f'<div style="font-family: \'DM Mono\', monospace; font-size: 12px; color: var(--accent2); padding: 12px; background: var(--surface); border: 1px solid var(--border); border-radius: 8px;">{match_str}</div>', unsafe_allow_html=True)

                        # Genome visualization
                        st.subheader("Genome Visualization (first 500 bases)")
                        display_genome = genome[:500]
                        highlight_html = ""
                        for i, base in enumerate(display_genome):
                            is_match = any(i - len(pattern) + 1 < m <= i for m in matches if m >= i - len(pattern) + 1)
                            color_class = f"base-{base.lower()}"
                            match_class = "match-highlight" if is_match else ""
                            highlight_html += f'<span class="{color_class} {match_class}">{base}</span>'

                        st.markdown(f'''
                        <div style="
                            font-family: 'DM Mono', monospace;
                            font-size: 12px;
                            line-height: 2;
                            letter-spacing: 0.08em;
                            word-break: break-all;
                            padding: 12px 14px;
                            background: var(--bg);
                            border: 1px solid var(--border);
                            border-radius: 8px;
                            overflow-x: auto;
                        ">
                            {highlight_html}
                        </div>
                        ''', unsafe_allow_html=True)
                    else:
                        st.info(f"No matches found for pattern '{pattern}' in genome")

    except ValueError as e:
        st.error(str(e))

# ─────────────────────────────────────────────────────────────────
# TAB 2: DFA VIEWER
# ─────────────────────────────────────────────────────────────────
with tab2:
    st.markdown('<div class="section-label">AUTOMATON</div>', unsafe_allow_html=True)
    st.markdown('<h2 class="section-title">Deterministic Finite Automaton</h2>', unsafe_allow_html=True)
    st.markdown('<p class="section-desc">Interactive visualization of the DFA state transition table and complexity metrics.</p>', unsafe_allow_html=True)

    if st.session_state.delta is None or st.session_state.pattern != pattern:
        try:
            delta, accept_state = get_transition_table(pattern)
            st.session_state.delta = delta
            st.session_state.accept_state = accept_state
        except:
            st.error("Enter a valid pattern first")
            delta, accept_state = None, None
    else:
        delta, accept_state = st.session_state.delta, st.session_state.accept_state

    if delta:
        # Complexity metrics
        st.markdown("### Complexity Analysis")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.markdown(f'<div class="metric"><div class="metric-value">O(n)</div><div class="metric-label">Scan Time</div></div>', unsafe_allow_html=True)
        with col2:
            st.markdown(f'<div class="metric"><div class="metric-value">O(m)</div><div class="metric-label">Space</div></div>', unsafe_allow_html=True)
        with col3:
            st.markdown(f'<div class="metric"><div class="metric-value">{accept_state + 1}</div><div class="metric-label">States</div></div>', unsafe_allow_html=True)
        with col4:
            st.markdown(f'<div class="metric"><div class="metric-value">4</div><div class="metric-label">Alphabet |Σ|</div></div>', unsafe_allow_html=True)

        # Transition table
        st.markdown("### Transition Table")
        table_data = []
        for state in range(accept_state + 1):
            row = {"State": f"q{state}"}
            for char in ALPHABET:
                next_state = delta[state][char]
                cell = f"q{next_state}"
                if next_state == accept_state and state == accept_state:
                    cell += " ✓"
                row[char] = cell
            table_data.append(row)

        df = pd.DataFrame(table_data)
        st.dataframe(df, use_container_width=True, hide_index=True)

        # Legend
        st.markdown("### Base Legend")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.markdown('<span class="base-a">🟥 A</span> Adenine', unsafe_allow_html=True)
        with col2:
            st.markdown('<span class="base-t">🟨 T</span> Thymine', unsafe_allow_html=True)
        with col3:
            st.markdown('<span class="base-c">🟦 C</span> Cytosine', unsafe_allow_html=True)
        with col4:
            st.markdown('<span class="base-g">🟪 G</span> Guanine', unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────
# TAB 3: MATCH PLOT
# ─────────────────────────────────────────────────────────────────
with tab3:
    st.markdown('<div class="section-label">VISUALIZATION</div>', unsafe_allow_html=True)
    st.markdown('<h2 class="section-title">Match Position Distribution</h2>', unsafe_allow_html=True)
    st.markdown('<p class="section-desc">Interactive chart showing all match positions across the genome sequence.</p>', unsafe_allow_html=True)

    if st.session_state.matches and st.session_state.genome:
        matches = st.session_state.matches
        genome_len = len(st.session_state.genome)

        # Position histogram
        fig = go.Figure()
        fig.add_trace(go.Histogram(
            x=matches,
            nbinsx=min(50, genome_len // 20),
            marker=dict(color='#3fffd2', opacity=0.7),
            name="Matches",
            hovertemplate="Position: %{x}<br>Count: %{y}<extra></extra>"
        ))
        fig.update_layout(
            title=f"Match Distribution (Pattern: '{pattern}')",
            xaxis_title="Genome Position",
            yaxis_title="Frequency",
            template="plotly_dark",
            hovermode="x unified",
            plot_bgcolor="rgba(17, 24, 39, 0.3)",
            paper_bgcolor="rgba(7, 11, 18, 0.8)",
            font=dict(family="'DM Mono', monospace", color="#e8f0ee"),
            margin=dict(l=60, r=60, t=80, b=60),
        )
        st.plotly_chart(fig, use_container_width=True)

        # Stats
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("First Match", f"pos {matches[0] if matches else 'N/A'}")
        with col2:
            st.metric("Last Match", f"pos {matches[-1] if matches else 'N/A'}")
        with col3:
            avg_spacing = (matches[-1] - matches[0]) / (len(matches) - 1) if len(matches) > 1 else 0
            st.metric("Avg Spacing", f"{avg_spacing:.0f} bp")
    else:
        st.info("Run the matcher first to see match distribution")

# ─────────────────────────────────────────────────────────────────
# TAB 4: ANALYSIS
# ─────────────────────────────────────────────────────────────────
with tab4:
    st.markdown('<div class="section-label">DETAILED ANALYSIS</div>', unsafe_allow_html=True)
    st.markdown('<h2 class="section-title">Comprehensive Results</h2>', unsafe_allow_html=True)
    st.markdown('<p class="section-desc">Statistical breakdown and detailed match information.</p>', unsafe_allow_html=True)

    if st.session_state.matches and st.session_state.genome:
        matches = st.session_state.matches

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Matches", len(matches))
        with col2:
            st.metric("Genome Length", len(st.session_state.genome))
        with col3:
            density = len(matches) / len(st.session_state.genome) * 100
            st.metric("Match Density", f"{density:.4f}%")

        # Match details table
        st.markdown("### Match Details")
        match_details = []
        for i, pos in enumerate(matches[:100], 1):
            context_start = max(0, pos - 5)
            context_end = min(len(st.session_state.genome), pos + len(pattern) + 5)
            context = st.session_state.genome[context_start:context_end]
            match_details.append({
                "#": i,
                "Position": pos,
                "Context": context,
                "Distance from Start": pos,
            })

        df_matches = pd.DataFrame(match_details)
        st.dataframe(df_matches, use_container_width=True, hide_index=True)

        if len(matches) > 100:
            st.info(f"Showing first 100 of {len(matches)} matches")

        # Export options
        st.markdown("### Export Results")
        csv_data = pd.DataFrame({"position": matches})
        st.download_button(
            "📥 Download Matches (CSV)",
            csv_data.to_csv(index=False),
            file_name=f"matches_{pattern}.csv",
            mime="text/csv"
        )
    else:
        st.info("Run the matcher first to see detailed analysis")

# ─────────────────────────────────────────────────────────────────
# FOOTER
# ─────────────────────────────────────────────────────────────────
st.markdown("""
<div style="
    margin-top: 80px;
    padding-top: 40px;
    border-top: 1px solid rgba(99,210,190,0.06);
    font-family: 'DM Mono', monospace;
    font-size: 11px;
    color: var(--text3);
    text-align: center;
    letter-spacing: 0.05em;
">
    ⬡ GeneFlow · DNA String Matching · TAFL Project · 2026
</div>
""", unsafe_allow_html=True)

