#!/usr/bin/env python3
"""Upload Te Reo pronunciation rules to ElevenLabs and print the dictionary IDs.

One-shot setup script. Run this once after creating an ElevenLabs API key
that has the *Pronunciation Dictionaries: Write* scope. Paste the printed
IDs into ``.env`` and restart the backend; every TTS call will then route
through the dictionary so Te Reo place names are pronounced correctly.

Reads ``pronunciations.pls`` (the canonical, human-readable reference)
and converts it to ElevenLabs' ``add-from-rules`` JSON format. The PLS
``add-from-file`` endpoint exists too, but its parser is finicky — the
JSON rules format is more reliable and produces an identical dictionary.

Stdlib-only — no pip install needed.

Usage:
    set -a && source .env && set +a
    python3 scripts/setup_pronunciation_dict.py

Re-running creates a NEW dictionary each time (ElevenLabs doesn't dedupe by
name). Either delete the old one in the dashboard, or update in place via
the ``add-rules-from-file`` endpoint manually.
"""

from __future__ import annotations

import json
import os
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

API_BASE = "https://api.elevenlabs.io/v1"
PLS_FILE = Path(__file__).resolve().parent / "pronunciations.pls"
DICT_NAME = "aotearoa-voice-te-reo"
DICT_DESCRIPTION = (
    "Te Reo Māori place names, iwi names, and greetings for the "
    "Aotearoa Voice tour-guide demo. See scripts/pronunciations.pls."
)

PLS_NAMESPACE = {"pls": "http://www.w3.org/2005/01/pronunciation-lexicon"}


def parse_pls_to_rules(path: Path) -> list[dict]:
    """Parse a W3C PLS lexicon and return ElevenLabs ``add-from-rules`` entries.

    Each ``<lexeme>`` becomes one rule per ``<grapheme>``. The phoneme is
    shared across all graphemes within a lexeme.
    """
    tree = ET.parse(path)
    root = tree.getroot()
    alphabet = root.attrib.get("alphabet", "ipa")

    rules: list[dict] = []
    for lexeme in root.findall("pls:lexeme", PLS_NAMESPACE):
        graphemes = [
            (g.text or "").strip()
            for g in lexeme.findall("pls:grapheme", PLS_NAMESPACE)
        ]
        graphemes = [g for g in graphemes if g]

        phoneme_el = lexeme.find("pls:phoneme", PLS_NAMESPACE)
        phoneme = (phoneme_el.text or "").strip() if phoneme_el is not None else ""

        if not graphemes or not phoneme:
            continue

        for g in graphemes:
            rules.append(
                {
                    "string_to_replace": g,
                    "type": "phoneme",
                    "phoneme": phoneme,
                    "alphabet": alphabet,
                }
            )
    return rules


def main() -> int:
    api_key = os.environ.get("ELEVENLABS_API_KEY", "").strip()
    if not api_key or "placeholder" in api_key:
        print(
            "ERROR: ELEVENLABS_API_KEY is not set (or is still the placeholder).\n"
            "       Run `set -a && source .env && set +a` first, with a real key in .env.",
            file=sys.stderr,
        )
        return 1

    if not PLS_FILE.exists():
        print(f"ERROR: {PLS_FILE} not found.", file=sys.stderr)
        return 1

    try:
        rules = parse_pls_to_rules(PLS_FILE)
    except ET.ParseError as e:
        print(f"ERROR: {PLS_FILE.name} is not valid XML: {e}", file=sys.stderr)
        return 1

    if not rules:
        print(f"ERROR: no rules parsed from {PLS_FILE.name}.", file=sys.stderr)
        return 1

    print(f"Parsed {len(rules)} rules from {PLS_FILE.name}.")
    print(f"Uploading dictionary '{DICT_NAME}' to ElevenLabs...")

    body = json.dumps(
        {
            "name": DICT_NAME,
            "description": DICT_DESCRIPTION,
            "rules": rules,
        }
    ).encode("utf-8")

    req = Request(
        f"{API_BASE}/pronunciation-dictionaries/add-from-rules",
        data=body,
        headers={
            "xi-api-key": api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )

    try:
        with urlopen(req, timeout=30) as response:
            data = json.loads(response.read())
    except HTTPError as e:
        print(f"ERROR: HTTP {e.code}", file=sys.stderr)
        raw = e.read()
        try:
            print(json.dumps(json.loads(raw), indent=2), file=sys.stderr)
        except (json.JSONDecodeError, ValueError):
            print(raw.decode("utf-8", "replace"), file=sys.stderr)
        if e.code == 401:
            print(
                "\nHint: 401 usually means the API key lacks the "
                "'Pronunciation Dictionaries: Write' scope.",
                file=sys.stderr,
            )
        return 1
    except URLError as e:
        print(f"ERROR: Network error: {e}", file=sys.stderr)
        return 1

    dict_id = data.get("id")
    version_id = data.get("version_id")

    if not dict_id or not version_id:
        print(f"ERROR: unexpected response shape: {data}", file=sys.stderr)
        return 1

    print()
    print("✓ Dictionary uploaded.")
    print(f"  name:  {data.get('name')}")
    print(f"  rules: {len(rules)} entries")
    print()
    print("Add these to .env (or replace the existing values):")
    print()
    print(f"  ELEVENLABS_PRONUNCIATION_DICTIONARY_ID={dict_id}")
    print(f"  ELEVENLABS_PRONUNCIATION_DICTIONARY_VERSION_ID={version_id}")
    print()
    print("Then restart the backend so it picks up the new env:")
    print()
    print("  docker compose up -d --force-recreate backend")
    return 0


if __name__ == "__main__":
    sys.exit(main())
