"""
Resume state: scrape_state.json with completed artist_ids and last URL index.
"""

import json
from pathlib import Path

from _repo_root import repo_path

STATE_FILE = "packages/scraper/scrape_state.json"


def load_state() -> dict:
    """Load state: {completed_ids: set, last_index: int}."""
    path = repo_path(STATE_FILE)
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return {
                "completed_ids": set(data.get("completed_ids", [])),
                "last_index": data.get("last_index", 0),
            }
    return {"completed_ids": set(), "last_index": 0}


def save_state(completed_ids: set, last_index: int) -> None:
    """Persist state."""
    path = repo_path(STATE_FILE)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(
            {"completed_ids": sorted(completed_ids), "last_index": last_index},
            f,
            indent=2,
        )


def is_completed(artist_id: str, state: dict) -> bool:
    """Check if artist already processed (state or existing data file)."""
    if artist_id in state["completed_ids"]:
        return True
    data_file = repo_path("data", "artists", f"{artist_id}.json")
    return data_file.exists()


def mark_completed(artist_id: str, state: dict, last_index: int) -> None:
    """Update state with new completion."""
    state["completed_ids"].add(artist_id)
    state["last_index"] = last_index
    save_state(state["completed_ids"], last_index)
