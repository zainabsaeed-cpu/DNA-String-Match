"""AI-powered DNA pattern suggestion using Google Gemini API."""

from __future__ import annotations

from typing import Dict, Optional

try:
    import google.generativeai as genai
    HAS_GEMINI = True
except ImportError:
    HAS_GEMINI = False


class AIQueryHandler:
    """Extract DNA patterns from natural language queries using Google Gemini."""

    def __init__(self, api_key: Optional[str] = None):
        if not HAS_GEMINI:
            raise ImportError(
                "google-generativeai library not installed. "
                "Install with: pip install google-generativeai"
            )
        try:
            if api_key:
                genai.configure(api_key=api_key)
            else:
                genai.configure()  # Uses GOOGLE_API_KEY env var

            # ✅ FIX 1: Updated to gemini-2.0-flash (1.5-flash is deprecated)
            self.model = genai.GenerativeModel('gemini-2.0-flash')
        except Exception as e:
            raise ImportError(f"Gemini API key not configured: {str(e)}")

        self._conversation_history = []

    def _friendly_error(self, error: Exception) -> str:
        """Convert SDK/API failures into user-friendly messages."""
        error_msg = str(error)
        lower = error_msg.lower()
        if "api_key" in lower or "401" in error_msg or "403" in error_msg:
            return "Invalid or missing Gemini API key. Check your key at aistudio.google.com"
        if "quota" in lower or "429" in error_msg:
            return "Gemini free tier quota exceeded. Wait a minute and try again."
        return f"Gemini error: {error_msg[:120]}"

    def extract_pattern(self, query: str) -> tuple[bool, str]:
        """Extract a DNA pattern from a natural language query.

        Returns:
            (success, pattern_or_error_message)
        """
        if not query.strip():
            return False, "Query is empty."

        try:
            self._conversation_history.append({
                "role": "user",
                "content": query
            })

            prompt = f"""You are an expert in molecular biology and DNA sequence analysis.
A user is asking about DNA pattern matching.
Extract a single DNA pattern (using only A, T, C, G) from their request.
Return ONLY the pattern (4-8 nucleotides), or "NONE" if no valid pattern can be extracted.
Do not include explanations or extra text.

User query: {query}

Pattern:"""

            # ✅ FIX 2: Updated GenerationConfig usage (new SDK syntax)
            response = self.model.generate_content(
                prompt,
                generation_config={
                    "max_output_tokens": 64,
                    "temperature": 0.1,
                }
            )

            # ✅ FIX 3: Safely access response text
            if not response.candidates:
                return False, "Gemini returned no response. Try again."

            pattern = response.text.strip().upper()

            if pattern == "NONE" or not pattern:
                return False, f"Could not extract a pattern from: '{query}'"

            # Remove any spaces or newlines Gemini might sneak in
            pattern = pattern.replace(" ", "").replace("\n", "")

            # Validate DNA characters
            valid_chars = set("ATCG")
            if not all(c in valid_chars for c in pattern):
                return False, f"AI returned invalid DNA pattern: {pattern}"

            if not (4 <= len(pattern) <= 12):
                return False, f"Pattern length must be 4-12 bases, got: {len(pattern)}"

            return True, pattern

        except Exception as e:
            return False, self._friendly_error(e)

    def chat(self, message: str, context: Optional[Dict[str, str]] = None) -> tuple[bool, str]:
        """Generate a Gemini chat reply for the desktop assistant panel."""
        if not message.strip():
            return False, "Message is empty."

        try:
            self._conversation_history.append({"role": "user", "content": message})

            recent_turns = self._conversation_history[-8:]
            history_lines = [f"{item['role'].title()}: {item['content']}" for item in recent_turns]
            history_text = "\n".join(history_lines)

            context_lines = []
            if context:
                for key, value in context.items():
                    context_lines.append(f"- {key}: {value}")
            context_block = "\n".join(context_lines) if context_lines else "- none"

            prompt = f"""You are GeneFlow AI assistant for DNA finite-automata analysis.
Help the user with DNA pattern matching, DFA concepts, genome interpretation, and tool usage.
Keep answers concise, practical, and safe for scientific workflows.

Current app context:
{context_block}

Recent conversation:
{history_text}

Assistant reply:"""

            response = self.model.generate_content(
                prompt,
                generation_config={
                    "max_output_tokens": 450,
                    "temperature": 0.35,
                },
            )

            if not response.candidates:
                return False, "Gemini returned no response. Try again."

            answer = response.text.strip()
            if not answer:
                return False, "Gemini returned an empty response."

            self._conversation_history.append({"role": "assistant", "content": answer})
            return True, answer
        except Exception as e:
            return False, self._friendly_error(e)

    def get_motif_suggestions(self, genome: str, top_k: int = 3) -> list[dict]:
        """Suggest frequent motifs from genome using k-mer analysis.

        Returns list of dicts with 'motif', 'count', 'confidence' keys.
        """
        if len(genome) < 8:
            return []

        motif_counts: dict[str, int] = {}
        for k in range(6, 9):
            for i in range(len(genome) - k + 1):
                kmer = genome[i:i + k]
                if all(c in "ATCG" for c in kmer):
                    motif_counts[kmer] = motif_counts.get(kmer, 0) + 1

        suggestions = []
        for motif, count in sorted(motif_counts.items(), key=lambda x: -x[1])[:top_k]:
            confidence = min(100, (count / max(len(genome) - len(motif) + 1, 1)) * 100)
            suggestions.append({
                "motif": motif,
                "count": count,
                "confidence": round(confidence, 1)
            })

        return suggestions