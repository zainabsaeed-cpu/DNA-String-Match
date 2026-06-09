"""FASTA genome loader used by the PyQt simulator."""

from __future__ import annotations

from pathlib import Path


VALID = {"A", "T", "C", "G"}


def _clean_chunks(chunks: list[str]) -> str:
    genome = "".join(chunks)
    cleaned = "".join(ch for ch in genome if ch in VALID)
    if not cleaned:
        raise ValueError("No valid DNA sequence found in input (expected A/T/C/G).")
    return cleaned


def load_genome_text(text: str) -> str:
    """Load FASTA/plain-text DNA sequence from text and keep only A/T/C/G symbols."""
    chunks: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith(">") or line.startswith(";"):
            continue
        chunks.append(line.upper())
    return _clean_chunks(chunks)


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

    return _clean_chunks(chunks)


def load_uploaded_genome(uploaded_file) -> str:
    """Load FASTA/plain-text DNA sequence from a file-like uploaded object."""
    if uploaded_file is None:
        raise ValueError("No file provided.")

    if hasattr(uploaded_file, "seek"):
        uploaded_file.seek(0)

    if hasattr(uploaded_file, "getvalue"):
        raw = uploaded_file.getvalue()
    else:
        raw = uploaded_file.read()

    if isinstance(raw, bytes):
        text = raw.decode("utf-8", errors="ignore")
    else:
        text = str(raw)

    return load_genome_text(text)

