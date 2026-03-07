"""
Parse tattoofilter.com artist pages. Uses Selenium for JS-rendered content.
Returns same ParsedArtist shape as parse.py for use in pipeline.
"""

import re
import time
import random
from typing import Optional

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

from parse import ParsedArtist

try:
    from webdriver_manager.chrome import ChromeDriverManager
    USE_WEBDRIVER_MANAGER = True
except ImportError:
    USE_WEBDRIVER_MANAGER = False

BASE_URL = "https://www.tattoofilter.com"


def _create_driver(headless: bool = True):
    opts = Options()
    if headless:
        opts.add_argument("--headless=new")
        opts.add_argument("--disable-gpu")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument(
        "--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    if USE_WEBDRIVER_MANAGER:
        try:
            return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=opts)
        except Exception:
            pass
    return webdriver.Chrome(options=opts)


# Site/brand Instagram handles: ignore these and use URL slug so we don't merge all artists into one.
INSTAGRAM_HANDLE_BLOCKLIST = frozenset({"tattoofilter", "tattoofilter.com"})


def _extract_instagram_handle(url: str) -> Optional[str]:
    if not url:
        return None
    m = re.search(r"instagram\.com/([a-zA-Z0-9_.]+)", url, re.IGNORECASE)
    if m:
        handle = m.group(1).lower().split("/")[0].split("?")[0]
        if handle in INSTAGRAM_HANDLE_BLOCKLIST:
            return None
        return handle
    return None


def _slug_to_handle(url: str) -> str:
    """Use URL slug as artist id when no Instagram."""
    slug = url.rstrip("/").split("/")[-1]
    return re.sub(r"[^a-z0-9._-]", "", slug.lower().replace("-", "_"))[:30] or "unknown"


def _normalize_style(s: str) -> str:
    s = s.strip().lower()
    if s in ("black and grey", "black and gray"):
        return "black&gray"
    return s


def _scroll_and_load_more(driver, max_clicks: int = 20, scroll_pause: float = 0.6):
    """Scroll and click 'load more' to reveal tattoo images."""
    for _ in range(max_clicks):
        try:
            for xpath in [
                "//*[contains(translate(text(), 'LOADMORE', 'load more'), 'load more')]",
                "//*[contains(@class, 'load-more')]",
                "//*[contains(@class, 'loadMore')]",
            ]:
                try:
                    btn = driver.find_element(By.XPATH, xpath)
                    if btn.is_displayed() and btn.is_enabled():
                        driver.execute_script("arguments[0].scrollIntoView(true);", btn)
                        time.sleep(0.5)
                        driver.execute_script("arguments[0].click();", btn)
                        time.sleep(2.5)
                        break
                except Exception:
                    continue
        except Exception:
            pass
        driver.execute_script("window.scrollBy(0, 600);")
        time.sleep(scroll_pause)


def _is_wanted_tattoo_image(url: str) -> bool:
    """Exclude artist/studio avatar, default/placeholder images, and PNGs. Keep only /tattoo/ images."""
    low = url.lower()
    if "/artist/" in low:  # e.g. cdntattoofilter.com/artist/7824/s.jpg
        return False
    if "/studio/" in low:  # e.g. cdntattoofilter.com/studio/1294/s.jpg
        return False
    if "/default/" in low:  # studio-img.png, location-img.png
        return False
    if ".png" in low.split("?")[0]:
        return False
    return True


def _extract_image_urls_from_backgrounds(driver, max_images: int) -> list[str]:
    """Extract image URLs from style='background-image: url(...)' on divs."""
    urls = []
    seen = set()
    try:
        for el in driver.find_elements(By.XPATH, "//*[contains(@style, 'background-image') or contains(@style, 'background:')]"):
            style = el.get_attribute("style") or ""
            for m in re.findall(r'url\(["\']?(https?://[^)"\'\s]+)["\']?\)', style, re.I):
                u = m.split("?")[0]
                if u not in seen and _is_wanted_tattoo_image(u):
                    seen.add(u)
                    urls.append(u)
    except Exception:
        pass
    return list(dict.fromkeys(urls))[:max_images]


def _extract_image_urls_from_dom(driver, max_images: int) -> list[str]:
    """Get image URLs from live DOM (after scroll/lazy load). Selenium returns current src."""
    urls = []
    seen = set()
    try:
        for img in driver.find_elements(By.TAG_NAME, "img"):
            for attr in ("src", "data-src", "data-lazy-src"):
                try:
                    src = img.get_attribute(attr)
                    if not src or src in seen:
                        continue
                    src = src.split("?")[0].strip()
                    if not src.startswith("http"):
                        continue
                    low = src.lower()
                    if any(x in low for x in ["avatar", "logo", "icon", "emoji", "favicon", "placeholder"]):
                        continue
                    if "data:" in low and not low.startswith("data:"):
                        continue
                    if not _is_wanted_tattoo_image(src):
                        continue
                    seen.add(src)
                    urls.append(src)
                except Exception:
                    continue
    except Exception:
        pass
    return list(dict.fromkeys(urls))[:max_images]


