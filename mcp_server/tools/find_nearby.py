from __future__ import annotations

from typing import Literal
from . import LOCATIONS_BY_ID

Category = Literal["food", "accommodation", "walks"]


def find_nearby(location_id: str, category: Category) -> dict:
    """Find nearby food, accommodation, or walks for a given location.

    Args:
        location_id: The location's stable ID — see ``find_locations``.
        category: One of "food", "accommodation", or "walks".

    Returns:
        A dict with the location name and an array of suggestions, each with
        a ``name`` and a one-line ``note``. Returns ``{"error": ...}`` if the
        location ID isn't known.
    """
    loc = LOCATIONS_BY_ID.get(location_id)
    if not loc:
        return {
            "error": f"Unknown location_id '{location_id}'.",
            "known_ids": list(LOCATIONS_BY_ID.keys()),
        }
    suggestions = loc.get("nearby", {}).get(category, [])
    return {
        "location_id": location_id,
        "location_name": loc["name"],
        "category": category,
        "suggestions": suggestions,
    }
