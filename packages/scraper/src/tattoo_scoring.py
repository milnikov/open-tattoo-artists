#!/usr/bin/env python3
"""
Heuristic "is this Instagram account a tattoo artist?" score.

Used by:
- create_artists_from_discovery_candidates.py (gate before creating an artist
  JSON from a graph candidate)
- prune_discovery_artists.py (retroactively delete junk auto-created artists)
- discover_instagram_graph.py (legacy single-script discovery)

The score in [0, 1] is the sum of weighted signals over candidate metadata:
- positive tattoo keywords **only in full_name + biography** (Instagram display
  name + bio). Usernames are ignored for positive keyword matching so a handle
  like ``blackwork_joe`` alone cannot pass the gate. ``@mentions`` are stripped
  from the bio before matching so e.g. ``@someonetattoo`` does not inject a
  false ``tattoo`` hit.
- negative keywords in username + full_name + biography
- graph evidence, follower threshold, media activity, and IG-verified bonuses
  apply **only when** at least one positive tattoo term appears in name+bio
- private account penalty (always applies)

In addition to ``tattoo_confidence`` we expose ``classify_account_type`` which
returns one of ``"artist"``, ``"studio"`` or ``"unknown"`` based on a separate
set of studio/shop markers (username, biography, multiple @-mentions, opening
hours, etc.). This is used by prune_discovery_artists.py to keep only
individual artists in ``data/artists/``.
"""

from __future__ import annotations

import re


POSITIVE_TERMS = {
    # English (substring matches: tattoo / tattoos / tattooer / tattooist /
    # tattooartist / tattooing / tattooed / tattooshop, etc.)
    "tattoo",
    "tatts",
    "ink",
    "inked",
    "fineline",
    "blackwork",
    "dotwork",
    "trad",
    "traditional",
    "irezumi",
    "needle",
    "skinart",
    # Portuguese: tatuagem, tatuagens
    "tatuag",
    # PT/ES: tatuador, tatuadora
    "tatuad",
    # Spanish: tatuaje, tatuajes
    "tatuaj",
    # Italian: tatuaggio, tatuaggi
    "tatuagg",
    # IT: tatuatore, tatuatrice; ES tatuatura
    "tatuat",
    # French: tatouage, tatoueur, tatoueuse
    "tatouage",
    "tatoueur",
    "tatoueu",
    # German: tätowierung, tätowierer (with/without umlaut)
    "tätow",
    "tatow",
    # Japanese romaji
    "horishi",
    "horimono",
    # Turkish
    "dövme",
    "dovme",
    # Russian transliteration: tatuirovka
    "tatuir",
    # Polish: tatuaż / tatuażysta
    "tatuaż",
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

_MENTION_RE = re.compile(r"@[a-zA-Z0-9_.]{2,}")


def _name_bio_for_matching(full_name: str | None, biography: str | None) -> str:
    """Lowercased ``full_name`` + biography with Instagram @handles removed."""
    bio = biography or ""
    bio = _MENTION_RE.sub(" ", bio)
    return f"{full_name or ''}\n{bio}".lower()


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
    min_followers: int = 3000,
) -> tuple[float, list[str]]:
    """Return ``(score, reasons)`` where score is clamped to [0, 1].

    ``reasons`` is a list of short human-readable strings explaining each
    contribution; useful for transparency in rejection reports.
    """
    reasons: list[str] = []
    score = 0.0
    name_bio = _name_bio_for_matching(full_name, biography)
    text_all = " ".join([username or "", full_name or "", biography or ""]).lower()

    pos_name_bio = sum(1 for t in POSITIVE_TERMS if t in name_bio)
    neg = sum(1 for t in NEGATIVE_TERMS if t in text_all)
    if pos_name_bio:
        add = min(0.45, pos_name_bio * 0.12)
        score += add
        reasons.append(f"name_bio_keywords(+{add:.2f})")
    if neg:
        sub = min(0.4, neg * 0.12)
        score -= sub
        reasons.append(f"non_artist_keywords(-{sub:.2f})")

    if pos_name_bio:
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

        if is_verified:
            score += 0.04
            reasons.append("verified(+0.04)")
    else:
        reasons.append("no_name_bio_tattoo_signal(structural_boosts_skipped)")

    if is_private is True:
        score -= 0.1
        reasons.append("private_account(-0.10)")

    return max(0.0, min(1.0, score)), reasons


