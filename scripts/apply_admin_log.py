#!/usr/bin/env python
"""
Apply admin moderation decisions from a markdown log.

Supported lines (examples):

- Artist `cryptictattoo` (#carlosmacias) marked as **Studio** (should be hidden as studio).
- Artist `snot` ($NOT) marked as **Not artist**.
- Artist `brinditattoo` ('Brindi Tattoo') marked as **Verified artist**.
- Artist `foo` (Name) marked **Need to check** (session note).
- Legacy: Artist `bar` (Name) queued for **Instagram enrichment** … (sets verified `need_to_check` like Need to check).
- Session note: `Note: …` or `Session note: …` on its own bullet (printed in summary, no JSON change).
- Tattoo image `001` of artist `someartist` (Some Name) marked for **deletion**. Full: ..., Thumb: ...

Effects:
- "Studio"        -> sets verified: "studio" on that artist JSON.
- "Verified"      -> sets verified: "artist".
- "Need to check" -> sets verified: "need_to_check" on that artist JSON.
- Legacy **Instagram enrichment** queue lines -> same as Need to check (verified: "need_to_check").
- "Not artist"    -> deletes the artist JSON file (skips verified updates for that id).
- Session bullets `Note:` / `Session note:` -> printed only (no JSON change).
- Tattoo image    -> removes that image from the artist's tattoos[] array.

If one artist appears in several categories, precedence is: artist > studio > need_to_check.

Usage:
  python scripts/apply_admin_log.py path/to/admin-session.md
"""

import argparse
import json
import re
from pathlib import Path

RE_ARTIST_LINE = re.compile(
    r"^- Artist `(?P<id>[^`]+)` .* \*\*(?P<action>Studio|Verified artist|Not artist|Need to check)\*\*",
    re.IGNORECASE,
)

# Older /admin logs used Instagram wording; same as Need to check on disk.
RE_ARTIST_INSTAGRAM_LEGACY = re.compile(
    r"^- Artist `(?P<id>[^`]+)` .* \*\*Instagram enrichment\*\*",
    re.IGNORECASE,
)

# Free-form session notes (optional).
RE_SESSION_NOTE = re.compile(
    r"^- (?:Session note|Note):\s*(?P<text>.+)$",
    re.IGNORECASE,
)

RE_TATTOO_LINE = re.compile(
    r"^- Tattoo image `(?P<image_id>[^`]+)` of artist `(?P<artist_id>[^`]+)` .* \*\*deletion\*\*",
    re.IGNORECASE,
)


def parse_log(path: Path):
    studios: set[str] = set()
    verified_artists: set[str] = set()
    not_artists: set[str] = set()
    need_to_check: set[str] = set()
    session_notes: list[str] = []
    tattoo_deletes: dict[str, set[str]] = {}

    text = path.read_text(encoding="utf-8")
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("- "):
            continue

        m = RE_SESSION_NOTE.match(line)
        if m:
            session_notes.append(m.group("text").strip())
            continue

        m = RE_ARTIST_LINE.match(line)
        if m:
            artist_id = m.group("id").strip()
            action = m.group("action").lower()
            if action.startswith("studio"):
                studios.add(artist_id)
            elif action.startswith("verified"):
                verified_artists.add(artist_id)
            elif action.startswith("not artist"):
                not_artists.add(artist_id)
            elif "need to check" in action:
                need_to_check.add(artist_id)
            continue

        m = RE_ARTIST_INSTAGRAM_LEGACY.match(line)
        if m:
            need_to_check.add(m.group("id").strip())
            continue

        m = RE_TATTOO_LINE.match(line)
        if m:
            image_id = m.group("image_id").strip()
            artist_id = m.group("artist_id").strip()
            tattoo_deletes.setdefault(artist_id, set()).add(image_id)
            continue

    return studios, verified_artists, not_artists, need_to_check, session_notes, tattoo_deletes


def load_artist_json(artists_dir: Path, artist_id: str):
    path = artists_dir / f"{artist_id}.json"
    if not path.exists():
        print(f"[skip] artist JSON not found: {path}")
        return None, path
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data, path
    except Exception as e:
        print(f"[error] failed to parse {path}: {e}")
        return None, path


def save_artist_json(path: Path, data: dict):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def apply_log(log_path: Path, repo_root: Path):
    artists_dir = repo_root / "data" / "artists"
    if not artists_dir.is_dir():
        raise SystemExit(f"artists dir not found: {artists_dir}")

    (
        studios,
        verified_artists,
        not_artists,
        need_to_check,
        session_notes,
        tattoo_deletes,
    ) = parse_log(log_path)

    print(f"Studios: {sorted(studios)}")
    print(f"Verified artists: {sorted(verified_artists)}")
    print(f"Not artists (to delete): {sorted(not_artists)}")
    print(f"Need to check -> verified need_to_check: {sorted(need_to_check)}")
    if session_notes:
        print("Session notes (no auto-apply):")
        for note in session_notes:
            print(f"  - {note}")
    print(f"Tattoo deletions: {{artist_id: [image_ids...]}}")
    for aid, ids in tattoo_deletes.items():
        print(f"  {aid}: {sorted(ids)}")

    # Apply verified: artist > studio > need_to_check (later keys overwrite earlier in dict build)
    verified_targets: dict[str, str] = {}
    for artist_id in need_to_check:
        if artist_id not in not_artists:
            verified_targets[artist_id] = "need_to_check"
    for artist_id in studios:
        if artist_id not in not_artists:
            verified_targets[artist_id] = "studio"
    for artist_id in verified_artists:
        if artist_id not in not_artists:
            verified_targets[artist_id] = "artist"

    for artist_id in sorted(verified_targets.keys()):
        data, path = load_artist_json(artists_dir, artist_id)
        if data is None:
            continue
        verified_value = verified_targets[artist_id]
        data["verified"] = verified_value
        save_artist_json(path, data)
        print(f"[ok] set verified={verified_value!r} for {artist_id} ({path})")

    # Apply tattoo deletions
    for artist_id, image_ids in tattoo_deletes.items():
        data, path = load_artist_json(artists_dir, artist_id)
        if data is None:
            continue
        tattoos = data.get("tattoos")
        if not isinstance(tattoos, list):
            print(f"[skip] no tattoos array for {artist_id}")
            continue
        before = len(tattoos)
        remaining = [t for t in tattoos if str(t.get("image_id")) not in image_ids]
        removed = before - len(remaining)
        if removed == 0:
            print(f"[skip] no matching tattoos for {artist_id} ({sorted(image_ids)})")
            continue
        data["tattoos"] = remaining
        save_artist_json(path, data)
        print(f"[ok] removed {removed} tattoo(s) from {artist_id} ({path})")

    # Delete not-artist JSONs
    for artist_id in sorted(not_artists):
        path = artists_dir / f"{artist_id}.json"
        if not path.exists():
            print(f"[skip] not-artist file already missing: {path}")
            continue
        path.unlink()
        print(f"[ok] deleted not-artist JSON: {path}")


def main():
    parser = argparse.ArgumentParser(description="Apply admin markdown moderation log.")
    parser.add_argument("log_path", type=Path, help="Path to admin-session.md")
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Repo root (default: parent of scripts/)",
    )
    args = parser.parse_args()

    apply_log(args.log_path, args.repo_root)


if __name__ == "__main__":
    main()

