"""FASTA genome loader used by the PyQt simulator."""

from __future__ import annotations

from pathlib import Path


VALID = {"A", "T", "C", "G"}


def load_genome(path: str) -> str:
    """Load FASTA/plain-text DNA sequence and keep only A/T/C/G symbols."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"File not found: {path}")

    chunks = []
    with p.open("r", encoding="utf-8") as fh:
        for raw in fh:
            line = raw.strip()
            if not line or line.startswith(">"):
                continue
            chunks.append(line.upper())

    genome = "".join(chunks)
    cleaned = "".join(ch for ch in genome if ch in VALID)

    if not cleaned:
        raise ValueError("No valid DNA sequence found in file (expected A/T/C/G).")

    return cleaned