def _extract_image_urls_from_html(page_source: str, max_images: int) -> list[str]:
    """Fallback: collect from page source (img src/data-src + regex for CDN URLs)."""
    urls = []
    seen = set()
    soup = BeautifulSoup(page_source, "html.parser")
    for img in soup.find_all("img"):
        src = img.get("src") or img.get("data-src") or img.get("data-lazy-src")
        if not src or src in seen:
            continue
        src = src.split("?")[0]
        if not src.startswith("http") or "data:" in src:
            continue
        low = src.lower()
        if any(x in low for x in ["avatar", "logo", "icon", "emoji", "flag.", "favicon"]):
            continue
        if not _is_wanted_tattoo_image(src):
            continue
        seen.add(src)
        urls.append(src)
    # Regex: image URLs with extension (only jpg/jpeg/webp/gif; no png)
    for m in re.findall(r'https?://[^\s"\'<>]+(?:\.(?:jpg|jpeg|webp|gif))(?:\?[^\s"\'<>]*)?', page_source, re.I):
        u = m.split("?")[0]
        if u not in seen and _is_wanted_tattoo_image(u):
            seen.add(u)
            urls.append(u)
    # background-image: url(...)
    for m in re.findall(r'url\(["\']?(https?://[^)"\'\s]+)["\']?\)', page_source, re.I):
        u = m.split("?")[0]
        if u not in seen and _is_wanted_tattoo_image(u):
            seen.add(u)
            urls.append(u)
    return list(dict.fromkeys(urls))[:max_images]


