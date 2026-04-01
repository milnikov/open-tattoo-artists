#!/usr/bin/env python3
"""Match World Tattoo Gallery /artists/all snapshot to data/indexes/artists.compact.json.

Refresh the HTML snapshot (run from repo root):
  curl -sSL -A 'Mozilla/5.0' 'https://www.worldtattoogallery.com/artists/all' -o /tmp/wtg.html
Then re-parse slug + display name into docs/worldtattoogallery_artists_page.json (regex on
  artist URLs and strong display names in the card markup
) and run this script again.
"""
from __future__ import annotations

import json
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
COMPACT = REPO / "data/indexes/artists.compact.json"
WTG_JSON = REPO / "docs/worldtattoogallery_artists_page.json"
OUT = REPO / "docs/worldtattoogallery_missing_artists.json"

STOP = {"tattoo", "tattoos", "ink", "art", "the", "studio", "shop"}


def fold(s: str) -> str:
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


def slug_id_candidates(slug: str) -> set[str]:
    s = slug.lower()
    return {s.replace("-", ""), s.replace("-", "_")}


def main() -> None:
    artists = json.loads(COMPACT.read_text(encoding="utf-8"))
    id_set = {a["id"].lower() for a in artists}
    folded_rows = [(fold(a["name"]), a["id"]) for a in artists]
    id_to_fn = {aid: fn for fn, aid in folded_rows}

    name_to_ids: dict[str, list[str]] = defaultdict(list)
    for fn, aid in folded_rows:
        name_to_ids[fn].append(aid)

    # inverted index: token -> ids (for token match candidates only)
    token_to_ids: dict[str, set[str]] = defaultdict(set)
    for fn, aid in folded_rows:
        for t in fn.split():
            if len(t) > 2:
                token_to_ids[t].add(aid)

    wtg = json.loads(WTG_JSON.read_text(encoding="utf-8"))["artists"]

    def name_token_candidates(wtg_name: str) -> list[str]:
        wt = [t for t in fold(wtg_name).split() if len(t) > 2 and t not in STOP]
        if not wt:
            return []
        sets = [token_to_ids.get(t) for t in wt]
        sets = [s for s in sets if s]
        if not sets:
            return []
        inter = sets[0].copy()
        for s in sets[1:]:
            inter &= s
        return list(inter)

    results: list[dict] = []
    for row in wtg:
        slug, name = row["slug"], row["name"]
        match_type = match_id = None

        for c in slug_id_candidates(slug):
            if c in id_set:
                match_type, match_id = "id_from_slug", c
                break

        fn = fold(name)
        if not match_type and fn in name_to_ids:
            ids = name_to_ids[fn]
            if len(ids) == 1:
                match_type, match_id = "name_exact_fold", ids[0]
            elif len(ids) > 1:
                match_type, match_id = "name_ambiguous", ids[0]

        if not match_type and len(fn) > 0:
            for db_fn, aid in folded_rows:
                if fn == db_fn or (len(fn) > 6 and fn in db_fn):
                    match_type, match_id = "name_substring", aid
                    break

        if not match_type:
            wt = [t for t in fn.split() if len(t) > 2 and t not in STOP]
            if wt:
                cand_ids = name_token_candidates(name)
                ok = []
                for aid in cand_ids:
                    db_fn = id_to_fn.get(aid, "")
                    if all(t in db_fn for t in wt):
                        ok.append(aid)
                if len(ok) == 1:
                    match_type, match_id = "name_tokens", ok[0]
                elif len(ok) > 1:
                    match_type, match_id = "tokens_ambiguous", ok[0]

        results.append(
            {
                "slug": slug,
                "name": name,
                "matched": match_type is not None,
                "match_type": match_type,
                "match_id": match_id,
            }
        )

    matched = [r for r in results if r["matched"]]
    missing = [r for r in results if not r["matched"]]
    ambig = [r for r in results if r["match_type"] in ("name_ambiguous", "tokens_ambiguous")]

    out = {
        "source_url": "https://www.worldtattoogallery.com/artists/all",
        "extracted_note": "535 artist cards from HTML snapshot; see docs/worldtattoogallery_artists_page.json. Regenerate via this script after updating the snapshot.",
        "database_note": "Compared to data/indexes/artists.compact.json. Match order: id == slug without hyphens (or underscores), exact folded name, substring (len>6), token intersection with all tokens in DB folded name.",
        "caveat": "Token/substring matches can rarely be wrong-person; id_from_slug is strongest.",
        "counts": {
            "world_tattoo_gallery_artists": len(results),
            "matched": len(matched),
            "missing": len(missing),
            "flagged_ambiguous_match": len(ambig),
        },
        "match_type_breakdown": dict(Counter(r["match_type"] for r in matched)),
        "missing": [{"slug": r["slug"], "name": r["name"]} for r in sorted(missing, key=lambda x: fold(x["name"]))],
        "ambiguous_matches": [
            {"slug": r["slug"], "name": r["name"], "match_type": r["match_type"], "picked_id": r["match_id"]}
            for r in ambig
        ],
    }
    OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(
        f"artists={len(results)} matched={len(matched)} missing={len(missing)} ambig={len(ambig)} -> {OUT}"
    )


if __name__ == "__main__":
    main()
