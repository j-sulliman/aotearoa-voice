from __future__ import annotations

from datetime import datetime, timedelta
from . import LOCATIONS_BY_ID

# Location archetypes — coarse climate buckets keyed by location_id.
# We don't hit a real weather API; the spec calls for realistic seasonal data
# from a stub. The buckets approximate long-run averages so the agent's
# answers don't surprise a Kiwi listener.
_ARCHETYPE = {
    # Original 8 demo locations
    "wai-o-tapu":         "north_inland",
    "tongariro-crossing": "alpine",
    "aoraki":             "alpine",
    "hokitika":           "west_coast",
    "waiheke":            "north_coast",
    "cape-reinga":        "subtropical",
    "milford-sound":      "fiordland",
    "tamaki-makaurau":    "north_coast",
    # Extended set
    "waikato":            "north_inland",
    "taupo":              "north_inland",
    "tauranga":           "north_coast",
    "rotorua":            "north_inland",
    "whangarei":          "subtropical",
    "whakatane":          "north_coast",
    "whanganui":          "north_coast",
    "taranaki":           "west_coast",
    "otautahi":           "canterbury",
    "wellington":         "wellington",
    "queenstown":         "central_otago",
    "dunedin":            "south_coast",
    "napier":             "hawkes_bay",
    "nelson":             "nelson",
}

# Average daytime high (°C) by archetype × NZ season.
# Seasons: summer (Dec-Feb), autumn (Mar-May), winter (Jun-Aug), spring (Sep-Nov)
_TEMPS = {
    "north_coast":   {"summer": 24, "autumn": 19, "winter": 14, "spring": 18},
    "north_inland":  {"summer": 23, "autumn": 17, "winter": 11, "spring": 16},
    "subtropical":   {"summer": 25, "autumn": 21, "winter": 16, "spring": 19},
    "west_coast":    {"summer": 19, "autumn": 16, "winter": 12, "spring": 15},
    "fiordland":     {"summer": 18, "autumn": 14, "winter": 8,  "spring": 13},
    "alpine":        {"summer": 16, "autumn": 9,  "winter": 1,  "spring": 8},
    "canterbury":    {"summer": 22, "autumn": 16, "winter": 10, "spring": 16},
    "wellington":    {"summer": 20, "autumn": 16, "winter": 11, "spring": 14},
    "central_otago": {"summer": 22, "autumn": 14, "winter": 4,  "spring": 14},
    "south_coast":   {"summer": 18, "autumn": 13, "winter": 8,  "spring": 12},
    "hawkes_bay":    {"summer": 25, "autumn": 19, "winter": 13, "spring": 17},
    "nelson":        {"summer": 22, "autumn": 16, "winter": 11, "spring": 15},
}

_CONDITIONS = {
    "north_coast":   {"summer": "warm and humid, afternoon showers possible",
                      "autumn": "settled and mild, light winds",
                      "winter": "cool, frequent rain bands from the west",
                      "spring": "changeable — sunshine and showers"},
    "north_inland":  {"summer": "warm with thunderstorm risk in the afternoon",
                      "autumn": "crisp mornings, clear afternoons",
                      "winter": "frosty mornings, thermal steam visible",
                      "spring": "breezy, mixed cloud and sun"},
    "subtropical":   {"summer": "humid and warm, occasional tropical squalls",
                      "autumn": "settled and balmy, light easterlies",
                      "winter": "mild, gusty westerlies",
                      "spring": "warm but unsettled"},
    "west_coast":    {"summer": "warm with rain bands rolling off the Tasman",
                      "autumn": "cool and damp, big-sky sunsets",
                      "winter": "cold, persistent rain — pack a jacket",
                      "spring": "still wet, longer dry windows"},
    "fiordland":     {"summer": "rain most days — that's the point",
                      "autumn": "cool, wet, dramatic cloud",
                      "winter": "cold and wet, snow on the tops",
                      "spring": "wet with bursts of brilliant clear days"},
    "alpine":        {"summer": "mostly clear with afternoon cloud build-up",
                      "autumn": "stable but cold mornings, snow possible up high",
                      "winter": "snow, ice, alpine conditions — guides recommended",
                      "spring": "still wintry, lengthening daylight"},
    "canterbury":    {"summer": "warm and dry, occasional gusty nor'wester",
                      "autumn": "crisp, clear and stable — driving weather",
                      "winter": "frosty mornings, often clear days; snow on the hills inland",
                      "spring": "changeable, strong nor'westers possible"},
    "wellington":    {"summer": "warm with gusty southerlies — fine spells between fronts",
                      "autumn": "settled and clear when the wind drops",
                      "winter": "cool and gusty, frequent fronts off the Tasman",
                      "spring": "famously windy, mixed cloud and sun"},
    "central_otago": {"summer": "warm and dry — schist rocks shimmer in the heat",
                      "autumn": "cold mornings, brilliant willow colour, clear days",
                      "winter": "frosty and clear; ski conditions on the Remarkables",
                      "spring": "rapidly warming, lengthening days"},
    "south_coast":   {"summer": "cool maritime, frequent sea fog mornings",
                      "autumn": "still and clear when the southerly drops",
                      "winter": "cold but rarely freezing; frequent rain bands",
                      "spring": "blustery, slowly warming"},
    "hawkes_bay":    {"summer": "warm and dry — classic vintage weather",
                      "autumn": "settled and warm; harvest season",
                      "winter": "cool and frosty inland, mild on the coast",
                      "spring": "warming fast, breezy at times"},
    "nelson":        {"summer": "warm and reliably sunny — most sunshine in the country",
                      "autumn": "stable and clear, classic walking weather",
                      "winter": "cool and crisp; often clear afternoons",
                      "spring": "warming with occasional westerly fronts"},
}


def _season_for(month: int) -> str:
    if month in (12, 1, 2):
        return "summer"
    if month in (3, 4, 5):
        return "autumn"
    if month in (6, 7, 8):
        return "winter"
    return "spring"


def get_weather(location_id: str) -> dict:
    """Return realistic seasonal weather for a location.

    This is a deliberate stub: we don't call a real weather API for the demo.
    Values are long-run averages by climate archetype and current NZ season.

    Args:
        location_id: The location's stable ID — see ``find_locations``.

    Returns:
        A dict with current conditions and a 3-day outlook, or
        ``{"error": ...}`` if the ID isn't known.
    """
    if location_id not in LOCATIONS_BY_ID:
        return {
            "error": f"Unknown location_id '{location_id}'.",
            "known_ids": list(LOCATIONS_BY_ID.keys()),
        }

    archetype = _ARCHETYPE.get(location_id, "north_coast")
    today = datetime.utcnow()
    season = _season_for(today.month)
    base_temp = _TEMPS[archetype][season]
    conditions = _CONDITIONS[archetype][season]

    forecast_3day = []
    # Tiny deterministic wobble so the three days don't read identically.
    for offset, delta in enumerate([0, +1, -1]):
        d = today + timedelta(days=offset)
        forecast_3day.append(
            {
                "date": d.strftime("%Y-%m-%d"),
                "high_c": base_temp + delta,
                "low_c": base_temp + delta - 6,
                "conditions": conditions,
            }
        )

    return {
        "location_id": location_id,
        "season": season,
        "archetype": archetype,
        "temp_c": base_temp,
        "conditions": conditions,
        "forecast_3day": forecast_3day,
        "note": "Demo stub — long-run seasonal averages, not a live forecast.",
    }