def parse_artist_page(
    url: str,
    headless: bool = True,
    max_images: int = 50,
    metadata_only: bool = False,
) -> Optional[ParsedArtist]:
    """
    Parse a tattoofilter.com artist page. Returns ParsedArtist compatible with pipeline.
    Uses URL slug as instagram_handle when no Instagram link is found.
    """
    driver = None
    try:
        driver = _create_driver(headless=headless)
        driver.get(url)
        time.sleep(random.uniform(3, 5))

        # Name: from title "Evan Kim | Tattoofilter" or h1
        name = ""
        try:
            title = (driver.title or "").strip()
            if title and "|" in title:
                name = title.split("|")[0].strip()
            if not name and title:
                name = title.replace("Tattoofilter", "").strip(" |")
        except Exception:
            pass
        if not name:
            slug = url.rstrip("/").split("/")[-1]
            name = slug.replace("_", " ").replace("-", " ").title()

        # On TattooFilter the artist nick (URL slug) is their Instagram username.
        slug = url.rstrip("/").split("/")[-1]
        handle = _slug_to_handle(url)  # e.g. 118, 1991_ink (safe for filenames)
        if slug and slug.lower() not in INSTAGRAM_HANDLE_BLOCKLIST:
            instagram_url = f"https://instagram.com/{slug}"
        else:
            instagram_url = None

        # Location: e.g. "roomManhattan, New York City" or "room Trieste, Province of Trieste" (no space after "room" on some pages)
        city, country = "Unknown", "Unknown"
        try:
            body = (driver.find_element(By.TAG_NAME, "body").text or "")
            # room with optional space (roomManhattan or room Manhattan), then capture until digits/tattoos
            m = re.search(r"room\s*([\s\S]+?)(?=\s*[\d,]+\s*tattoos|\s*[\d,]+\s*likes|$)", body, re.I)
            if not m:
                m = re.search(r"room\s*([^\n]+)", body, re.I)
            if m:
                loc_line = m.group(1).strip()
                loc_clean = re.sub(r"[\U0001F1E0-\U0001F1FF\U0001F300-\U0001F9FF]", "", loc_line).strip()
                loc_clean = re.sub(r"\s+", " ", loc_clean).strip()
                parts = [p.strip() for p in re.split(r"[,;]", loc_clean) if p.strip()]
                if len(parts) >= 2:
                    city = parts[0][:80]
                    last = parts[-1][:80]
                    if any(x in last for x in ("County", "States", "USA", "Florida", "California", "Texas", "New York", "Miami-Dade")):
                        country = "United States"
                    elif "Province" in last or "Trieste" in last:
                        country = "Italy"
                    elif len(last) <= 50 and re.match(r"^[A-Za-z\s\-']+$", last):
                        country = last
                    else:
                        country = "Unknown"
                elif len(parts) == 1 and 2 <= len(parts[0]) <= 80:
                    city = parts[0]
                    if "New York" in city or "Manhattan" in city or "Brooklyn" in city or "Queens" in city or "Miami" in city:
                        country = "United States"
                    elif city in ("London", "Manchester", "Birmingham"):
                        country = "United Kingdom"
                    elif "Bogotá" in city or "Bogota" in city:
                        country = "Colombia"
                    elif "Trieste" in city:
                        country = "Italy"
        except Exception:
            pass

        # Styles: from style links in header (e.g. "Single Needle", "Fine Line"). Exclude "X's Tattoos" / "tattoos".
        styles = []
        try:
            for a in driver.find_elements(By.XPATH, "//a[contains(@href, '/tattoos/')]"):
                text = (a.text or "").strip()
                if 2 <= len(text) <= 40 and not text.startswith("http"):
                    low = text.lower()
                    if low == "tattoos" or "'s tattoos" in low or low.endswith("'s tattoos"):
                        continue
                    if "tattoos" in low and ("'" in text or "’" in text):  # e.g. "Sofia Castro's Tattoos"
                        continue
                    norm = _normalize_style(text)
                    if norm and norm not in styles:
                        styles.append(norm)
        except Exception:
            pass
        styles = styles[:15]

        # Images: scroll tattoo grid into view first, then load more so lazy-loaded /tattoo/ images appear
        image_urls = []
        if not metadata_only:
            try:
                # Scroll to "X's Tattoos" section so the tattoo grid is in view and loads
                for hint in ["'s Tattoos", "tattoos filtered by", "Body part"]:
                    try:
                        el = driver.find_element(By.XPATH, f"//*[contains(text(), '{hint}')]")
                        driver.execute_script("arguments[0].scrollIntoView({block: 'start'});", el)
                        time.sleep(1.5)
                        break
                    except Exception:
                        continue
            except Exception:
                pass
            _scroll_and_load_more(driver, max_clicks=20)
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2.5)
            image_urls = _extract_image_urls_from_dom(driver, max_images)
            if not image_urls:
                image_urls = _extract_image_urls_from_html(driver.page_source, max_images)
            if not image_urls:
                image_urls = _extract_image_urls_from_backgrounds(driver, max_images)
            image_urls = [u for u in image_urls if _is_wanted_tattoo_image(u)][:max_images]

        # Website: first external link that isn't social
        website = None
        try:
            for a in driver.find_elements(By.TAG_NAME, "a"):
                href = a.get_attribute("href")
                if not href or "instagram" in href or "facebook" in href or "tattoofilter" in href:
                    continue
                if href.startswith("http"):
                    website = href
                    break
        except Exception:
            pass

        # Bio: short "about" between Contact and Workplace (e.g. "Hey, I'm a Colombian tattoo artist...")
        bio = None
        try:
            body = (driver.find_element(By.TAG_NAME, "body").text or "")
            # Between "Contact" and "Workplace" or "X's Tattoos"
            m = re.search(r"Contact\s+(.+?)(?=Workplace|'s Tattoos|Body part|Influences|$)", body, re.I | re.DOTALL)
            if m:
                raw = m.group(1).strip()
                # Take first 1–2 sentences (up to ~500 chars), drop "follow" / "Share" lines
                lines = [l.strip() for l in raw.split("\n") if l.strip() and l.strip() not in ("follow", "Share share", "share")]
                if lines:
                    bio = " ".join(lines[:3]).strip()[:500]
                    if len(bio) < 20:
                        bio = None
        except Exception:
            pass

        return ParsedArtist(
            instagram_url=instagram_url,
            instagram_handle=handle,
            name=name,
            city=city,
            country=country,
            styles=styles,
            website=website,
            source_url=url,
            image_urls=image_urls,
            bio=bio,
            tattooing_since=None,
        )
    except Exception as e:
        raise RuntimeError(f"Parse error for {url}: {e}") from e
    finally:
        if driver:
            driver.quit()


if __name__ == "__main__":
    """Run parser for one or more URLs and print extracted data as JSON.
    Usage: python parse_tattoofilter.py [<url> ...] [--no-images]
    Example: python parse_tattoofilter.py "https://www.tattoofilter.com/artists/evankim" "https://www.tattoofilter.com/artists/6dita"
    """
    import json
    import sys
    from dataclasses import asdict

    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    no_images = "--no-images" in sys.argv
    urls = args if args else ["https://www.tattoofilter.com/artists/1991.ink"]

    for i, url in enumerate(urls):
        if len(urls) > 1:
            print(f"\n--- [{i + 1}/{len(urls)}] {url} ---\n", file=sys.stderr)
        try:
            p = parse_artist_page(url, headless=True, max_images=50, metadata_only=no_images)
            if p:
                d = asdict(p)
                d["image_urls_count"] = len(p.image_urls)
                if no_images:
                    d["image_urls"] = []
                print(json.dumps(d, indent=2, ensure_ascii=False))
            else:
                print("{}")
        except Exception as e:
            print(json.dumps({"url": url, "error": str(e)}, indent=2), file=sys.stderr)
            if len(urls) == 1:
                sys.exit(1)
