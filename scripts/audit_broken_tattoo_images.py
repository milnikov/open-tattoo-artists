#!/usr/bin/env python3
"""Count artists whose first tattoo thumb is missing on the image CDN (HTTP != 200)."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
ARTISTS_DIR = REPO_ROOT / "data" / "artists"
OLD_R2 = "https://pub-4fe1c204aa1d4ce08395d234befdc73f.r2.dev"
CDN = "https://img.thetattoo.world"


def normalize_url(url: str) -> str:
    if not url:
        return ""
    return url.replace(OLD_R2, CDN)


def http_get_code(url: str) -> int:
    if not url.startswith("http"):
        return -1
    try:
        r = subprocess.run(
            [
                "/usr/bin/curl",
                "-s",
                "-o",
                "/dev/null",
                "-w",
                "%{http_code}",
                "--max-time",
                "12",
                url,
            ],
            capture_output=True,
            text=True,
            timeout=15,
        )
        return int(r.stdout.strip() or "0")
    except Exception:
        return 0


def load_work() -> tuple[list[tuple[str, str, str]], dict[str, int]]:
    """Returns ([(artist_id, url, image_id), ...], stats)."""
    work: list[tuple[str, str, str]] = []
    stats = {
        "json_files": 0,
        "parse_errors": 0,
        "no_tattoos": 0,
        "no_thumb_url": 0,
    }
    for p in sorted(ARTISTS_DIR.glob("*.json")):
        stats["json_files"] += 1
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            stats["parse_errors"] += 1
            continue
        tattoos = d.get("tattoos") or []
        if not tattoos:
            stats["no_tattoos"] += 1
            continue
        t0 = tattoos[0]
        thumb = normalize_url(str(t0.get("image_thumb") or ""))
        if not thumb.startswith("http"):
            stats["no_thumb_url"] += 1
            continue
        work.append((d.get("id") or p.stem, thumb, str(t0.get("image_id") or "")))
    return work, stats


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workers", type=int, default=40)
    parser.add_argument(
        "--out",
        type=Path,
        default=REPO_ROOT / "packages/scraper/audit_broken_tattoo_images.json",
        help="Write broken artist ids + URL to this JSON",
    )
    args = parser.parse_args()

    work, stats = load_work()
    total_with_check = len(work)
    print(f"Artists to check (first tattoo thumb): {total_with_check}", flush=True)
    print(f"  no tattoos: {stats['no_tattoos']}", flush=True)
    print(f"  no thumb URL: {stats['no_thumb_url']}", flush=True)

    broken: list[dict] = []
    ok = 0
    other_fail = 0

    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        futures = {pool.submit(http_get_code, url): (aid, url, iid) for aid, url, iid in work}
        done = 0
        for fut in as_completed(futures):
            aid, url, iid = futures[fut]
            code = fut.result()
            done += 1
            if done % 500 == 0:
                print(f"  ... {done}/{total_with_check}", flush=True)
            if code == 200:
                ok += 1
            else:
                if code == 404:
                    broken.append({"id": aid, "http": code, "image_id": iid, "image_thumb": url})
                else:
                    other_fail += 1
                    broken.append(
                        {
                            "id": aid,
                            "http": code,
                            "image_id": iid,
                            "image_thumb": url,
                            "note": "non-404 failure",
                        }
                    )

    broken_404 = sum(1 for b in broken if b.get("http") == 404)
    print("", flush=True)
    print("=== Summary ===", flush=True)
    print(f"Artists with at least one tattoo: {total_with_check + stats['no_tattoos']} (approx)", flush=True)
    print(f"Checked (have thumb URL): {total_with_check}", flush=True)
    print(f"OK (first thumb HTTP 200): {ok}", flush=True)
    print(f"Broken (first thumb HTTP 404): {broken_404}", flush=True)
    print(f"Other non-200: {other_fail}", flush=True)
    if total_with_check:
        print(f"Broken share: {100.0 * broken_404 / total_with_check:.2f}%", flush=True)

    report = {
        "checked": total_with_check,
        "ok": ok,
        "broken_404": broken_404,
        "other_non_200": other_fail,
        "stats": stats,
        "broken": broken,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {args.out}", flush=True)

    hidden_path = REPO_ROOT / "data" / "indexes" / "hidden_missing_cdn_images.json"
    hidden_ids = sorted({b["id"] for b in broken if b.get("http") == 404})
    hidden_doc = {
        "schema_version": 1,
        "reason": "First tattoo thumbnail HTTP 404 on img.thetattoo.world.",
        "audited_at": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "artist_ids": hidden_ids,
    }
    hidden_path.write_text(
        json.dumps(hidden_doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"Wrote {hidden_path} ({len(hidden_ids)} ids)", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
