"""DFA construction helpers for DNA pattern matching."""

from __future__ import annotations

from typing import Dict, Tuple


ALPHABET = ("A", "T", "C", "G")


def get_transition_table(pattern: str) -> Tuple[Dict[int, Dict[str, int]], int]:
    """Build DFA transition table for a single DNA pattern.

    Returns:
        (delta, accept_state)
        delta[state][char] -> next_state
    """
    pattern = pattern.strip().upper()
    if not pattern:
        raise ValueError("Pattern cannot be empty.")

    invalid = set(pattern) - set(ALPHABET)
    if invalid:
        raise ValueError(f"Pattern contains invalid characters: {sorted(invalid)}")

    m = len(pattern)
    delta: Dict[int, Dict[str, int]] = {
        state: {char: 0 for char in ALPHABET} for state in range(m + 1)
    }

    for state in range(m + 1):
        for char in ALPHABET:
            prefix = pattern[:state] + char
            for k in range(min(m, state + 1), -1, -1):
                if prefix.endswith(pattern[:k]):
                    delta[state][char] = k
                    break

    return delta, m


def build_dfa(pattern: str):
    """Backwards-compatible list-based DFA format used by old scripts."""
    delta, accept_state = get_transition_table(pattern)
    return [delta[s] for s in range(accept_state + 1)]
