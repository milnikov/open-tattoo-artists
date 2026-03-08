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


# Style keywords that appear in location blurb on the page (strip from country field).
LOCATION_STYLE_KEYWORDS = re.compile(
    r"\b(?:REALISM|BLACK\s+AND\s+GREY|BLACK\s+AND\s+GRAY|TRADITIONAL|ILLUSTRATIVE|BLACKWORK|"
    r"LINE\s+ART|FINE\s+LINE|MICRO-?REALISM|PORTRAIT|MINIMALIST|DOTWORK|TRIBAL|WATERCOLOR|"
    r"JAPANESE|GEOMETRIC|NEO-?TRADITIONAL|SINGLE\s+NEEDLE|SCRIPT|AMERICAN\s+TRADITIONAL)\b",
    re.I,
)

# Regions/states that map to a country (used so country holds only country name).
REGION_TO_COUNTRY = {
    "leinster": "Ireland",
    "munster": "Ireland",
    "connacht": "Ireland",
    "ulster": "Ireland",
    "greater london": "United Kingdom",
    "england": "United Kingdom",
    "scotland": "United Kingdom",
    "wales": "United Kingdom",
    "community of madrid": "Spain",
    "madrid": "Spain",
    "valencian community": "Spain",
    "catalonia": "Spain",
    "ontario": "Canada",
    "quebec": "Canada",
    "british columbia": "Canada",
    "alberta": "Canada",
    "province of trieste": "Italy",
    "trieste": "Italy",
    "latium": "Italy",
    "lazio": "Italy",
    "hesse": "Germany",
    "bavaria": "Germany",
    "new york": "United States",
    "california": "United States",
    "texas": "United States",
    "florida": "United States",
    "miami-dade": "United States",
    "queens": "United States",
    "new york city": "United States",
}

# Known country names (for city vs country: if only this is present, city=Unknown).
KNOWN_COUNTRIES = frozenset({
    "ireland", "united kingdom", "uk", "spain", "italy", "germany", "france", "portugal",
    "netherlands", "belgium", "poland", "austria", "switzerland", "greece", "romania",
    "united states", "usa", "canada", "mexico", "brazil", "argentina", "colombia", "chile",
    "australia", "new zealand", "japan", "south korea", "china", "india", "russia",
    "belarus", "ukraine", "czech republic", "hungary", "sweden", "norway", "denmark",
    "finland", "israel", "turkey", "south africa", "egypt", "thailand", "indonesia",
    "philippines", "malaysia", "singapore", "united arab emirates", "lebanon",
})

# Sponsor/brand and non-style tags to exclude from styles (substring or exact match, lower).
STYLE_BLOCKLIST = frozenset({
    "sponsor", "sponsor:", "killerinktattoo", "cheyenne_tattooequipment", "tattoodefender",
    "recoveryaftercare", "florence welch", "rihanna", "justin bieber", "ellie goulding",
    "celebrity couple", "celebrity couple tattoos", "couple tattoos",
})

# Known tattoo style phrases for splitting compounds (longer first). Normalized to slug.
COMPOUND_STYLE_PHRASES = [
    "black and grey", "black and gray", "micro-realism", "micro realism", "fine line",
    "line art", "neo-traditional", "neotraditional", "single needle", "blackwork",
    "american traditional", "black and grey realism", "black and gray realism",
    "realism", "traditional", "illustrative", "portrait", "minimalist", "dotwork",
    "tribal", "watercolor", "japanese", "geometric", "trash polka", "script",
    "stick and poke", "ignorant", "surrealism", "biomechanical", "ornamental",
]


def _strip_style_keywords_from_location(loc_line: str) -> str:
    """Remove style keywords from location string so country is not mixed with styles."""
    return LOCATION_STYLE_KEYWORDS.sub("", loc_line).strip().strip(",; ")


def _region_or_part_to_country(part: str) -> str:
    """Map region/state to country, or return part if it's already a country."""
    key = part.strip().lower()
    if key in REGION_TO_COUNTRY:
        return REGION_TO_COUNTRY[key]
    if key in KNOWN_COUNTRIES:
        return part.strip()
    # Normalize common variants
    if key in ("usa", "us"):
        return "United States"
    if key in ("uk", "great britain"):
        return "United Kingdom"
    return part.strip()


