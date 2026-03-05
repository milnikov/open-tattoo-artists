#!/usr/bin/env python3
"""
Discover all artist profile URLs from tattoofilter.com, then compare with
packages/scraper/discovered_pages.json and output a list of new artists
(URLs not already in discovered_pages).

Usage:
  python discover_tattoofilter_artists.py                    # full: /artists/all + location/nationality pages
  python discover_tattoofilter_artists.py --no-locations     # only /artists/all (faster)
  python discover_tattoofilter_artists.py --no-selenium      # requests only (no browser)
"""

import argparse
import json
import re
import sys
import time
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

# Add parent so we can import _repo_root when run as script
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _repo_root import repo_path

BASE_URL = "https://www.tattoofilter.com"
ARTISTS_ALL_URL = f"{BASE_URL}/artists/all"

# Extra listing pages to crawl (location + nationality) for maximum coverage
LOCATION_SLUGS = [
    "new-york-city", "london", "los-angeles", "barcelona", "berlin", "san-francisco",
    "manhattan", "brooklyn", "queens", "bronx", "staten-island",
    "miami", "chicago", "austin", "seattle", "portland", "amsterdam", "paris", "madrid",
    "rome", "milan", "vienna", "prague", "sydney", "melbourne", "tokyo", "seoul",
]
NATIONALITY_SLUGS = [
    "united-states", "united-kingdom", "germany", "brazil", "spain", "canada",
    "france", "italy", "australia", "netherlands", "poland", "mexico", "argentina",
    "japan", "south-korea", "russia", "ukraine", "sweden", "norway", "portugal",
]

# Path segments that are directory/listing pages, not individual artist profiles
ARTIST_PAGE_EXCLUDE_PREFIXES = (
    "/artists/all",
    "/artists/l/",      # location listing
    "/artists/from/",   # nationality listing
    "/artists/countries",
    "/artists/nationalities",
)
ARTIST_PAGE_EXCLUDE_EXACT = {f"{BASE_URL}/artists", f"{BASE_URL}/artists/"}


def setup_driver():
    """Create headless Chrome driver (uses webdriver-manager for correct chromedriver)."""
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options

    opts = Options()
    opts.add_argument("--headless")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--window-size=1920,1080")
    try:
        from webdriver_manager.chrome import ChromeDriverManager
        from selenium.webdriver.chrome.service import Service
        service = Service(ChromeDriverManager().install())
        return webdriver.Chrome(service=service, options=opts)
    except Exception:
        return webdriver.Chrome(options=opts)


def is_artist_profile_url(url: str) -> bool:
    """True if URL is an individual artist profile, not a listing page."""
    if not url.startswith(BASE_URL) or "/artists/" not in url:
        return False
    if url.rstrip("/") in ARTIST_PAGE_EXCLUDE_EXACT:
        return False
    for prefix in ARTIST_PAGE_EXCLUDE_PREFIXES:
        if prefix in url:
            return False
    # Must be /artists/<single_slug> with no extra path (e.g. /artists/lena, /artists/sana.ink)
    parsed = urlparse(url)
    path = parsed.path.strip("/")
    parts = path.split("/")
    if len(parts) != 2 or parts[0] != "artists" or not parts[1]:
        return False
    return True


def extract_artist_urls_from_html(html: str, base: str) -> set:
    """Extract artist profile URLs from page HTML."""
    soup = BeautifulSoup(html, "html.parser")
    found = set()
    for a in soup.find_all("a", href=True):
        href = a["href"]
        absolute = urljoin(base, href)
        parsed = urlparse(absolute)
        clean = f"{parsed.scheme}://{parsed.netloc}{parsed.path}".rstrip("/")
        if is_artist_profile_url(clean):
            found.add(clean)
    # Regex fallback for links in JS or data attributes
    for match in re.findall(rf'{re.escape(BASE_URL)}/artists/([a-zA-Z0-9_.-]+)', html):
        slug = match.split("/")[0].split("?")[0]
        if slug and slug not in ("all", "l", "from", "countries", "nationalities"):
            found.add(f"{BASE_URL}/artists/{slug}")
    return found


