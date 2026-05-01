#!/usr/bin/env python3
"""Score and classify every instagram_graph artist; print histograms and samples.

Read-only. Doesn't change any data on disk."""

from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "packages" / "scraper" / "src"))

from _repo_root import repo_path  # noqa: E402
from tattoo_scoring import classify_account_type, tattoo_confidence  # noqa: E402


def _coerce_int(value):
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def main() -> None:
    artists_dir = repo_path("data", "artists")
    bins = [0.30, 0.40, 0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80, 0.90, 1.01]

    type_counter = Counter()
    bin_counts = Counter()
    bin_type_counts: dict[tuple[float, str], int] = Counter()
    samples_by_bin: dict[tuple[float, str], list[dict]] = defaultdict(list)
    studio_samples: list[dict] = []
    artist_samples: list[dict] = []
    keep_count = 0
    studio_count = 0
    junk_count = 0

    THRESHOLD = 0.40
    total = 0
    skipped = 0

    for path in sorted(artists_dir.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(data, dict):
            continue
        discovery = data.get("discovery") if isinstance(data.get("discovery"), dict) else {}
        if discovery.get("source") != "instagram_graph":
            skipped += 1
            continue

        ig = data.get("instagram_enriched") if isinstance(data.get("instagram_enriched"), dict) else {}
        bio = data.get("bio") if isinstance(data.get("bio"), str) else None
        full_name = data.get("name") if isinstance(data.get("name"), str) else None
        score, _reasons = tattoo_confidence(
            username=path.stem.lower(),
            full_name=full_name,
            biography=bio,
            evidence_count=_coerce_int(discovery.get("evidence_count")) or 0,
            follower_count=_coerce_int(ig.get("follower_count")),
            media_count=_coerce_int(ig.get("media_count")),
            is_private=ig.get("is_private") if isinstance(ig.get("is_private"), bool) else None,
            is_verified=ig.get("is_verified") if isinstance(ig.get("is_verified"), bool) else None,
        )
        kind, reasons = classify_account_type(
            username=path.stem.lower(),
            full_name=full_name,
            biography=bio,
        )
        total += 1
        type_counter[kind] += 1

        # Categorisation under proposed final policy.
        if score < THRESHOLD:
            junk_count += 1
        elif kind == "studio":
            studio_count += 1
            if len(studio_samples) < 8:
                studio_samples.append({
                    "h": path.stem, "s": round(score, 3), "k": kind,
                    "rsn": ",".join(reasons),
                    "bio": (bio or "")[:90].replace("\n", " "),
                })
        else:
            keep_count += 1
            if len(artist_samples) < 8 and bio:
                artist_samples.append({
                    "h": path.stem, "s": round(score, 3), "k": kind,
                    "bio": (bio or "")[:90].replace("\n", " "),
                })

        for upper in bins:
            if score < upper:
                bin_counts[upper] += 1
                bin_type_counts[(upper, kind)] += 1
                if len(samples_by_bin[(upper, kind)]) < 2:
                    samples_by_bin[(upper, kind)].append({
                        "h": path.stem, "s": round(score, 3), "k": kind,
                        "rsn": ",".join(reasons) if reasons else "-",
                        "bio": (bio or "")[:80].replace("\n", " "),
                    })
                break

    print(f"Total instagram_graph artists scored: {total} (skipped non-discovery: {skipped})")
    print(f"Type counts overall: {dict(type_counter)}")
    print()
    print(f"Proposed policy: prune if score < {THRESHOLD}, then quarantine type=='studio'")
    print(f"  -> junk         (score<{THRESHOLD}):       {junk_count}")
    print(f"  -> studios      (score>={THRESHOLD}, kind=studio): {studio_count}")
    print(f"  -> kept artists (score>={THRESHOLD}, kind!=studio): {keep_count}")
    print()
    print("Histogram by score x kind:")
    print(f"  {'bin':>8} {'total':>7} {'studio':>7} {'artist':>7} {'unknown':>7}")
    for upper in bins:
        c = bin_counts.get(upper, 0)
        s = bin_type_counts.get((upper, "studio"), 0)
        a = bin_type_counts.get((upper, "artist"), 0)
        u = bin_type_counts.get((upper, "unknown"), 0)
        label = f"<{upper:.2f}" if upper <= 1.0 else "<=1.00"
        print(f"  {label:>8} {c:>7} {s:>7} {a:>7} {u:>7}")
    print()
    print("Sample STUDIOS that score>=0.40 (would be quarantined):")
    for r in studio_samples:
        print(f"  @{r['h']:<28} score={r['s']:<5} reason={r['rsn']:<35}  bio={r['bio']!r}")
    print()
    print("Sample ARTISTS that score>=0.40 (would be kept):")
    for r in artist_samples:
        print(f"  @{r['h']:<28} score={r['s']:<5}  bio={r['bio']!r}")


if __name__ == "__main__":
    main()
