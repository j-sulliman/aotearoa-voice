"""Tour-guide tools backing the MCP server."""

from pathlib import Path
import json

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def _load_json(filename: str):
    with (DATA_DIR / filename).open("r", encoding="utf-8") as f:
        return json.load(f)


LOCATIONS: list[dict] = _load_json("locations.json")
LOCATIONS_BY_ID: dict[str, dict] = {loc["id"]: loc for loc in LOCATIONS}
PRONUNCIATIONS: dict[str, dict] = _load_json("pronunciations.json")
