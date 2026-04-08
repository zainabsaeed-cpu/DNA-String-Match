"""AI-powered DNA pattern suggestion using the Hugging Face Inference API."""

from __future__ import annotations

import json
import os
import ssl
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from typing import Dict, Optional

try:
    import certifi
    HAS_CERTIFI = True
except ImportError:
    HAS_CERTIFI = False

DEFAULT_MODEL = "mistralai/Mistral-7B-Instruct-v0.3"
FALLBACK_MODELS = [
    "mistralai/Mistral-7B-Instruct-v0.3",
    "meta-llama/Llama-3.1-8B-Instruct",
    "HuggingFaceH4/zephyr-7b-beta",
    "Qwen/Qwen2.5-3B-Instruct",
]
DEFAULT_ENDPOINT = "https://router.huggingface.co/v1/chat/completions"


def _resolve_hf_token(api_key: Optional[str] = None) -> Optional[str]:
    if api_key:
        return api_key.strip()

    def read_dotenv_file(path: Path) -> Optional[str]:
        if not path.is_file():
            return None
        try:
            for raw_line in path.read_text(encoding="utf-8").splitlines():
                line = raw_line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                name, value = line.split("=", 1)
                if name.strip() in {
                    "HUGGINGFACE_API_KEY",
                    "HUGGINGFACEHUB_API_TOKEN",
                    "HUGGING_FACE_HUB_TOKEN",
                    "HF_TOKEN",
                    "GOOGLE_API_KEY",
                }:
                    return value.strip().strip('"').strip("'")
        except OSError:
            return None
        return None

    for env_name in (
        "HUGGINGFACE_API_KEY",
        "HUGGINGFACEHUB_API_TOKEN",
        "HUGGING_FACE_HUB_TOKEN",
        "HF_TOKEN",
        "GOOGLE_API_KEY",
    ):
        value = os.getenv(env_name)
        if value:
            return value.strip()

    search_roots = [Path.cwd(), Path(__file__).resolve().parent]
    for root in search_roots:
        token = read_dotenv_file(root / ".env")
        if token:
            return token

    return None


def _extract_generated_text(payload: object) -> str:
    if isinstance(payload, list):
        for item in payload:
            if isinstance(item, dict):
                if "generated_text" in item and item["generated_text"]:
                    return str(item["generated_text"])
                if "summary_text" in item and item["summary_text"]:
                    return str(item["summary_text"])
        return ""

    if isinstance(payload, dict):
        if "generated_text" in payload and payload["generated_text"]:
            return str(payload["generated_text"])
        if "summary_text" in payload and payload["summary_text"]:
            return str(payload["summary_text"])
        if "error" in payload:
            raise RuntimeError(str(payload["error"]))

    return ""


class AIQueryHandler:
    """Extract DNA patterns from natural language queries using Hugging Face."""

    def __init__(self, api_key: Optional[str] = None, model_name: str = DEFAULT_MODEL):
        self.api_key = _resolve_hf_token(api_key)
        if not self.api_key:
            raise ImportError(
                "Hugging Face API key not configured. Set HUGGINGFACE_API_KEY, "
                "HUGGINGFACEHUB_API_TOKEN, or HF_TOKEN in your environment."
            )
        self.model_name = model_name
        self._conversation_history = []

    def _model_candidates(self) -> list[str]:
        candidates = [self.model_name, *FALLBACK_MODELS]
        ordered: list[str] = []
        for candidate in candidates:
            if candidate and candidate not in ordered:
                ordered.append(candidate)
        return ordered

    def _friendly_error(self, error: Exception) -> str:
        """Convert SDK/API failures into user-friendly messages."""
        error_msg = str(error)
        lower = error_msg.lower()
        if "api_key" in lower or "401" in error_msg or "403" in error_msg:
            return "Invalid or missing Hugging Face API key. Check your token in your Hugging Face settings."
        if "quota" in lower or "429" in error_msg:
            return "Hugging Face request limit hit. Wait a minute and try again."
        if "model is currently loading" in lower:
            return "The Hugging Face model is loading. Try again in a moment."
        return f"Hugging Face error: {error_msg[:120]}"

    def _generate(self, prompt: str, max_new_tokens: int, temperature: float) -> str:
        ssl_context = ssl.create_default_context(cafile=certifi.where()) if HAS_CERTIFI else ssl.create_default_context()
        last_error: Optional[Exception] = None

        for model_name in self._model_candidates():
            payload = {
                "model": model_name,
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": max_new_tokens,
                "temperature": temperature,
                "stream": False,
                "top_p": 0.9,
            }
            request = Request(
                DEFAULT_ENDPOINT,
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                method="POST",
            )

            try:
                with urlopen(request, timeout=60, context=ssl_context) as response:
                    raw = response.read().decode("utf-8")
            except HTTPError as exc:
                error_body = exc.read().decode("utf-8", errors="ignore") if exc.fp else ""
                message = error_body or str(exc)
                last_error = RuntimeError(message)
                if "not supported by any provider" in message.lower() or exc.code in (404, 422):
                    continue
                raise last_error from exc
            except URLError as exc:
                message = str(exc)
                if "CERTIFICATE_VERIFY_FAILED" in message:
                    message = (
                        "SSL certificate verification failed. If this keeps happening on macOS, "
                        "install the Python certificates bundle or run the Python certificate installer."
                    )
                last_error = RuntimeError(message)
                raise last_error from exc

            parsed = json.loads(raw)
            if isinstance(parsed, dict) and parsed.get("error"):
                message = str(parsed["error"])
                last_error = RuntimeError(message)
                if "not supported by any provider" in message.lower():
                    continue
                raise last_error

            if isinstance(parsed, dict):
                choices = parsed.get("choices") or []
                if choices:
                    message = choices[0].get("message") or {}
                    content = message.get("content")
                    if content:
                        return str(content)

            generated = _extract_generated_text(parsed)
            if generated:
                return generated

            last_error = RuntimeError(f"No text returned by Hugging Face model '{model_name}'.")

        if last_error is not None:
            raise last_error
        raise RuntimeError("No Hugging Face models were available.")

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

            pattern = self._generate(prompt, max_new_tokens=32, temperature=0.1).strip().upper()

            if pattern == "NONE" or not pattern:
                return False, f"Could not extract a pattern from: '{query}'"

            # Remove any spaces or newlines the model might sneak in
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

            answer = self._generate(prompt, max_new_tokens=320, temperature=0.35).strip()
            if not answer:
                return False, "Hugging Face returned an empty response."

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