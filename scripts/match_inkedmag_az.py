#!/usr/bin/env python3
"""Match Inked Mag A–Z article artists to data/indexes/artists.compact.json.

Article: https://inkedmag.com/original-news/an-a-z-guide-to-the-worlds-best-tattoo-artists

Refresh HTML, re-parse into docs/inkedmag_az_artists.json, then run this script.
"""
from __future__ import annotations

import html as html_lib
import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
COMPACT = REPO / "data/indexes/artists.compact.json"
ARTISTS_JSON = REPO / "docs/inkedmag_az_artists.json"
OUT = REPO / "docs/inkedmag_az_missing_artists.json"

STOP = {"tattoo", "tattoos", "ink", "art", "the", "studio", "shop"}

# Display name (article) -> artist id when automated matching is wrong or too fuzzy.
MANUAL_IDS: dict[str, str] = {
    "Bang Bang": "bangbangnyc",  # Keith McCurdy; studio account in catalog
    "Goldy": "zlatakolomoyskaya",
    "Q": "dongkyulee",
    "Mashkow, Alexey": "_mashkow_",
    "Ryan Ashley Malarkey": "ryanashley",
    "Castle Basas": "castlebasas",
    "O'Kharin, Sasha": "o_kharin",
    "Valentina Riabova": "valentinaryabova",  # article spelling; DB uses Ryabova
    "Khail Aitken": "khailtattooer",
    "Dmitriy Samohin": "dimitriysamohin",
    "Herzdame, Sarah": "herzdame",
}


def fold(s: str) -> str:
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


def name_variants(raw: str) -> list[str]:
    """Original, html-unescaped, and 'Last, First' -> 'First Last' if comma present."""
    t = html_lib.unescape(raw.strip())
    out = [t]
    if "," in t:
        left, right = [x.strip() for x in t.split(",", 1)]
        if left and right:
            out.append(f"{right} {left}")
    return list(dict.fromkeys(out))


def id_guesses_from_name(display: str) -> set[str]:
    g: set[str] = set()
    for variant in name_variants(display):
        fn = fold(variant)
        if not fn:
            continue
        parts = fn.split()
        g.add("".join(parts))
        g.add("_".join(parts))
        if len(parts) >= 2:
            g.add(parts[0] + "_" + parts[-1])
    return {x for x in g if x}


def extract_artists_from_html(html: str) -> list[str]:
    """Plain <h2>Name</h2> entries in article body (excludes Newsletter widget)."""
    names = []
    for m in re.finditer(r"<h2>([^<]+)</h2>", html):
        name = html_lib.unescape(m.group(1).strip())
        if name == "Newsletter":
            continue
        names.append(name)
    return names


def build_indexes(artists: list[dict]):
    id_set = {a["id"].lower() for a in artists}
    folded_rows = [(fold(a["name"]), a["id"]) for a in artists]
    id_to_fn = {aid: fn for fn, aid in folded_rows}

    name_to_ids: dict[str, list[str]] = defaultdict(list)
    for fn, aid in folded_rows:
        name_to_ids[fn].append(aid)

    token_to_ids: dict[str, set[str]] = defaultdict(set)
    for fn, aid in folded_rows:
        for t in fn.split():
            if len(t) > 2:
                token_to_ids[t].add(aid)

    return id_set, folded_rows, id_to_fn, name_to_ids, token_to_ids


