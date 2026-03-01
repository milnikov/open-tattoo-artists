"""
Resume state: scrape_state.json with completed artist_ids and last URL index.
"""

import json
from pathlib import Path

from _repo_root import repo_path

STATE_FILE = "packages/scraper/scrape_state.json"


def _state_path(suffix: str = "") -> Path:
    """Path for state file, with optional suffix (e.g. _w0 for worker 0)."""
    base = repo_path("packages", "scraper", "scrape_state.json")
    if suffix:
        return base.parent / f"scrape_state{suffix}.json"
    return base


def load_state(state_file: str | Path | None = None) -> dict:
    """Load state: {completed_ids: set, last_index: int}."""
    path = Path(state_file) if state_file else repo_path(STATE_FILE)
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return {
                "completed_ids": set(data.get("completed_ids", [])),
                "last_index": data.get("last_index", -1),
            }
    return {"completed_ids": set(), "last_index": -1}


def save_state(completed_ids: set, last_index: int, state_file: str | Path | None = None) -> None:
    """Persist state."""
    path = Path(state_file) if state_file else repo_path(STATE_FILE)
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


def mark_completed(artist_id: str, state: dict, last_index: int, state_file: str | Path | None = None) -> None:
    """Update state with new completion."""
    state["completed_ids"].add(artist_id)
    state["last_index"] = last_index
    save_state(state["completed_ids"], last_index, state_file)


def merge_worker_states(worker_suffixes: list[str], main_state_path: Path | None = None) -> None:
    """Merge completed_ids from worker state files into main state. Call after parallel run."""
    main_path = main_state_path or repo_path(STATE_FILE)
    all_ids = set()
    max_index = -1
    if main_path.exists():
        with open(main_path, encoding="utf-8") as f:
            data = json.load(f)
            all_ids = set(data.get("completed_ids", []))
            max_index = data.get("last_index", -1)
    for suf in worker_suffixes:
        wp = repo_path("packages", "scraper", f"scrape_state{suf}.json")
        if wp.exists():
            with open(wp, encoding="utf-8") as f:
                data = json.load(f)
                all_ids |= set(data.get("completed_ids", []))
                max_index = max(max_index, data.get("last_index", -1))
    save_state(all_ids, max_index, main_path)
