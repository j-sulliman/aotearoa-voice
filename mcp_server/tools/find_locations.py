from __future__ import annotations

from typing import Literal
from . import LOCATIONS

Theme = Literal["nature", "city", "food", "history"]


def find_locations(
    region: str | None = None,
    theme: Theme | None = None,
) -> list[dict]:
    """List curated locations across Aotearoa, optionally filtered by region or theme.

    Args:
        region: Case-insensitive substring match against the location's region
            (e.g. "Auckland", "Rotorua", "South Island").
        theme: One of "nature", "city", "food", or "history".

    Returns:
        A list of summary objects: ``{id, name, region, themes, summary}``.
    """
    results = []
    region_q = region.strip().lower() if region else None

    for loc in LOCATIONS:
        if region_q and region_q not in loc["region"].lower():
            continue
        if theme and theme not in loc["themes"]:
            continue
        results.append(
            {
                "id": loc["id"],
                "name": loc["name"],
                "region": loc["region"],
                "themes": loc["themes"],
                "summary": loc["description"].split(". ")[0] + ".",
            }
        )
    return results