def extract_artist_urls_from_dom(driver) -> set:
    """Extract artist profile URLs from current DOM via Selenium."""
    from selenium.webdriver.common.by import By
    found = set()
    try:
        for el in driver.find_elements(By.TAG_NAME, "a"):
            href = el.get_attribute("href")
            if not href or "/artists/" not in href:
                continue
            parsed = urlparse(href)
            clean = f"{parsed.scheme}://{parsed.netloc}{parsed.path}".rstrip("/")
            if is_artist_profile_url(clean):
                found.add(clean)
    except Exception:
        pass
    return found


def discover_tattoofilter_artists_requests():
    """Fetch /artists/all and location/nationality listing pages via requests; return set of artist URLs (no JS)."""
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    })
    artist_urls = set()
    urls_to_fetch = [ARTISTS_ALL_URL]
    urls_to_fetch.extend(f"{BASE_URL}/artists/l/{s}" for s in LOCATION_SLUGS)
    urls_to_fetch.extend(f"{BASE_URL}/artists/from/{s}" for s in NATIONALITY_SLUGS)
    for url in urls_to_fetch:
        try:
            r = session.get(url, timeout=15)
            r.raise_for_status()
            artist_urls.update(extract_artist_urls_from_html(r.text, BASE_URL))
        except Exception as e:
            pass  # skip 404 or errors
    return artist_urls


def _discover_artists_on_listing_page(driver, url, max_load_more=80, max_scrolls=150, no_change_stop=25, label=""):
    """Load a single listing page, click 'load more' and scroll; return set of artist URLs."""
    from selenium.webdriver.common.by import By

    artist_urls = set()
    driver.get(url)
    time.sleep(2)

    load_more_count = 0
    scroll_count = 0
    no_change = 0
    prev_size = 0

    load_more_selectors = [
        "//*[contains(text(), 'load more')]",
        "//*[contains(text(), 'Load More')]",
        "//button[contains(., 'load more')]",
        "//a[contains(., 'load more')]",
        "//*[contains(@class, 'load-more')]",
        "//*[contains(@class, 'loadMore')]",
    ]

    while scroll_count < max_scrolls:
        if load_more_count < max_load_more:
            for xpath in load_more_selectors:
                try:
                    btn = driver.find_element(By.XPATH, xpath)
                    if btn.is_displayed() and btn.is_enabled():
                        driver.execute_script("arguments[0].scrollIntoView(true);", btn)
                        time.sleep(0.5)
                        driver.execute_script("arguments[0].click();", btn)
                        time.sleep(2)
                        load_more_count += 1
                        break
                except Exception:
                    continue

        driver.execute_script("window.scrollBy(0, 500);")
        time.sleep(0.25)
        current = extract_artist_urls_from_dom(driver)
        artist_urls.update(current)

        if len(artist_urls) == prev_size:
            no_change += 1
            if no_change >= no_change_stop:
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(1.5)
                artist_urls.update(extract_artist_urls_from_dom(driver))
                if len(artist_urls) == prev_size:
                    break
                no_change = 0
        else:
            no_change = 0

        prev_size = len(artist_urls)
        scroll_count += 1

        if scroll_count % 25 == 0:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(0.8)

    artist_urls.update(extract_artist_urls_from_html(driver.page_source, BASE_URL))
    return artist_urls


