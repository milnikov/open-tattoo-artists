#!/usr/bin/env python3
"""
Heuristic "is this Instagram account a tattoo artist?" score.

Used by:
- create_artists_from_discovery_candidates.py (gate before creating an artist
  JSON from a graph candidate)
- prune_discovery_artists.py (retroactively delete junk auto-created artists)
- discover_instagram_graph.py (legacy single-script discovery)

The score in [0, 1] is the sum of weighted signals over candidate metadata:
- positive / negative keywords in handle + full_name + biography
- graph evidence (number of distinct already-known artists pointing at this
  handle via following or "similar accounts")
- follower count threshold
- non-empty media count
- private account penalty
- IG-verified bonus
"""

from __future__ import annotations


POSITIVE_TERMS = {
    "tattoo",
    "tattoos",
    "tattooer",
    "tattooist",
    "tattooartist",
    "ink",
    "inked",
    "fineline",
    "blackwork",
    "dotwork",
    "trad",
    "traditional",
    "irezumi",
    "tattooing",
}

NEGATIVE_TERMS = {
    "meme",
    "news",
    "media",
    "gamer",
    "gaming",
    "restaurant",
    "agency",
    "marketing",
    "crypto",
    "casino",
}


def tattoo_confidence(
    *,
    username: str,
    full_name: str | None,
    biography: str | None,
    evidence_count: int,
    follower_count: int | None,
    media_count: int | None,
    is_private: bool | None,
    is_verified: bool | None,
    min_followers: int = 1000,
) -> tuple[float, list[str]]:
    """Return ``(score, reasons)`` where score is clamped to [0, 1].

    ``reasons`` is a list of short human-readable strings explaining each
    contribution; useful for transparency in rejection reports.
    """
    reasons: list[str] = []
    score = 0.0
    text = " ".join([username or "", full_name or "", biography or ""]).lower()

    pos = sum(1 for t in POSITIVE_TERMS if t in text)
    neg = sum(1 for t in NEGATIVE_TERMS if t in text)
    if pos:
        add = min(0.45, pos * 0.12)
        score += add
        reasons.append(f"tattoo_keywords(+{add:.2f})")
    if neg:
        sub = min(0.4, neg * 0.12)
        score -= sub
        reasons.append(f"non_artist_keywords(-{sub:.2f})")

    if evidence_count:
        add = min(0.3, evidence_count * 0.06)
        score += add
        reasons.append(f"graph_evidence(+{add:.2f})")

    if follower_count is not None and follower_count >= min_followers:
        score += 0.15
        reasons.append(f"followers>={min_followers}(+0.15)")

    if media_count is not None and media_count >= 9:
        score += 0.08
        reasons.append("active_profile(+0.08)")

    if is_private is True:
        score -= 0.1
        reasons.append("private_account(-0.10)")

    if is_verified:
        score += 0.04
        reasons.append("verified(+0.04)")

    return max(0.0, min(1.0, score)), reasons
