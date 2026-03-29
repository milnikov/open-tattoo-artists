#!/usr/bin/env python3
"""
Restore `name` in data/artists/*.json from an older git revision without touching the rest
(instagram_enriched, tattoos, bio, etc.).

Use when Instagram enrichment overwrote good names with IG display names; compare current
file on disk to `git show <REF>:data/artists/<id>.json` and write back only when the old
name looks like a real catalog name and the current one looks corrupted.

Workflow (Mac or VM with full git history):
  1. Copy IDs list from VM: scp user@vm:~/Tattoo_artists/packages/scraper/tattooswizard_ig_enrich_ids.json packages/scraper/
  2. Find REF = last commit *before* the bad enrich started, e.g.:
       git log --oneline -20 --all | head
       git log -1 --format=%H --first-parent main~N
     or the parent of the first "chore: enrich" commit.
  3. Dry-run:
       PYTHONPATH=packages/scraper/src python3 packages/scraper/src/fix_artist_names_from_git_revision.py \\
         --ids-file packages/scraper/tattooswizard_ig_enrich_ids.json \\
         --git-ref REF \\
         --dry-run
  4. Apply: same without --dry-run

Requires a clean working tree for only the files you intend to change, or run from a branch
where you are OK writing data/artists.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path

from _repo_root import REPO_ROOT

from enrich_instagram_rapidapi import (
    _emoji_char_count,
    _instagram_display_is_clearly_junk,
    _looks_like_person_name,
)


def git_show_artist_json(repo: Path, git_ref: str, artist_id: str) -> dict | None:
    rel = f"data/artists/{artist_id}.json"
    try:
        proc = subprocess.run(
            ["git", "-C", str(repo), "show", f"{git_ref}:{rel}"],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0:
        return None
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        return None


@contextmanager
def old_artists_extract_dir(repo: Path, git_ref: str):
    """
    One `git archive` + tar extract of data/artists at git_ref (fast vs thousands of `git show`).
    Yields Path to the directory of *.json files (…/data/artists).
    """
    tmp = Path(tempfile.mkdtemp(prefix="fix_names_old_"))
    try:
        proc_git = subprocess.Popen(
            ["git", "-C", str(repo), "archive", git_ref, "data/artists"],
            stdout=subprocess.PIPE,
        )
        if proc_git.stdout is None:
            raise RuntimeError("git archive: no stdout")
        try:
            subprocess.run(
                ["tar", "-xf", "-", "-C", str(tmp)],
                stdin=proc_git.stdout,
                check=True,
            )
        finally:
            proc_git.stdout.close()
        if proc_git.wait() != 0:
            raise RuntimeError("git archive failed")
        yield tmp / "data" / "artists"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def should_restore_name(previous: str, current: str) -> bool:
    """True if we should set name back to *previous* from git."""
    p = (previous or "").strip()
    c = (current or "").strip()
    if p == c:
        return False
    prev_ok = _looks_like_person_name(p)
    curr_ok = _looks_like_person_name(c)
    if prev_ok and not curr_ok:
        return True
    if prev_ok and _instagram_display_is_clearly_junk(c):
        return True
    if prev_ok and _emoji_char_count(c) > 0:
        return True
    return False


def load_ids(path: Path) -> list[str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return [str(x) for x in data if x]
    raise SystemExit(f"Expected JSON array in {path}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Restore artist name field from git REF for IDs in a JSON list; leave rest of JSON unchanged."
    )
    parser.add_argument(
        "--ids-file",
        type=Path,
        required=True,
        help="JSON array of artist ids (e.g. tattooswizard_ig_enrich_ids.json)",
    )
    parser.add_argument(
        "--git-ref",
        type=str,
        required=True,
        help="Commit/tag/tree to read old files from (e.g. abc1237 or main~5)",
    )
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT, help="Git repo root (default: auto-detected)")
    parser.add_argument("--dry-run", action="store_true", help="Print changes only; do not write")
    parser.add_argument("--limit", type=int, default=None, help="Process at most N ids (for testing)")
    parser.add_argument(
        "--git-show-per-id",
        action="store_true",
        help="Slow: use one git show per artist (default: one git archive + tar of data/artists).",
    )
    args = parser.parse_args()

    repo = args.repo_root.resolve()
    ids_path = args.ids_file if args.ids_file.is_absolute() else repo / args.ids_file
    if not ids_path.is_file():
        print(f"ids-file not found: {ids_path}", file=sys.stderr)
        sys.exit(1)

    ids = load_ids(ids_path)
    if args.limit is not None:
        ids = ids[: args.limit]

    verify = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "--verify", args.git_ref],
        capture_output=True,
        text=True,
    )
    if verify.returncode != 0:
        print(f"Invalid --git-ref {args.git_ref!r}: {verify.stderr.strip()}", file=sys.stderr)
        sys.exit(1)

    resolved_ref = verify.stdout.strip()

    fixed = 0
    unchanged = 0
    no_git_file = 0
    skipped_heuristic = 0

    def run_ids_loop(old_dir: Path | None) -> None:
        nonlocal fixed, unchanged, no_git_file, skipped_heuristic
        for artist_id in ids:
            path = repo / "data" / "artists" / f"{artist_id}.json"
            if not path.is_file():
                print(f"  skip (missing on disk): {artist_id}", file=sys.stderr)
                continue
            if old_dir is not None:
                old_path = old_dir / f"{artist_id}.json"
                if not old_path.is_file():
                    no_git_file += 1
                    continue
                try:
                    old_doc = json.loads(old_path.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError):
                    no_git_file += 1
                    continue
            else:
                old_doc = git_show_artist_json(repo, resolved_ref, artist_id)
                if not old_doc:
                    no_git_file += 1
                    continue

            prev_name = old_doc.get("name") or ""
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            curr_name = data.get("name") or ""

            if not should_restore_name(prev_name, curr_name):
                if prev_name.strip() != curr_name.strip():
                    skipped_heuristic += 1
                unchanged += 1
                continue

            print(f"  {artist_id}: {curr_name!r} -> {prev_name!r}", flush=True)
            fixed += 1
            if not args.dry_run:
                data["name"] = prev_name
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)

    if args.git_show_per_id:
        run_ids_loop(None)
    else:
        print(f"Extracting data/artists @ {resolved_ref} (git archive) ...", file=sys.stderr, flush=True)
        try:
            with old_artists_extract_dir(repo, resolved_ref) as old_dir:
                if not old_dir.is_dir():
                    print("Extracted path missing; use --git-show-per-id.", file=sys.stderr)
                    sys.exit(1)
                run_ids_loop(old_dir)
        except (RuntimeError, subprocess.CalledProcessError) as e:
            print(f"git archive extract failed: {e}; retry with --git-show-per-id.", file=sys.stderr)
            sys.exit(1)

    verb = "Would fix" if args.dry_run else "Fixed"
    print(
        f"\nSummary: {verb}={fixed}, unchanged={unchanged}, "
        f"no file at ref={no_git_file}, differed but skipped by heuristic={skipped_heuristic}"
    )
    if args.dry_run and fixed:
        print("Run again without --dry-run to write.")


if __name__ == "__main__":
    main()
