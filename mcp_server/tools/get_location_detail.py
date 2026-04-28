from __future__ import annotations

from . import LOCATIONS_BY_ID


def get_location_detail(location_id: str) -> dict:
    """Return the full record for a single location.

    Args:
        location_id: The location's stable ID, e.g. ``"wai-o-tapu"`` or
            ``"tamaki-makaurau"``. Use ``find_locations`` first if you need
            to discover the ID.

    Returns:
        The full location object, or ``{"error": ...}`` if the ID isn't known.
    """
    loc = LOCATIONS_BY_ID.get(location_id)
    if not loc:
        return {
            "error": f"Unknown location_id '{location_id}'.",
            "known_ids": list(LOCATIONS_BY_ID.keys()),
        }
    return {
        "id": loc["id"],
        "name": loc["name"],
        "name_en": loc["name_en"],
        "name_mi": loc["name_mi"],
        "region": loc["region"],
        "lat": loc["lat"],
        "lng": loc["lng"],
        "themes": loc["themes"],
        "hero_image": loc["hero_image"],
        "description": loc["description"],
        "things_to_do": loc["things_to_do"],
        "best_season": loc["best_season"],
        "transit_context": loc["transit_context"],
    }
