from __future__ import annotations

from . import PRONUNCIATIONS

# Build a case-insensitive lookup that strips macrons and hyphens, so
# "Tamaki Makaurau", "tāmaki makaurau", and "Tāmaki-Makaurau" all match.
_MACRON_MAP = str.maketrans({
    "ā": "a", "ē": "e", "ī": "i", "ō": "o", "ū": "u",
    "Ā": "a", "Ē": "e", "Ī": "i", "Ō": "o", "Ū": "u",
})


def _normalise(s: str) -> str:
    return s.translate(_MACRON_MAP).lower().replace("-", " ").strip()


_NORMALISED_LOOKUP = {_normalise(k): k for k in PRONUNCIATIONS}


def get_pronunciation_guide(word: str) -> dict:
    """Return a pronunciation guide for a Te Reo Māori or Aotearoa place name.

    The lookup is forgiving: macrons, hyphens, and case are normalised so
    "tamaki makaurau" matches "Tāmaki Makaurau".

    Args:
        word: The word or place name to pronounce (e.g. "Wai-O-Tapu").

    Returns:
        A dict with ``phonetic``, ``audio_hint``, and ``meaning``, or
        ``{"error": ...}`` if the word isn't in our verified table. We never
        guess — pronunciation is high-stakes for a Te Reo demo.
    """
    key = _NORMALISED_LOOKUP.get(_normalise(word))
    if not key:
        return {
            "error": f"No verified pronunciation for '{word}'.",
            "guidance": (
                "Use the English form rather than guessing a Te Reo "
                "pronunciation. Te Aka Māori Dictionary is the authoritative "
                "reference for verified audio."
            ),
            "available_words": sorted(PRONUNCIATIONS.keys()),
        }
    entry = PRONUNCIATIONS[key]
    return {
        "word": key,
        "phonetic": entry["phonetic"],
        "audio_hint": entry["audio_hint"],
        "meaning": entry.get("meaning"),
    }
