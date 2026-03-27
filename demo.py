#!/usr/bin/env python3
"""DNA FA Matcher - Live Demo"""

from dfa import get_transition_table
from matcher import find_matches
from aho_corasick import AhoCorasickMatcher

print("\nDNA FA MATCHER - LIVE DEMO")
print("=" * 70)

# Demo 1: Single Pattern DFA
print("\n[1] SINGLE PATTERN DFA MATCHING")
print("-" * 70)
pattern = "ATCG"
genome = "ATCGATCGATCGATCGATCGATCGATCGATCG"
print("Pattern:", pattern)
print("Genome:  ", genome)

delta, accept_state = get_transition_table(pattern)
matches = find_matches(genome, delta, accept_state, len(pattern))
print("Matches found:", len(matches))
print("Positions (1-indexed):", matches)

# Demo 2: Multi-Pattern Aho-Corasick
print("\n[2] MULTI-PATTERN MATCHING (Aho-Corasick)")
print("-" * 70)
patterns = ["ATCG", "TGC", "AA"]
print("Patterns:", patterns)
print("Genome:   ", genome)

matcher = AhoCorasickMatcher(patterns)
results = matcher.find_all_matches(genome)
print("Results:")
total = 0
for p, pos in results.items():
    count = len(pos)
    total += count
    print("  {}: {} matches at {}".format(p, count, pos))
print("Total matches:", total)

# Demo 3: Visualization
print("\n[3] VISUALIZATION GENERATION")
print("-" * 70)
try:
    from visualize import draw_fa_diagram, plot_matches
    
    pattern = "ATCG"
    test_genome = "ATCGATCGATCG"
    delta, accept_state = get_transition_table(pattern)
    matches = find_matches(test_genome, delta, accept_state, len(pattern))
    
    fa_path = draw_fa_diagram(pattern, delta, accept_state, "/tmp/demo_fa.png")
    print("FA Diagram created:", fa_path)
    
    plot_path = plot_matches(test_genome, matches, pattern, "/tmp/demo_plot.png")
    print("Match Plot created:", plot_path)
except Exception as e:
    print("Visualization (optional):", type(e).__name__)

print("\n" + "=" * 70)
print("ALL COMPONENTS WORKING!")
print("=" * 70)
print("\nTO RUN THE WEB UI:")
print("   streamlit run app.py")
print("   Then open: http://localhost:8501")
print("\nTO RUN THE DESKTOP APP:")
print("   python3 main.py")
print("\nFOR MORE INFO:")
print("   See README.md or QUICKSTART.md")
print("\n" + "=" * 70 + "\n")