def discover_tattoofilter_artists(driver, max_load_more=150, max_scrolls=500, no_change_stop=30, crawl_locations=True):
    """Crawl /artists/all (with higher limits) and optionally location/nationality pages; return merged set of artist URLs."""
    from selenium.webdriver.common.by import By

    all_artists = set()

    # 1) Main "All artists" page with aggressive limits
    print("  Crawling /artists/all ...")
    all_artists.update(_discover_artists_on_listing_page(
        driver, ARTISTS_ALL_URL,
        max_load_more=max_load_more, max_scrolls=max_scrolls, no_change_stop=no_change_stop,
    ))
    print(f"    Got {len(all_artists)} artists from /artists/all")

    if not crawl_locations:
        return all_artists

    # 2) Location pages
    for slug in LOCATION_SLUGS:
        url = f"{BASE_URL}/artists/l/{slug}"
        try:
            current = _discover_artists_on_listing_page(
                driver, url, max_load_more=30, max_scrolls=60, no_change_stop=12, label=slug,
            )
            added = len(current - all_artists)
            all_artists.update(current)
            if added > 0 or len(current) > 0:
                print(f"    l/{slug}: +{added} new (total on page {len(current)})")
        except Exception as e:
            pass  # skip broken or 404 pages

    # 3) Nationality pages
    for slug in NATIONALITY_SLUGS:
        url = f"{BASE_URL}/artists/from/{slug}"
        try:
            current = _discover_artists_on_listing_page(
                driver, url, max_load_more=30, max_scrolls=60, no_change_stop=12, label=slug,
            )
            added = len(current - all_artists)
            all_artists.update(current)
            if added > 0 or len(current) > 0:
                print(f"    from/{slug}: +{added} new (total on page {len(current)})")
        except Exception:
            pass

    return all_artists


def load_discovered_urls(discovered_path: Path) -> set:
    """Load all URLs from discovered_pages.json (all categories)."""
    if not discovered_path.exists():
        return set()
    with open(discovered_path, encoding="utf-8") as f:
        data = json.load(f)
    urls = set()
    for key, value in data.items():
        if isinstance(value, list):
            urls.update(str(u) for u in value)
    return urls


def main():
    parser = argparse.ArgumentParser(description="Discover TattooFilter artists and compare to discovered_pages.json")
    parser.add_argument("--no-selenium", action="store_true", help="Use requests only (no browser); fewer artists.")
    parser.add_argument("--no-locations", action="store_true", help="Only crawl /artists/all; skip location/nationality pages.")
    args = parser.parse_args()

    discovered_path = repo_path("packages", "scraper", "discovered_pages.json")
    out_dir = repo_path("packages", "scraper")
    out_json = out_dir / "tattoofilter_new_artists.json"
    out_txt = out_dir / "tattoofilter_new_artists.txt"

    print("=" * 60)
    print("TattooFilter: discover artist pages & compare to discovered_pages")
    print("=" * 60)

    if args.no_selenium:
        print("\n🔍 Fetching artist list (requests only, no JS)...")
        tattoofilter_artists = discover_tattoofilter_artists_requests()
        print(f"   Total TattooFilter artist URLs: {len(tattoofilter_artists)}")
    else:
        driver = setup_driver()
        try:
            print("\n🔍 Fetching artist list from tattoofilter.com ...")
            tattoofilter_artists = discover_tattoofilter_artists(driver, crawl_locations=not args.no_locations)
            print(f"   Total TattooFilter artist URLs: {len(tattoofilter_artists)}")
        finally:
            driver.quit()

    print("\n📂 Loading existing discovered_pages.json ...")
    known_urls = load_discovered_urls(discovered_path)
    print(f"   Total URLs in discovered_pages: {len(known_urls)}")

    new_artists = sorted(tattoofilter_artists - known_urls)
    print(f"\n✨ New artists (not in discovered_pages): {len(new_artists)}")

    with open(out_json, "w", encoding="utf-8") as f:
        json.dump({"source": "https://www.tattoofilter.com", "artists": new_artists}, f, indent=2)

    with open(out_txt, "w", encoding="utf-8") as f:
        f.write(f"TattooFilter new artists (not in discovered_pages.json): {len(new_artists)}\n")
        f.write("=" * 60 + "\n\n")
        for u in new_artists:
            f.write(u + "\n")

    print(f"\n✅ Results saved to:")
    print(f"   - {out_json}")
    print(f"   - {out_txt}")
    print(f"\n📊 Summary: {len(new_artists)} new artist URLs to add.")


if __name__ == "__main__":
    main()
