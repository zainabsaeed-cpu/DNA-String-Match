"""Matcher utilities for DFA-based DNA search and step tracing."""

from __future__ import annotations

from typing import Dict, List

from dfa import get_transition_table


def find_matches(text: str, delta: Dict[int, Dict[str, int]], accept_state: int, pattern_len: int) -> List[int]:
    """Return 1-indexed match start positions."""
    state = 0
    positions: List[int] = []

    for i, ch in enumerate(text):
        state = delta[state].get(ch, 0)
        if state == accept_state:
            positions.append(i - pattern_len + 2)

    return positions


def trace_dfa(text: str, delta: Dict[int, Dict[str, int]], accept_state: int, pattern_len: int):
    """Return step-by-step DFA transitions for animation and logs."""
    state = 0
    trace = []

    for i, ch in enumerate(text):
        prev = state
        state = delta[state].get(ch, 0)
        trace.append(
            {
                "index": i,
                "char": ch,
                "prev_state": prev,
                "next_state": state,
                "is_match": state == accept_state,
                "match_start": (i - pattern_len + 2) if state == accept_state else None,
            }
        )

    return trace


def dfa_match(text: str, pattern: str):
    """Compatibility helper used by old `main.py` demo code (0-indexed)."""
    delta, accept_state = get_transition_table(pattern)
    one_indexed = find_matches(text.upper(), delta, accept_state, len(pattern))
    return [p - 1 for p in one_indexed]