def _parse_location_parts(loc_clean: str) -> tuple[str, str]:
    """Return (city, country). City is 'Unknown' if only country is known."""
    parts = [p.strip() for p in re.split(r"[,;]", loc_clean) if p.strip()]
    if not parts:
        return "Unknown", "Unknown"
    # Single part: treat as country if known, else as city (country Unknown)
    if len(parts) == 1:
        one = parts[0][:80].strip()
        key = one.lower()
        if key in KNOWN_COUNTRIES or key in ("usa", "uk", "us"):
            return "Unknown", _region_or_part_to_country(one)
        return one, "Unknown"
    # Two or more: first = city, last = region or country
    city_candidate = parts[0][:80].strip()
    last_part = parts[-1][:80].strip()
    country = _region_or_part_to_country(last_part)
    # If first part is actually a country (e.g. "Belarus" in "Belarus, Something"), swap
    if city_candidate.lower() in KNOWN_COUNTRIES or city_candidate.lower() in ("usa", "uk", "us"):
        return "Unknown", _region_or_part_to_country(city_candidate)
    return city_candidate, country


def _is_blocked_style(text: str) -> bool:
    """True if this style label is sponsor/celebrity/theme and should be omitted."""
    low = text.strip().lower()
    for blocked in STYLE_BLOCKLIST:
        if blocked in low or low == blocked:
            return True
    return False


def _split_compound_style(text: str) -> list[str]:
    """Split e.g. 'black and grey micro-realism' into ['black&gray', 'micro-realism']."""
    low = text.strip().lower()
    if not low:
        return []
    result = []
    remaining = low
    # Sort by length desc so we match longer phrases first
    for phrase in sorted(COMPOUND_STYLE_PHRASES, key=len, reverse=True):
        if phrase not in remaining:
            continue
        # Extract this phrase and add normalized
        norm = _normalize_style(phrase)
        if norm and norm not in result:
            result.append(norm)
        remaining = remaining.replace(phrase, " ", 1).strip()
        remaining = re.sub(r"\s+", " ", remaining)
    if remaining and re.match(r"^[a-z0-9\s\-&]+$", remaining) and len(remaining) >= 2:
        norm = _normalize_style(remaining)
        if norm and norm not in result:
            result.append(norm)
    return result if result else [_normalize_style(low)]


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

        # Location: e.g. "room Manhattan, New York City" or "room Trieste, Province of Trieste".
        # Strip style keywords (REALISM, TRADITIONAL, etc.) so country is only country/region.
        city, country = "Unknown", "Unknown"
        try:
            body = (driver.find_element(By.TAG_NAME, "body").text or "")
            m = re.search(r"room\s*([\s\S]+?)(?=\s*[\d,]+\s*tattoos|\s*[\d,]+\s*likes|$)", body, re.I)
            if not m:
                m = re.search(r"room\s*([^\n]+)", body, re.I)
            if m:
                loc_line = m.group(1).strip()
                loc_clean = re.sub(r"[\U0001F1E0-\U0001F1FF\U0001F300-\U0001F9FF]", "", loc_line).strip()
                loc_clean = re.sub(r"\s+", " ", loc_clean).strip()
                loc_clean = _strip_style_keywords_from_location(loc_clean)
                if loc_clean:
                    city, country = _parse_location_parts(loc_clean)
        except Exception:
            pass

        # Styles: only real tattoo style slugs. Exclude sponsor/celebrity/theme; split compounds.
        styles = []
        seen = set()
        try:
            for a in driver.find_elements(By.XPATH, "//a[contains(@href, '/tattoos/')]"):
                text = (a.text or "").strip()
                if 2 <= len(text) <= 60 and not text.startswith("http"):
                    low = text.lower()
                    if low == "tattoos" or "'s tattoos" in low or low.endswith("'s tattoos"):
                        continue
                    if "tattoos" in low and ("'" in text or "’" in text):
                        continue
                    if _is_blocked_style(text):
                        continue
                    for norm in _split_compound_style(text):
                        if norm and norm not in seen:
                            seen.add(norm)
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