# --- Studio / shop classifier -------------------------------------------------
# rather than an individual artist.
STUDIO_USERNAME_MARKERS = (
    "tattooshop",
    "tattoostudio",
    "tattoo_studio",
    "tattoo.studio",
    "tattooatelier",
    "studio",
    "estudio",
    "estúdio",
    "atelier",
    "parlour",
    "parlor",
    "tatuaria",
    "tatuería",
    "tatueria",
    "inkstudio",
    "ink.studio",
    "ink_studio",
    "tattoolab",
    "tattoo_lab",
    "tattoo.lab",
    "tattoohouse",
    "tattoo.house",
    "tattoo_house",
    "tattoocollective",
    "tattoo.collective",
    "tattoo_collective",
    "tattooclub",
    "tattoogallery",
    "salon",
    "salão",
    "saloon",
)

# Substring markers in the *biography* (case-insensitive) that suggest a
# shop / collective rather than an individual artist.
STUDIO_BIO_MARKERS = (
    "tattoo studio",
    "tattoostudio",
    "tattoo shop",
    "tattooshop",
    "tattoo parlour",
    "tattoo parlor",
    "tattoo atelier",
    "estudio de tatuaje",
    "estúdio de tatuagem",
    "estudio de tatuagem",
    "tatuagens em",
    "tatuajes en",
    "tatouage studio",
    "tatuator studio",
    "studio di tatuaggi",
    "salão de tatuagem",
    "guest spot",
    "guest spots",
    "guests welcome",
    "walk-ins",
    "walkins welcome",
    "walk ins welcome",
    "all artists",
    "our artists",
    "resident artist",
    "resident artists",
    "agende seu hor",
    "agendamento online",
    "marca a tua",
    "book your appointment",
    "we are open",
    "located in",
)

# Compiled patterns used to detect shop-like signals such as opening hours,
# phone numbers and full street addresses in biographies.
_HOURS_PATTERNS = [
    re.compile(r"\b\d{1,2}:\d{2}\s*[-–]\s*\d{1,2}:\d{2}\b"),
    re.compile(r"\b\d{1,2}\s*h\s*[-–às]+\s*\d{1,2}\s*h\b", re.IGNORECASE),
    re.compile(
        r"\b(mon|tue|wed|thu|fri|sat|sun|"
        r"seg|ter|qua|qui|sex|sab|dom|"
        r"lun|mar|mié|mier|jue|vie|sáb|"
        r"mo|di|mi|fr|sa|so|"
        r"lu|ma|me|je|ve|sa|di"
        r")\b\s*[-–/]\s*"
        r"(mon|tue|wed|thu|fri|sat|sun|"
        r"seg|ter|qua|qui|sex|sab|dom|"
        r"lun|mar|mié|jue|vie|sáb|"
        r"mo|di|mi|fr|sa|so|"
        r"lu|ma|me|je|ve|sa|di)",
        re.IGNORECASE,
    ),
]


def classify_account_type(
    *,
    username: str,
    full_name: str | None,
    biography: str | None,
) -> tuple[str, list[str]]:
    """Return ``(label, reasons)`` where label is ``"studio"``, ``"artist"``
    or ``"unknown"``. ``reasons`` is a list of short tags explaining the
    decision.

    Heuristics: any single strong studio marker (username substring, bio
    substring, 3+ @-mentions, or opening-hours pattern) classifies the account
    as a studio. Otherwise it is left as ``"artist"`` or ``"unknown"``.
    """
    reasons: list[str] = []
    uname = (username or "").lower()
    name = (full_name or "").lower()
    bio = (biography or "").lower()

    for marker in STUDIO_USERNAME_MARKERS:
        if marker in uname or marker in name:
            reasons.append(f"username_marker:{marker}")
            return "studio", reasons

    for marker in STUDIO_BIO_MARKERS:
        if marker in bio:
            reasons.append(f"bio_marker:{marker}")
            return "studio", reasons

    if bio:
        mentions = _MENTION_RE.findall(bio)
        if len(mentions) >= 3:
            reasons.append(f"bio_mentions:{len(mentions)}")
            return "studio", reasons

        for pat in _HOURS_PATTERNS:
            if pat.search(bio):
                reasons.append("opening_hours")
                return "studio", reasons

    if not bio:
        return "unknown", ["empty_bio"]
    return "artist", reasons
