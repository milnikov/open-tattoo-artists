#!/usr/bin/env python3
"""
Enrich artist data via RapidAPI Instagram Scraper Stable API.
Default: ig_get_fb_profile_v3.php (one call per artist; returns full profile including biography).
  1) User profile (v3: bio, stats, profile pic)
  2) Following list (paginated)
  3) For accounts with >1000 followers: 30 posts (get_ig_user_posts.php)

When --update-artists (default): updates data/artists/*.json with:
  - updated_at, name, bio (from Instagram), instagram_enriched (id, follower_count, profile_pic_url (R2), following)
  - Profile pic + up to 30 post images (from get_ig_user_posts) uploaded to R2 unless --no-r2.

API key from env RAPIDAPI_KEY or config rapidapi_key. Run from repo root.
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import requests

from _repo_root import repo_path

# Default endpoint paths (override in config.yaml if your subscription uses different paths)
BASE_URL = "https://instagram-scraper-stable-api.p.rapidapi.com"
# v3 returns full profile including biography; use POST. Hover (GET) returns user_data + user_posts but no bio.
DEFAULT_ENDPOINT_USER_INFO = "ig_get_fb_profile_v3.php"
DEFAULT_ENDPOINT_FOLLOWING = "get_ig_user_followers_v2.php"
DEFAULT_ENDPOINT_POSTS = "get_ig_user_posts.php"

DEFAULT_HEADERS = {
    "x-rapidapi-host": "instagram-scraper-stable-api.p.rapidapi.com",
    "Content-Type": "application/x-www-form-urlencoded",
}

ENRICH_STATE_FILE = "packages/scraper/enrich_instagram_state.json"
EXIT_ALL_DONE = 2


def load_config() -> dict | None:
    """Load config.yaml from packages/scraper/ if present."""
    import yaml
    config_path = repo_path("packages", "scraper", "config.yaml")
    if not config_path.exists():
        return None
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_headers(api_key: str) -> dict:
    return {
        **DEFAULT_HEADERS,
        "x-rapidapi-key": api_key,
    }


def extract_username_from_url(url: str) -> str | None:
    if not url:
        return None
    url = url.strip().rstrip("/")
    m = re.match(r"https?://(?:www\.)?instagram\.com/([^/?]+)/?", url)
    return m.group(1) if m else (url if not url.startswith("http") else None)


def load_artists_with_instagram(
    data_artists_dir: Path,
    only_ids: set[str] | None = None,
) -> list[tuple[str, str]]:
    """Return [(artist_id, ig_username), ...] sorted by artist_id, only those with links.instagram.
    If only_ids is set, only include artists whose id is in that set (e.g. hidden artists for --only-ids-file).
    """
    out = []
    for p in sorted(data_artists_dir.glob("*.json")):
        artist_id = p.stem
        if only_ids is not None and artist_id not in only_ids:
            continue
        try:
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
            links = data.get("links") or {}
            ig = links.get("instagram") or ""
            username = extract_username_from_url(ig)
            if username:
                out.append((artist_id, username))
        except (json.JSONDecodeError, KeyError):
            continue
    return out


def load_id_set_from_file(path: Path) -> set[str]:
    """Load set of artist IDs from JSON array or text file (one id per line)."""
    with open(path, "r", encoding="utf-8") as f:
        raw = f.read().strip()
    if not raw:
        return set()
    if raw.startswith("["):
        data = json.loads(raw)
        return set(str(x) for x in data if x)
    return set(line.strip() for line in raw.splitlines() if line.strip())


def load_enrich_state() -> dict:
    path = repo_path(ENRICH_STATE_FILE)
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            d = json.load(f)
        return {
            "completed_ids": set(d.get("completed_ids", [])),
            "last_index": d.get("last_index", -1),
        }
    return {"completed_ids": set(), "last_index": -1}


def save_enrich_state(completed_ids: set, last_index: int) -> None:
    path = repo_path(ENRICH_STATE_FILE)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"completed_ids": sorted(completed_ids), "last_index": last_index}, f, indent=2)


def artist_already_enriched(artist_path: Path) -> bool:
    if not artist_path.exists():
        return False
    try:
        with open(artist_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return "instagram_enriched" in data
    except (json.JSONDecodeError, KeyError):
        return False


def load_usernames_from_input(path: Path) -> list[str]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    usernames = []
    seen = set()
    for raw in data.get("handles", data.get("urls", data.get("artists", []))):
        if isinstance(raw, str):
            u = extract_username_from_url(raw)
        else:
            u = None
        if u and u not in seen:
            seen.add(u)
            usernames.append(u)
    return usernames


def fetch_user_info(
    api_key: str, username: str, posts_count: int = 3, endpoint: str | None = None
) -> dict | None:
    """Fetch user profile. v3 (ig_get_fb_profile_v3.php) uses POST and returns biography; hover uses GET and returns user_posts."""
    path = endpoint or DEFAULT_ENDPOINT_USER_INFO
    url = f"{BASE_URL}/{path}"
    use_post = "v3" in path or path == "ig_get_fb_profile_v3.php"
    try:
        if use_post:
            r = requests.post(
                url,
                data={"username_or_url": username},
                headers=get_headers(api_key),
                timeout=30,
            )
        else:
            r = requests.get(
                url,
                params={"username_or_url": username},
                headers=get_headers(api_key),
                timeout=30,
            )
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"  [user_info] {username}: {e}", file=sys.stderr)
        return None


def fetch_following_page(
    api_key: str,
    username: str,
    start_from: str | None = None,
    endpoint: str | None = None,
    pagination_param: str = "start_from",
) -> dict | None:
    """POST to followers/following endpoint. amount=50 (max per page). Pagination via start_from or max_id."""
    path = endpoint or DEFAULT_ENDPOINT_FOLLOWING
    url = f"{BASE_URL}/{path}"
    payload = {
        "username_or_url": username,
        "data": "following",
        "amount": "50",
    }
    # First page: 0 or omit; next pages: token from response (v2 may use max_id)
    if start_from is not None:
        payload[pagination_param] = start_from
    else:
        payload[pagination_param] = "0"
    try:
        r = requests.post(
            url,
            data=payload,
            headers=get_headers(api_key),
            timeout=30,
        )
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"  [following] {username}: {e}", file=sys.stderr)
        return None


def fetch_user_posts(
    api_key: str,
    username: str,
    amount: int = 30,
    endpoint: str | None = None,
    pagination_token: str | None = None,
) -> tuple[list, str | None]:
    """
    POST get_ig_user_posts.php: username_or_url, amount, optional pagination_token.
    Returns (list of post objects, next_pagination_token or None).
    """
    path = endpoint or DEFAULT_ENDPOINT_POSTS
    url = f"{BASE_URL}/{path}"
    payload = {"username_or_url": username, "amount": str(amount)}
    if pagination_token:
        payload["pagination_token"] = pagination_token
    try:
        r = requests.post(
            url,
            data=payload,
            headers=get_headers(api_key),
            timeout=60,
        )
        r.raise_for_status()
        data = r.json()
        # API shape: {"posts": [{"node": {..., "image_versions2": {"candidates": [{"url": "..."}]}}}], "pagination_token": "..."}
        posts = (
            data.get("posts")
            or data.get("items")
            or data.get("edges")
            or []
        )
        if not posts and isinstance(data.get("data"), dict):
            inner = data["data"]
            posts = (
                inner.get("posts")
                or inner.get("items")
                or inner.get("edges")
                or (inner.get("edge_owner_to_timeline_media") or {}).get("edges")
                or []
            )
        if not posts and isinstance(data.get("data"), list):
            posts = data["data"]
        if isinstance(posts, dict):
            posts = posts.get("posts") or posts.get("items") or posts.get("edges") or []
        if not isinstance(posts, list):
            posts = []
        # If items are [{node: {...}, ...}], flatten to nodes for URL extraction
        if posts and isinstance(posts[0], dict) and "node" in posts[0] and "node" not in (posts[0].get("node") or {}):
            posts = [p.get("node") for p in posts if p.get("node")]
        next_token = (
            data.get("pagination_token")
            or data.get("next_max_id")
            or data.get("next_cursor")
        )
        return posts, next_token
    except Exception as e:
        print(f"  [posts] {username}: {e}", file=sys.stderr)
        return [], None


def _extract_image_url_from_post(post: dict) -> str | None:
    """Extract first image URL from a post (node). Handles image_versions2.candidates, carousel_media[0], display_url, etc."""
    if not isinstance(post, dict):
        return None
    node = post.get("node") or post
    if not node:
        return None

    def _url_from_candidates(candidates: list) -> str | None:
        if not candidates:
            return None
        c = candidates[0]
        if isinstance(c, dict):
            return c.get("url") or c.get("image_url")
        if isinstance(c, str) and c.startswith("http"):
            return c
        return None

    # Direct URL fields
    for key in ("display_url", "thumbnail_src", "image_url", "url", "thumbnail"):
        val = node.get(key)
        if isinstance(val, str) and val.startswith("http"):
            return val
    # image_versions2.candidates (main and carousel cover)
    cands = (node.get("image_versions2") or {}).get("candidates") or []
    if not cands:
        cands = node.get("images") or []
    url = _url_from_candidates(cands)
    if url:
        return url
    # Carousel: first media item (API may put images only in carousel_media)
    for item in (node.get("carousel_media") or [])[:1]:
        if not isinstance(item, dict):
            continue
        cands = (item.get("image_versions2") or {}).get("candidates") or []
        url = _url_from_candidates(cands)
        if url:
            return url
    return None


def fetch_up_to_30_post_image_urls(
    api_key: str,
    username: str,
    endpoint: str | None = None,
) -> list[str]:
    """Fetch up to 30 posts and return list of image URLs (order preserved)."""
    all_urls = []
    token = None
    while len(all_urls) < 30:
        posts, token = fetch_user_posts(
            api_key, username, amount=30, endpoint=endpoint, pagination_token=token
        )
        for p in posts:
            url = _extract_image_url_from_post(p)
            if url and url not in all_urls:
                all_urls.append(url)
            if len(all_urls) >= 30:
                break
        if not token or len(posts) < 30:
            break
        time.sleep(0.5)
    return all_urls[:30]


def _extract_following_list_from_page(page: dict) -> list:
    """Extract list of users from one API response (v1, v2, or nested)."""
    users = (
        page.get("users")
        or page.get("following")
        or page.get("followers")
        or page.get("items")
        or page.get("list")
        or []
    )
    data = page.get("data")
    if isinstance(data, dict):
        users = (
            users
            or data.get("following")
            or data.get("users")
            or data.get("followers")
            or data.get("items")
            or data.get("list")
            or []
        )
    elif isinstance(data, list):
        users = users or data
    return users if isinstance(users, list) else []


def _get_next_page_token(page: dict) -> str | None:
    """Get pagination token for next page (v1/v2 use different keys)."""
    return (
        page.get("next_start_from")
        or page.get("next_max_id")
        or page.get("next_cursor")
        or page.get("cursor")
        or (page.get("pagination") or {}).get("next_max_id")
        or (page.get("pagination") or {}).get("next_cursor")
    )


def _normalize_following_to_usernames(users: list) -> list[str]:
    """Convert list of user objects to list of username strings."""
    out = []
    for u in users:
        if isinstance(u, str):
            out.append(u)
        elif isinstance(u, dict):
            username = (
                u.get("username")
                or (u.get("user") or {}).get("username")
                or u.get("user_name")
            )
            if username:
                out.append(username)
    return out


def fetch_all_following(
    api_key: str,
    username: str,
    following_count: int | None,
    endpoint: str | None = None,
    pagination_param: str = "start_from",
) -> list[str]:
    """Return list of usernames the user is following (50 per page, paginated)."""
    all_users = []
    start_from = None  # first page
    while True:
        page = fetch_following_page(
            api_key,
            username,
            start_from=start_from,
            endpoint=endpoint,
            pagination_param=pagination_param,
        )
        if not page:
            break
        raw = _extract_following_list_from_page(page)
        usernames = _normalize_following_to_usernames(raw)
        all_users.extend(usernames)
        next_token = _get_next_page_token(page)
        if next_token is not None:
            start_from = next_token
        elif len(raw) >= 50:
            # No token in response; use offset for next page (50 per request)
            start_from = str(len(all_users))
        else:
            break
        time.sleep(0.5)
    return all_users


def _extract_user_data_and_follower_count(info: dict) -> tuple[dict, int]:
    """
    Extract user object and follower_count from first API response (ig_get_fb_profile_hover etc).
    Handles: user_data, data, user, data.user, graphql.user, and edge_followed_by.count for count.
    """
    # Try to get a user-like object
    user_data = (
        info.get("user_data")
        or info.get("data")
        or info.get("user")
        or info
    )
    # If data is a dict with a nested "user", use it (e.g. { "data": { "user": {...} } })
    if isinstance(user_data, dict):
        nested = user_data.get("user") or user_data.get("user_data")
        if isinstance(nested, dict) and (nested.get("username") is not None or nested.get("follower_count") is not None or nested.get("pk") is not None):
            user_data = nested
    if isinstance(info.get("graphql"), dict) and isinstance(info["graphql"].get("user"), dict):
        user_data = info["graphql"]["user"]

    # Follower count: direct or GraphQL edge_followed_by.count or "followers" (some API variants)
    follower_count = user_data.get("follower_count") if isinstance(user_data, dict) else 0
    if follower_count is None and isinstance(user_data, dict):
        edge = (user_data.get("edge_followed_by") or {}) if isinstance(user_data.get("edge_followed_by"), dict) else {}
        follower_count = edge.get("count")
    if follower_count is None and isinstance(user_data, dict):
        follower_count = user_data.get("followers")
    if follower_count is None:
        follower_count = 0
    follower_count = int(follower_count) if follower_count is not None else 0
    return (user_data or {}, follower_count)


def enrich_one(
    api_key: str,
    username: str,
    posts_count: int = 3,
    endpoint_user_info: str | None = None,
    endpoint_following: str | None = None,
    endpoint_posts: str | None = None,
    following_pagination_param: str = "start_from",
    skip_following: bool = False,
    fetch_30_posts: bool = True,
) -> dict:
    info = fetch_user_info(
        api_key, username, posts_count=posts_count, endpoint=endpoint_user_info
    )
    if not info:
        return {
            "username": username,
            "error": "user_info_failed",
            "user_data": None,
            "user_posts": None,
            "following": [],
            "posts_30_urls": [],
        }

    user_data, follower_count = _extract_user_data_and_follower_count(info)
    if skip_following:
        following_list = []
    else:
        following_count = user_data.get("following_count") or 0
        following_list = fetch_all_following(
            api_key,
            username,
            following_count,
            endpoint=endpoint_following,
            pagination_param=following_pagination_param,
        )

    # Step 2 (30 posts): only for accounts with > 1000 followers
    posts_30_urls = []
    if not fetch_30_posts or not endpoint_posts:
        if fetch_30_posts and not endpoint_posts:
            print(f"  [30posts] Skipping @{username}: no posts endpoint configured", file=sys.stderr)
    elif follower_count <= 1000:
        print(f"  [30posts] Skipping @{username}: follower_count={follower_count} (need >1000)", file=sys.stderr)
    else:
        print(f"  [30posts] Fetching for @{username} (follower_count={follower_count}) ...", file=sys.stderr)
        posts_30_urls = fetch_up_to_30_post_image_urls(
            api_key, username, endpoint=endpoint_posts
        )
        if posts_30_urls:
            print(f"  [30posts] @{username}: got {len(posts_30_urls)} post URLs", file=sys.stderr)
        else:
            print(f"  [30posts] @{username}: 0 images (API may be unavailable or returned empty; check RapidAPI plan for get_ig_user_posts)", file=sys.stderr)
        time.sleep(0.3)

    return {
        "username": username,
        "user_data": user_data,
        "user_posts": info.get("user_posts") or info.get("posts") or [],
        "following": following_list,
        "posts_30_urls": posts_30_urls,
        "_raw_user_info": info,
    }


def enrich_one_skip_profile(
    api_key: str,
    username: str,
    existing_data: dict,
    endpoint_posts: str | None = None,
    fetch_30_posts: bool = True,
) -> dict:
    """When artist already has follower_count: skip step 1 (profile API), only fetch 30 posts if >1000."""
    existing_ig = existing_data.get("instagram_enriched") or {}
    follower_count = existing_ig.get("follower_count")
    if follower_count is None:
        return None  # caller should do full enrich_one
    try:
        follower_count = int(follower_count)
    except (TypeError, ValueError):
        return None

    user_data = {
        "id": existing_ig.get("id"),
        "pk": existing_ig.get("id"),
        "full_name": existing_data.get("name"),
        "follower_count": follower_count,
        "following_count": existing_ig.get("following_count"),
        "media_count": existing_ig.get("media_count"),
        "profile_pic_url": existing_ig.get("profile_pic_url"),
    }
    following_list = existing_ig.get("following") or []

    posts_30_urls = []
    if fetch_30_posts and endpoint_posts and follower_count > 1000:
        print(f"  [30posts] Fetching for @{username} (follower_count={follower_count}, skip profile) ...", file=sys.stderr)
        posts_30_urls = fetch_up_to_30_post_image_urls(
            api_key, username, endpoint=endpoint_posts
        )
        if posts_30_urls:
            print(f"  [30posts] @{username}: got {len(posts_30_urls)} post URLs", file=sys.stderr)
        else:
            print(f"  [30posts] @{username}: 0 images", file=sys.stderr)
        time.sleep(0.3)

    return {
        "username": username,
        "user_data": user_data,
        "user_posts": [],
        "following": following_list,
        "posts_30_urls": posts_30_urls,
        "_raw_user_info": {},
    }


def _profile_pic_url(user_data: dict) -> str | None:
    if not user_data:
        return None
    return (
        user_data.get("profile_pic_url")
        or (user_data.get("hd_profile_pic_url_info") or {}).get("url")
    )


def _post_image_urls(user_posts: list) -> list[str]:
    urls = []
    for post in (user_posts or [])[:3]:
        node = post.get("node") if isinstance(post, dict) else post
        if not node:
            continue
        cands = (node.get("image_versions2") or {}).get("candidates") or []
        if cands:
            url = cands[0].get("url") if isinstance(cands[0], dict) else cands[0]
            if url:
                urls.append(url)
    return urls


def _download_image(url: str) -> bytes | None:
    try:
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        return r.content if r.content else None
    except Exception:
        return None


def _upload_instagram_images_to_r2(
    artist_id: str,
    profile_pic_url: str | None,
    post_urls: list[str],
    r2_client,
    bucket: str,
    public_url_base: str,
) -> tuple[str | None, list[str]]:
    """Download profile + up to 3 post images, upload to R2. Returns (profile_r2_url, [post_r2_urls])."""
    from r2 import upload_raw

    base_key = f"artists/{artist_id}/instagram"
    profile_r2 = None
    if profile_pic_url:
        raw = _download_image(profile_pic_url)
        if raw:
            key = f"{base_key}/profile.jpg"
            profile_r2 = upload_raw(
                r2_client, bucket, key, raw, "image/jpeg", public_url_base
            )
    post_r2 = []
    for i, url in enumerate(post_urls[:3], start=1):
        raw = _download_image(url)
        if raw:
            key = f"{base_key}/post_{i}.jpg"
            post_r2.append(
                upload_raw(r2_client, bucket, key, raw, "image/jpeg", public_url_base)
            )
    return profile_r2, post_r2


def _empty_analysis() -> dict:
    return {
        "themes": [],
        "dominant_colours": [],
        "body_parts": [],
        "size_category": None,
        "confidence_score": None,
    }


def _extract_bio(user_data: dict, raw_info: dict) -> str:
    """Extract biography from user_data / raw API response (v3 returns it at top level)."""
    candidates = []
    for d in (user_data, raw_info):
        if not isinstance(d, dict):
            continue
        for key in ("biography", "bio", "about", "description", "bio_summary"):
            val = d.get(key)
            if isinstance(val, str) and val.strip():
                candidates.append(val.strip())
    for key in ("data", "body", "profile", "user"):
        inner = raw_info.get(key) if isinstance(raw_info, dict) else None
        if isinstance(inner, dict):
            for k in ("biography", "bio", "about", "description"):
                val = inner.get(k)
                if isinstance(val, str) and val.strip():
                    candidates.append(val.strip())
            inner_user = inner.get("user") or inner.get("user_data")
            if isinstance(inner_user, dict):
                for k in ("biography", "bio", "about", "description"):
                    val = inner_user.get(k)
                    if isinstance(val, str) and val.strip():
                        candidates.append(val.strip())
    return candidates[0] if candidates else ""


def build_instagram_enriched_and_meta(
    enriched: dict,
    artist_id: str,
    r2_client=None,
    bucket: str | None = None,
    public_url_base: str | None = None,
    skip_r2: bool = False,
) -> tuple[dict, str | None, str, str | None, list]:
    """
    Build slim instagram_enriched and return
    (instagram_enriched, name_override, updated_at, bio_append, new_tattoos_front).
    If R2 set: uploads profile pic only; 30 posts from get_ig_user_posts -> webp -> R2, prepended as tattoos.
    """
    user_data = enriched.get("user_data") or {}
    following = enriched.get("following") or []
    posts_30_urls = enriched.get("posts_30_urls") or []

    name_override = (user_data.get("full_name") or "").strip()
    updated_at = datetime.now().strftime("%Y-%m-%d")
    # Biography: from user_data / raw response (v3 returns it at top level)
    raw_info = enriched.get("_raw_user_info") or {}
    bio_append = _extract_bio(user_data, raw_info)
    bio_append = (bio_append or "").strip() if isinstance(bio_append, str) else ""

    slim = {
        "id": user_data.get("id") or user_data.get("pk"),
        "follower_count": user_data.get("follower_count"),
        "following_count": user_data.get("following_count"),
        "media_count": user_data.get("media_count"),
        "following": following,
    }

    new_tattoos_front = []
    if not skip_r2 and r2_client and bucket and public_url_base:
        profile_url = _profile_pic_url(user_data)
        # Only upload profile pic from step 1; 30 posts come from get_ig_user_posts (step 2)
        profile_r2, _ = _upload_instagram_images_to_r2(
            artist_id, profile_url, [], r2_client, bucket, public_url_base
        )
        if profile_r2:
            slim["profile_pic_url"] = profile_r2

        # 30 posts: download -> webp thumb+full -> R2, same format as tattoos
        if posts_30_urls:
            try:
                from images import _process_image
                from r2 import upload_image
            except ImportError as e:
                print(f"  [30posts] Skipping image upload (missing module): {e}", file=sys.stderr)
            else:
                base = (public_url_base or "").rstrip("/")
                for i, url in enumerate(posts_30_urls[:30], start=1):
                    raw = _download_image(url)
                    if not raw:
                        continue
                    try:
                        thumb_b, full_b = _process_image(raw, 400, 1600)
                    except Exception:
                        continue
                    image_id = f"ig_{i:03d}"
                    upload_image(
                        r2_client, bucket, artist_id, image_id, thumb_b, full_b
                    )
                    new_tattoos_front.append({
                        "image_id": image_id,
                        "image_full": f"{base}/artists/{artist_id}/full/{image_id}.webp",
                        "image_thumb": f"{base}/artists/{artist_id}/thumb/{image_id}.webp",
                        "analysis": _empty_analysis(),
                    })
                    time.sleep(0.05)
    return slim, name_override or None, updated_at, bio_append or None, new_tattoos_front


def git_commit_and_push(cwd: Path, message: str = "chore: enrich artist Instagram data") -> bool:
    try:
        # Pull remote changes first so push won't be rejected (e.g. if you pushed from another machine)
        subprocess.run(
            ["git", "fetch", "origin", "main"],
            check=True,
            cwd=str(cwd),
            capture_output=True,
        )
        subprocess.run(
            ["git", "merge", "--no-edit", "origin/main"],
            cwd=str(cwd),
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "add", "data/artists/", str(repo_path(ENRICH_STATE_FILE))],
            check=True,
            cwd=str(cwd),
            capture_output=True,
        )
        status = subprocess.run(
            ["git", "status", "--short"],
            capture_output=True,
            text=True,
            cwd=str(cwd),
        )
        if not status.stdout.strip():
            return True
        subprocess.run(["git", "commit", "-m", message], check=True, cwd=str(cwd))
        subprocess.run(["git", "push", "origin", "main"], check=True, cwd=str(cwd))
        print(f"   📤 Pushed: {message}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"⚠️ Git push failed: {e}", file=sys.stderr)
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Enrich Instagram data via RapidAPI; optionally update data/artists/*.json in place."
    )
    parser.add_argument(
        "--update-artists",
        action="store_true",
        default=True,
        help="Update data/artists/<id>.json in place (default: True).",
    )
    parser.add_argument(
        "--no-update-artists",
        action="store_false",
        dest="update_artists",
        help="Do not update artist JSONs; write to instagram_enriched/ or --output.",
    )
    parser.add_argument(
        "--input",
        type=str,
        help="JSON file with 'handles' or 'urls' (only when --no-update-artists). Ignored when updating artists.",
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Output path: dir or single .json (only when --no-update-artists).",
    )
    parser.add_argument("--limit", type=int, default=None, help="Max artists per run (for VM batch).")
    parser.add_argument("--posts", type=int, default=3, help="Number of recent posts to fetch.")
    parser.add_argument("--delay", type=float, default=1.0, help="Seconds between users.")
    parser.add_argument(
        "--batch-size",
        type=int,
        default=None,
        help="Commit and push every N artists (only with --update-artists).",
    )
    parser.add_argument("--no-git", action="store_true", help="Do not commit/push (with --update-artists).")
    parser.add_argument("--no-r2", action="store_true", help="Do not upload profile/post images to R2.")
    parser.add_argument(
        "--skip-following",
        action="store_true",
        help="Do not fetch following list (saves quota when that API is broken).",
    )
    parser.add_argument(
        "--no-30-posts",
        action="store_true",
        help="Do not fetch 30 posts (get_ig_user_posts.php).",
    )
    parser.add_argument(
        "--only-ids-file",
        type=str,
        default=None,
        help="Only process artists whose id is in this file (JSON array or one id per line). Use with list_hidden_artists.py --output.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-enrich artists even if they already have instagram_enriched or are in completed state.",
    )
    args = parser.parse_args()

    config = load_config()
    api_key = os.environ.get("RAPIDAPI_KEY") or (config.get("rapidapi_key") if config else None)
    if not api_key:
        print("Set RAPIDAPI_KEY in the environment or rapidapi_key in packages/scraper/config.yaml.", file=sys.stderr)
        sys.exit(1)
    endpoint_user_info = (config or {}).get("rapidapi_endpoint_user_info") or DEFAULT_ENDPOINT_USER_INFO
    endpoint_following = (config or {}).get("rapidapi_endpoint_following") or DEFAULT_ENDPOINT_FOLLOWING
    endpoint_posts = (config or {}).get("rapidapi_endpoint_posts") or DEFAULT_ENDPOINT_POSTS
    following_pagination_param = (config or {}).get("rapidapi_following_pagination_param") or "start_from"

    data_artists = repo_path("data", "artists")
    if not data_artists.is_dir():
        print("data/artists not found.", file=sys.stderr)
        sys.exit(1)

    if args.update_artists:
        only_ids = None
        if args.only_ids_file:
            only_path = Path(args.only_ids_file) if Path(args.only_ids_file).is_absolute() else repo_path(args.only_ids_file)
            if not only_path.exists():
                print(f"only-ids-file not found: {only_path}", file=sys.stderr)
                sys.exit(1)
            only_ids = load_id_set_from_file(only_path)
            print(f"Restricting to {len(only_ids)} artist IDs from {only_path}")
        # Build list (artist_id, username), apply state and skip already enriched (unless --force)
        artist_list = load_artists_with_instagram(data_artists, only_ids=only_ids)
        state = load_enrich_state()
        todo = []
        for idx, (artist_id, username) in enumerate(artist_list):
            if not args.force:
                if artist_id in state["completed_ids"]:
                    continue
                if artist_already_enriched(data_artists / f"{artist_id}.json"):
                    state["completed_ids"].add(artist_id)
                    state["last_index"] = idx
                    continue
            todo.append((idx, artist_id, username))

        save_enrich_state(state["completed_ids"], state["last_index"])

        if args.limit is not None:
            todo = todo[: args.limit]
        if not todo:
            print("All artists already enriched. Exiting.")
            sys.exit(EXIT_ALL_DONE)

        batch_size = args.batch_size
        do_git = not args.no_git and batch_size is not None
        cwd = repo_path()

        r2_client = None
        r2_bucket = None
        r2_public_url = None
        if not args.no_r2 and config:
            r2_cfg = config.get("r2")
            if r2_cfg and r2_cfg.get("access_key_id"):
                from r2 import get_r2_client
                r2_client = get_r2_client(
                    r2_cfg["account_id"],
                    r2_cfg["access_key_id"],
                    r2_cfg["secret_access_key"],
                )
                r2_bucket = r2_cfg.get("bucket", "open-tattoo-artists")
                r2_public_url = r2_cfg.get("public_url", "")

        for i, (idx, artist_id, username) in enumerate(todo):
            artist_path = data_artists / f"{artist_id}.json"
            with open(artist_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            existing_follower_count = (data.get("instagram_enriched") or {}).get("follower_count")
            # With --force, always fetch full profile: links.instagram may have changed
            # (skip_profile would keep old ig id while hitting the new handle).
            if existing_follower_count is not None and not args.force:
                print(f"[{i+1}/{len(todo)}] {artist_id} (@{username}) [skip profile, follower_count={existing_follower_count}]")
                enriched = enrich_one_skip_profile(
                    api_key,
                    username,
                    data,
                    endpoint_posts=endpoint_posts,
                    fetch_30_posts=not args.no_30_posts,
                )
            else:
                print(f"[{i+1}/{len(todo)}] {artist_id} (@{username})")
                enriched = enrich_one(
                    api_key,
                    username,
                    posts_count=args.posts,
                    endpoint_user_info=endpoint_user_info,
                    endpoint_following=endpoint_following,
                    endpoint_posts=endpoint_posts,
                    following_pagination_param=following_pagination_param,
                    skip_following=args.skip_following,
                    fetch_30_posts=not args.no_30_posts,
                )

            slim, name_override, updated_at, bio_append, new_tattoos_front = (
                build_instagram_enriched_and_meta(
                    enriched,
                    artist_id,
                    r2_client=r2_client,
                    bucket=r2_bucket,
                    public_url_base=r2_public_url or "",
                    skip_r2=args.no_r2,
                )
            )
            data["updated_at"] = updated_at
            if name_override:
                data["name"] = name_override
            if bio_append:
                existing_bio = (data.get("bio") or "").strip()
                data["bio"] = (existing_bio + "\n\n" + bio_append).strip() if existing_bio else bio_append
            if new_tattoos_front:
                data["tattoos"] = new_tattoos_front + (data.get("tattoos") or [])
            data["instagram_enriched"] = slim
            with open(artist_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            state["completed_ids"].add(artist_id)
            state["last_index"] = idx
            save_enrich_state(state["completed_ids"], state["last_index"])

            if do_git and (i + 1) % batch_size == 0:
                git_commit_and_push(cwd, "chore: enrich artist Instagram data")

            if i < len(todo) - 1:
                time.sleep(args.delay)

        if do_git and len(todo) % batch_size != 0:
            git_commit_and_push(cwd, "chore: enrich artist Instagram data")

        print("Done.")
        return

    # --- No update artists: write to dir or single file ---
    if args.input:
        path = Path(args.input) if Path(args.input).is_absolute() else repo_path(args.input)
        if not path.exists():
            print(f"Input file not found: {path}", file=sys.stderr)
            sys.exit(1)
        usernames = load_usernames_from_input(path)
    else:
        usernames = [u for (_, u) in load_artists_with_instagram(data_artists)]

    if args.limit:
        usernames = usernames[: args.limit]

    out_path = None
    out_dir = None
    if args.output:
        p = Path(args.output)
        if p.suffix.lower() == ".json":
            out_path = p if p.is_absolute() else repo_path(*p.parts)
        else:
            out_dir = p if p.is_absolute() else repo_path(*p.parts)
    if out_dir is None and out_path is None:
        out_dir = repo_path("packages", "scraper", "instagram_enriched")

    if out_dir:
        out_dir.mkdir(parents=True, exist_ok=True)

    results = [] if out_path else None
    for i, username in enumerate(usernames):
        print(f"[{i+1}/{len(usernames)}] {username}")
        data = enrich_one(
            api_key,
            username,
            posts_count=args.posts,
            endpoint_user_info=endpoint_user_info,
            endpoint_following=endpoint_following,
            endpoint_posts=endpoint_posts,
            following_pagination_param=following_pagination_param,
            skip_following=args.skip_following,
            fetch_30_posts=not args.no_30_posts,
        )
        if out_dir:
            p = out_dir / f"{username}.json"
            with open(p, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        else:
            if results is not None:
                results.append(data)
        if i < len(usernames) - 1:
            time.sleep(args.delay)

    if out_path is not None and results is not None:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"Wrote {len(results)} records to {out_path}")

    print("Done.")


if __name__ == "__main__":
    main()
