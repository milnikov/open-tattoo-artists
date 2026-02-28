"""
Parse tattooswizard.com artist pages. Uses Selenium for JavaScript-rendered content.
Extracts: Instagram URL (required), name, location, styles, image URLs.
Reuses advanced image extraction from download_artist via tattooswizard_extractor.
"""

import re
import time
import random
from typing import Optional
from dataclasses import dataclass

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

from tattooswizard_extractor import (
    scroll_and_load_all,
    extract_image_urls_comprehensive,
    filter_tattoo_images,
)

try:
    from webdriver_manager.chrome import ChromeDriverManager
    USE_WEBDRIVER_MANAGER = True
except ImportError:
    USE_WEBDRIVER_MANAGER = False


@dataclass
class ParsedArtist:
    """Extracted artist data from a tattooswizard page."""
    instagram_url: str
    instagram_handle: str
    name: str
    city: str
    country: str
    styles: list[str]
    website: Optional[str] = None
    source_url: str = ""
    image_urls: list[str] = None

    def __post_init__(self):
        if self.image_urls is None:
            self.image_urls = []


def _create_driver(headless: bool = True):
    """Create headless Chrome driver with performance logging for network extraction."""
    opts = Options()
    if headless:
        opts.add_argument("--headless=new")
        opts.add_argument("--disable-gpu")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_argument(
        "--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    opts.set_capability("goog:loggingPrefs", {"performance": "ALL"})
    if USE_WEBDRIVER_MANAGER:
        service = Service(ChromeDriverManager().install())
        return webdriver.Chrome(service=service, options=opts)
    return webdriver.Chrome(options=opts)


def _extract_instagram_handle(url: str) -> Optional[str]:
    """Extract Instagram handle from URL."""
    if not url:
        return None
    url = url.strip().rstrip("/")
    m = re.search(r"instagram\.com/([a-zA-Z0-9_.]+)", url, re.IGNORECASE)
    if m:
        return m.group(1).lower()
    return None


def parse_artist_page(url: str, headless: bool = True, max_images: int = 50) -> Optional[ParsedArtist]:
    """
    Parse a tattooswizard artist page. Returns None if Instagram is not found (skip artist).
    Uses advanced image extraction (scroll + Load More + multi-method) from download_artist.
    """
    driver = None
    try:
        driver = _create_driver(headless=headless)
        driver.get(url)
        time.sleep(random.uniform(4, 6))

        # Capture page source for location BEFORE clicking Tattoos (About content in DOM)
        page_source_for_location = driver.page_source

        # Extract Instagram URL - required
        instagram_url = None
        links = driver.find_elements(By.TAG_NAME, "a")
        for a in links:
            try:
                href = a.get_attribute("href")
                if href and "instagram.com" in href.lower() and "/p/" not in href:
                    instagram_url = href
                    break
            except Exception:
                continue

        if not instagram_url:
            m = re.search(
                r'https?://(?:www\.)?instagram\.com/([a-zA-Z0-9_.]+)/?["\']',
                page_source_for_location,
                re.IGNORECASE,
            )
            if m:
                handle = m.group(1).lower()
                instagram_url = f"https://instagram.com/{handle}"

        if not instagram_url:
            return None

        handle = _extract_instagram_handle(instagram_url)
        if not handle:
            return None

        handle = re.sub(r"[^a-z0-9._]", "", handle)[:30]
        if not handle:
            return None

        # Name
        name = ""
        try:
            title = driver.title or ""
            if title and "|" in title:
                name = title.split("|")[0].strip()
        except Exception:
            pass
        if not name:
            slug = url.rstrip("/").split("/")[-1]
            name = slug.replace("_", " ").replace("-", " ").title()

        # Location: try multiple sources (header/About). Use initial page before Tattoos tab.
        city, country = "Unknown", "Unknown"

        def parse_loc_text(loc_text: str) -> tuple[str, str]:
            # Trim at UI words that indicate we've overshot the location
            for w in ("comment", "add message", "load more", "price", "resources"):
                idx = loc_text.lower().find(w)
                if idx >= 0:
                    loc_text = loc_text[:idx].strip().rstrip(",; ")
                    break
            parts = [p.strip() for p in re.split(r"[,;]", loc_text) if p.strip()]
            if len(parts) >= 2:
                city, country = parts[0][:80], parts[-1][:80]
                # Accept if country looks reasonable (short, mostly letters)
                if country and len(country) <= 50 and re.match(r"^[A-Za-z\s\-']+$", country):
                    return city, country
            if len(parts) == 1 and 2 <= len(parts[0]) <= 50:
                return parts[0][:80], "Unknown"
            return "Unknown", "Unknown"

        def normalize_html(html: str) -> str:
            """Replace tags with space so 'Current<span>location:</span>X' -> 'Current location: X'"""
            return re.sub(r"<[^>]+>", " ", html)

        # Primary: regex on normalized HTML (SSR has "Current location:" in About)
        normalized = normalize_html(page_source_for_location)
        m = re.search(r"Current\s+location\s*:\s*([^\n<]+)", normalized, re.IGNORECASE | re.DOTALL)
        if m:
            loc_text = m.group(1).strip()
            if len(loc_text) > 5:
                c, co = parse_loc_text(loc_text)
                if c != "Unknown" or co != "Unknown":
                    city, country = c, co
        if city == "Unknown":
            # Header: "Sainte-maxime, Provence-alpes-cote D'azur, France" before "11.8k"
            m = re.search(r"location\s+([^\n<]+?)(?=\s*\d+(?:\.\d+)?k?\b|\s*Add|$)", normalized, re.IGNORECASE | re.DOTALL)
            if m:
                cand = m.group(1).strip()
                if "," in cand and len(cand) > 5:
                    c, co = parse_loc_text(cand)
                    if c != "Unknown" or co != "Unknown":
                        city, country = c, co

        # Fallback: body text, try all matches and pick best (first with valid country)
        if city == "Unknown" and country == "Unknown":
            try:
                body_text = driver.find_element(By.TAG_NAME, "body").text
                for m in re.finditer(r"Current\s+location\s*:\s*([^\n]+)", body_text, re.IGNORECASE):
                    c, co = parse_loc_text(m.group(1).strip())
                    if c != "Unknown" and co != "Unknown" and len(co) < 30:
                        city, country = c, co
                        break
            except Exception:
                pass

        # Fallback: click About tab if location still missing (About may be lazy-loaded)
        if city == "Unknown" and country == "Unknown":
            try:
                about_tabs = driver.find_elements(By.PARTIAL_LINK_TEXT, "About")
                if about_tabs:
                    driver.execute_script("arguments[0].click();", about_tabs[0])
                    time.sleep(2)
                    about_src = driver.page_source
                    about_norm = normalize_html(about_src)
                    m = re.search(r"Current\s+location\s*:\s*([^\n<]+)", about_norm, re.IGNORECASE | re.DOTALL)
                    if m:
                        c, co = parse_loc_text(m.group(1).strip())
                        if c != "Unknown" or co != "Unknown":
                            city, country = c, co
                    # Switch back to Tattoos for image extraction
                    tabs = driver.find_elements(By.PARTIAL_LINK_TEXT, "Tattoos")
                    if tabs:
                        tabs[0].click()
                        time.sleep(random.uniform(2, 3))
                    page_source = driver.page_source
            except Exception:
                pass

        # Click Tattoos tab for image extraction and styles
        try:
            tabs = driver.find_elements(By.PARTIAL_LINK_TEXT, "Tattoos")
            if tabs:
                tabs[0].click()
                time.sleep(random.uniform(2, 3))
        except Exception:
            pass
        page_source = driver.page_source

        # Styles
        styles = []
        style_keywords = [
            "traditional", "neo-traditional", "realism", "watercolor", "tribal",
            "japanese", "blackwork", "dotwork", "geometric", "illustrative",
            "minimalist", "portrait", "anime", "fineline", "script", "lettering",
            "black and grey", "color", "surrealism", "abstract",
        ]
        page_lower = page_source.lower()
        for s in style_keywords:
            if s in page_lower:
                styles.append(s)

        # Website
        website = None
        for a in links:
            try:
                href = a.get_attribute("href")
                if not href or "instagram" in href or "facebook" in href or "twitter" in href:
                    continue
                if href.startswith("http") and "tattooswizard" not in href:
                    website = href
                    break
            except Exception:
                continue

        # Image URLs: reuse advanced extraction from download_artist
        all_tattoo_ids = scroll_and_load_all(driver)
        page_source = driver.page_source
        all_urls = extract_image_urls_comprehensive(driver, page_source, url, all_tattoo_ids)
        filtered = filter_tattoo_images(all_urls)
        image_urls = filtered[:max_images]
        print(f"  📷 Tattoo IDs: {len(all_tattoo_ids)} | Extracted URLs: {len(all_urls)} | Filtered: {len(filtered)} | Using: {len(image_urls)}")

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
        )
    except Exception as e:
        raise RuntimeError(f"Parse error for {url}: {e}") from e
    finally:
        if driver:
            driver.quit()