def match_one(
    display: str,
    *,
    id_set: set[str],
    folded_rows: list[tuple[str, str]],
    id_to_fn: dict[str, str],
    name_to_ids: dict[str, list[str]],
    token_to_ids: dict[str, set[str]],
) -> tuple[str | None, str | None]:
    if display in MANUAL_IDS:
        mid = MANUAL_IDS[display]
        if mid.lower() in id_set:
            return "manual_id", mid

    match_type = match_id = None

    for guess in id_guesses_from_name(display):
        if guess in id_set:
            match_type, match_id = "id_guess", guess
            break

    if not match_type:
        for variant in name_variants(display):
            fn = fold(variant)
            if not fn:
                continue
            if fn in name_to_ids:
                ids = name_to_ids[fn]
                if len(ids) == 1:
                    match_type, match_id = "name_exact_fold", ids[0]
                elif len(ids) > 1:
                    match_type, match_id = "name_ambiguous", ids[0]
                break
            if len(fn) > 0:
                for db_fn, aid in folded_rows:
                    if fn == db_fn or (len(fn) > 6 and fn in db_fn):
                        match_type, match_id = "name_substring", aid
                        break
            if match_type:
                break

    if not match_type:
        fn = fold(name_variants(display)[0])
        if not fn:
            return match_type, match_id
        wt = [t for t in fn.split() if len(t) > 2 and t not in STOP]
        if wt:
            sets = [token_to_ids.get(t) for t in wt]
            sets = [s for s in sets if s]
            cand_ids: list[str] = []
            if sets:
                inter = sets[0].copy()
                for s in sets[1:]:
                    inter &= s
                cand_ids = list(inter)
            ok = []
            for aid in cand_ids:
                db_fn = id_to_fn.get(aid, "")
                if all(t in db_fn for t in wt):
                    ok.append(aid)
            if len(ok) == 1:
                match_type, match_id = "name_tokens", ok[0]
            elif len(ok) > 1:
                match_type, match_id = "tokens_ambiguous", ok[0]

    return match_type, match_id


def main() -> None:
    artists = json.loads(COMPACT.read_text(encoding="utf-8"))
    id_set, folded_rows, id_to_fn, name_to_ids, token_to_ids = build_indexes(artists)

    if len(sys.argv) > 1 and sys.argv[1] == "--parse-html":
        p = Path(sys.argv[2])
        names = extract_artists_from_html(p.read_text(encoding="utf-8", errors="replace"))
        ARTISTS_JSON.write_text(
            json.dumps(
                {
                    "source_url": "https://inkedmag.com/original-news/an-a-z-guide-to-the-worlds-best-tattoo-artists",
                    "extracted_note": "Parsed plain <h2>Name</h2> headings from downloaded HTML (excludes Newsletter widget).",
                    "artists": [{"name": n} for n in names],
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        print(f"wrote {len(names)} names -> {ARTISTS_JSON}")
        return

    payload = json.loads(ARTISTS_JSON.read_text(encoding="utf-8"))
    rows = payload["artists"]

    results: list[dict] = []
    for row in rows:
        display = row["name"]
        mt, mid = match_one(
            display,
            id_set=id_set,
            folded_rows=folded_rows,
            id_to_fn=id_to_fn,
            name_to_ids=name_to_ids,
            token_to_ids=token_to_ids,
        )
        results.append(
            {
                "name": display,
                "matched": mt is not None,
                "match_type": mt,
                "match_id": mid,
            }
        )

    matched = [r for r in results if r["matched"]]
    missing = [r for r in results if not r["matched"]]
    ambig = [r for r in results if r["match_type"] in ("name_ambiguous", "tokens_ambiguous")]

    out = {
        "source_url": "https://inkedmag.com/original-news/an-a-z-guide-to-the-worlds-best-tattoo-artists",
        "extracted_note": payload.get(
            "extracted_note",
            "See docs/inkedmag_az_artists.json. Regenerate: python3 scripts/match_inkedmag_az.py --parse-html /path/to/page.html",
        ),
        "database_note": "Compared to data/indexes/artists.compact.json. Order: MANUAL_IDS, guessed id from name, exact folded name (variants), substring (len>6), token intersection.",
        "caveat": "Bang Bang mapped to bangbangnyc; verify vs Keith McCurdy solo id if you split studio vs artist.",
        "scrape_queue_note": "packages/scraper/discovered_pages.json has no inkedmag.com URLs; this article is not a scrape source in-repo.",
        "counts": {
            "inked_az_artists": len(results),
            "matched": len(matched),
            "missing": len(missing),
            "flagged_ambiguous_match": len(ambig),
        },
        "match_type_breakdown": dict(Counter(r["match_type"] for r in matched)),
        "missing": [{"name": r["name"]} for r in sorted(missing, key=lambda x: fold(x["name"]))],
        "ambiguous_matches": [
            {"name": r["name"], "match_type": r["match_type"], "picked_id": r["match_id"]} for r in ambig
        ],
    }
    OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"artists={len(results)} matched={len(matched)} missing={len(missing)} ambig={len(ambig)} -> {OUT}")


if __name__ == "__main__":
    main()
