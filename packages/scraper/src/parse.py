"""
Parse tattooswizard.com artist pages. Uses Selenium for JavaScript-rendered content.
Extracts: Instagram URL (required), name, location, styles, bio, tattooing_since, image URLs.
Reuses advanced image extraction from download_artist via tattooswizard_extractor.
"""

import re
import time
import random
from typing import Optional
from dataclasses import dataclass

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

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
    instagram_url: Optional[str]  # None when artist has no Instagram (handle from URL slug)
    instagram_handle: str
    name: str
    city: str
    country: str
    styles: list[str]
    website: Optional[str] = None
    source_url: str = ""
    image_urls: list[str] = None
    bio: Optional[str] = None
    tattooing_since: Optional[str] = None

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
        try:
            service = Service(ChromeDriverManager().install())
            return webdriver.Chrome(service=service, options=opts)
        except Exception as e:
            # ChromeDriverManager can fail with "File is not a zip file" if CDN returns HTML/error
            if "zip" in str(e).lower() or "BadZipFile" in type(e).__name__:
                pass  # fall back to system chromedriver
            else:
                raise
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


def _get_about_section_text(html: str) -> str:
    """Extract the About section body text from page HTML (e.g. after clicking About tab)."""
    try:
        soup = BeautifulSoup(html, "lxml")
    except Exception:
        soup = BeautifulSoup(html, "html.parser")
    about_heading = soup.find("h2", string=re.compile(r"^\s*About\s*$", re.I))
    if not about_heading:
        about_heading = soup.find(string=re.compile(r"^\s*About\s*$", re.I))
        if about_heading:
            about_heading = about_heading.parent
    if not about_heading:
        return ""
    # Collect bio paragraphs after About until we hit Price / Current location / next section
    parts = []
    for elem in about_heading.find_all_next(["p", "div"]):
        if elem.find_previous("h2") and elem.find_previous("h2") != about_heading:
            break
        if elem.name == "p":
            text = elem.get_text(separator=" ", strip=True)
            if not text or len(text) < 20:
                continue
            if "Current location" in text or "Price:" in text or "Comment" == text.strip():
                break
            if _is_footer_text(text):
                continue
            parts.append(text)
    if parts:
        return " ".join(parts).strip()[:2000]
    # Fallback: take first long text block after About
    next_ = about_heading.find_next(string=True)
    if next_ and len(next_.strip()) > 50:
        return next_.strip()[:2000]
    return ""


# Footer/site boilerplate that must not be used as artist bio
_BIO_FOOTER_PHRASES = frozenset({
    "discover talented tattoo artists",
    "get tattoo inspiration delivered",
    "join 50,000+ tattoo enthusiasts",
    "browse designs",
    "get inspired by ready-made",
    "ai tattoo generator",
    "generate unique designs with ai",
    "find an artist",
    "connect with verified professionals",
    "estimate your cost",
    "read the blog",
    "popular cities",
    "tattoo styles",
    "traditional realism japanese",
    "resources",
    "contact us",
    "about us",
    "careers",
    "collaborate",
    "terms of service",
    "privacy policy",
    "© 2026",
    "all rights reserved",
})


def _is_footer_text(text: str) -> bool:
    """True if text looks like site footer/boilerplate, not artist bio."""
    low = text.lower()
    return any(phrase in low for phrase in _BIO_FOOTER_PHRASES)


def _bio_score(text: str) -> int:
    """Higher = more likely to be the real About bio (not footer)."""
    if not text or len(text) < 50:
        return 0
    low = text.lower()
    if _is_footer_text(text):
        return 0
    score = 0
    if low.startswith('"') or "nestled" in low or "premier destination" in low:
        score += 3
    if "studio" in low and "tattoo" in low:
        score += 2
    if "specializing" in low or "specializes" in low:
        score += 2
    if "tattoo artist" in low or "tattoo studio" in low:
        score += 1
    if "guatemala" in low or "location" in low or "based in" in low:
        score += 1
    return score


def _get_about_text_via_selenium(driver) -> str:
    """Fallback when HTML parsing fails: find visible bio in About tab, avoid footer."""
    candidates = []
    try:
        for xpath in [
            "//*[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'specializing')]",
            "//*[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'tattoo artist')]",
            "//*[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'renowned')]",
            "//*[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'master of')]",
            "//*[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'premier destination')]",
            "//*[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'nestled')]",
            "//*[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'tattoo studio')]",
        ]:
            for el in driver.find_elements(By.XPATH, xpath):
                try:
                    text = (el.text or "").strip()
                    if 80 <= len(text) <= 2500:
                        candidates.append(text)
                    if len(text) < 80:
                        parent = el.find_element(By.XPATH, "..")
                        if parent:
                            text = (parent.text or "").strip()
                            if 80 <= len(text) <= 2500:
                                candidates.append(text)
                except Exception:
                    continue
    except Exception:
        pass
    # Prefer text that looks like real bio (score), exclude footer
    scored = [(t, _bio_score(t)) for t in candidates if _bio_score(t) > 0]
    if scored:
        return _strip_bio_quotes(max(scored, key=lambda x: x[1])[0][:2000])
    # Fallback: longest candidate that is not footer
    non_footer = [t for t in candidates if not _is_footer_text(t)]
    if non_footer:
        return _strip_bio_quotes(max(non_footer, key=len)[:2000])
    return ""


def _extract_styles_from_about(about_text: str) -> list[str]:
    """Extract style list from About text: 'specializing in \'...\' styles' or 'styles of X, Y, and Z'."""
    if not about_text:
        return []
    # Match: specializing in '...' or "..." (quoted list)
    m = re.search(r"specializ(?:ing|es)\s+in\s+['\"]([^'\"]+)['\"]", about_text, re.IGNORECASE)
    if m:
        raw = m.group(1).strip()
        return [_normalize_style(s.strip()) for s in re.split(r"[,;]", raw) if s.strip()]
    # Match: "styles of X, Y, and Z" or "styles of X, Y and Z" (unquoted)
    m = re.search(
        r"styles?\s+of\s+([^.]+?)(?:\.|designs?|$)",
        about_text,
        re.IGNORECASE | re.DOTALL,
    )
    if m:
        raw = m.group(1).strip()
        # Split on comma and " and "; normalize each
        parts = re.split(r"\s+and\s+|\s*,\s*", raw)
        result = []
        for s in parts:
            s = s.strip()
            if s:
                norm = _normalize_style(s)
                if norm and norm in _KNOWN_STYLE_SLUGS:
                    result.append(norm)
        if result:
            return result
    # Fallback: look for known style slugs mentioned in the about text
    about_lower = about_text.lower()
    found = []
    for slug in _KNOWN_STYLE_SLUGS:
        escaped = re.escape(slug).replace(r"\&", r"\s*&\s*")
        pattern = r"\b" + escaped + r"\b"
        if re.search(pattern, about_lower):
            found.append(_normalize_style(slug))
    return list(dict.fromkeys(found))  # preserve order, dedupe


# Single words that are not style names (header segment noise)
_HEADER_WORD_BLOCKLIST = frozenset({"add", "message", "load", "more", "fine", "and", "the", "in", "or", "by"})

# UI/nav text that must never be treated as artist styles (from DOM fallback)
_UI_STYLE_BLOCKLIST = frozenset({
    "try free", "sign in", "message", "tattoos", "about", "reviews", "illustrations",
    "load more", "add message", "generate designs free", "find artists", "design tools",
    "by location", "by style", "browse studios", "ai tattoo generator", "custom tattoo design",
    "flash tattoos", "price calculator", "for artists", "free artist profile", "blog", "join as artist",
    "comment", "resources", "explore", "browse designs", "get a custom design", "estimate your cost",
    "read the blog", "follow", "subscribe", "follow us", "contact", "careers", "collaborate",
})

# Known tattoo style slugs: DOM fallback only returns text that normalizes to one of these
_KNOWN_STYLE_SLUGS = frozenset({
    "traditional", "neo-traditional", "realism", "watercolor", "tribal", "japanese",
    "blackwork", "dotwork", "geometric", "illustrative", "minimalist", "portrait",
    "anime", "fineline", "script", "lettering", "black&gray", "black and grey", "black and gray",
    "color", "surrealism", "abstract", "fine line", "floral",
})


def _extract_styles_from_dom(driver) -> list[str]:
    """Extract style pills from the artist header. Pills sit between 'Add Message' and the tab row.
    Uses the header block element text (not full body) so order is reliable.
    """
    segment = _get_header_segment_for_styles(driver)
    if not segment:
        return []
    segment_lower = segment.lower().strip()
    if len(segment_lower) > 500:
        return []
    raw_tokens = re.split(r"[\s,]+", segment_lower)
    seen = set()
    result = []
    for token in raw_tokens:
        token = token.strip()
        if not token or len(token) < 2 or len(token) > 30:
            continue
        if token in _UI_STYLE_BLOCKLIST or token in _HEADER_WORD_BLOCKLIST or token in _TAB_ROW_WORDS:
            continue
        if re.match(r"^\d", token):
            continue
        normalized = _normalize_style(token)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        result.append(normalized)
    return result[:15]


def _get_header_segment_for_styles(driver) -> str:
    """Get the text between 'Add Message' and the tab row from the header block (not full body)."""
    try:
        # Find the element that contains "Add Message" (the button/link in the artist card)
        add_el = driver.find_elements(
            By.XPATH,
            "//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'add message')]",
        )
        if not add_el:
            # Fallback: use body text
            body_text = driver.find_element(By.TAG_NAME, "body").text or ""
            return _segment_from_full_text(body_text)
        el = add_el[0]
        # Go up to a container that includes the pills (often 2–4 levels: button -> div -> section/card)
        for _ in range(6):
            try:
                parent = el.find_element(By.XPATH, "..")
                if not parent:
                    break
                el = parent
                text = (el.text or "").strip()
                if not text or len(text) < 10:
                    continue
                # This block should contain "Add Message" and ideally the pills; may also contain tab names
                out = _segment_from_full_text(text)
                if out and len(out) > 2:
                    return out
            except Exception:
                break
    except Exception:
        pass
    # Fallback: full body
    try:
        return _segment_from_full_text(driver.find_element(By.TAG_NAME, "body").text or "")
    except Exception:
        return ""


# Tab row words to exclude from style pills (they may appear in any order in the header block)
_TAB_ROW_WORDS = frozenset({"tattoos", "about", "reviews", "illustrations", "load", "more"})


def _segment_from_full_text(text: str) -> str:
    """From a block of text, return the part after 'add message' and before the tab row.
    On the page, 'Add' and 'Message' are often on separate lines, so we match add\\s+message.
    Stop at the first line that is a tab word (Tattoos, About, Reviews, Illustrations, Load More)
    so we only get the style pills (fineline, dotwork, floral), not the newsletter/footer text.
    If 'add message' is missing (e.g. cookie wall or layout change), fall back to text before tab row.
    """
    if not text:
        return ""
    m = re.search(r"\badd\s+message\b", text, re.IGNORECASE | re.DOTALL)
    if m:
        after = text[m.end() :].strip()
        lines = []
        for line in after.split("\n"):
            line = line.strip()
            if not line:
                continue
            if _is_tab_row_line(line):
                break
            if _is_consent_or_banner_line(line):
                break
            lines.append(line)
        return " ".join(lines[:20])  # max 20 lines of pills
    # Fallback: page may not show "add message" (cookie banner, layout change). Use text before tab row.
    return _segment_before_tab_row(text)


def _is_tab_row_line(line: str) -> bool:
    """True if this line is a tab row label (e.g. 'Tattoos', 'About', '- Illustrations', 'Load More')."""
    if not line:
        return False
    clean = re.sub(r"^[\s\-\.\d]+", "", line).strip().lower()
    if not clean:
        return False
    if clean in _TAB_ROW_WORDS:
        return True
    first_word = clean.split()[0] if clean else ""
    return first_word in _TAB_ROW_WORDS


# Cookie/consent banner phrases: stop segment here so we don't blow the 500-char limit
_CONSENT_LINE_PHRASES = frozenset({
    "welcome to", "consent", "manage options", "your personal data", "cookies",
    "personal data", "store and/or access", "list of partners", "privacy and cookie",
})


def _is_consent_or_banner_line(line: str) -> bool:
    """True if this line looks like cookie/consent banner text (stop segment before it)."""
    if not line or len(line) < 10:
        return False
    lower = line.strip().lower()
    return any(phrase in lower for phrase in _CONSENT_LINE_PHRASES)


def _segment_before_tab_row(text: str, max_chars: int = 800) -> str:
    """Return the first chunk of text before we hit a tab-row word (Tattoos, About, etc.)
    or cookie/consent banner. Used when 'add message' is not present.
    """
    if not text:
        return ""
    lines = []
    for line in text.split("\n"):
        line = line.strip()
        if not line:
            continue
        if _is_tab_row_line(line):
            break
        if _is_consent_or_banner_line(line):
            break
        lines.append(line)
        if sum(len(l) for l in lines) > max_chars:
            break
    return " ".join(lines[:25])


def _normalize_style(s: str) -> str:
    """Normalize style string to lowercase slug; keep 'black&gray' etc."""
    s = s.strip().lower()
    if not s:
        return ""
    # Common variants -> canonical
    if s in ("black and grey", "black and gray"):
        return "black&gray"
    return s


def _strip_bio_quotes(text: str) -> str:
    """Remove surrounding double quotes from bio (e.g. \"Luis Escobar's...\" -> Luis Escobar's...)."""
    if not text or len(text) < 2:
        return text
    t = text.strip()
    if t.startswith('"') and t.endswith('"'):
        return t[1:-1].strip()
    return t


def _strip_leading_nav_from_bio(text: str) -> str:
    """Remove leading tab row / nav lines (Tattoos, About, Reviews, etc.) from bio text."""
    if not text:
        return text
    lines = text.strip().split("\n")
    start = 0
    for i, line in enumerate(lines):
        line_clean = re.sub(r"^[\s\-\.\d]+", "", line).strip().lower()
        if not line_clean:
            continue
        # Keep line if it looks like real bio (long enough, or contains comma/sentence)
        if len(line_clean) >= 40 or "," in line:
            start = i
            break
        if line_clean in _TAB_ROW_WORDS or line_clean in ("about", "load", "more"):
            start = i + 1
            continue
        start = i
        break
    return "\n".join(lines[start:]).strip()[:2000]


def _extract_bio_from_about(about_text: str) -> Optional[str]:
    """Extract the main bio paragraph from About section text."""
    if not about_text or len(about_text) < 30:
        return None
    bio = _strip_leading_nav_from_bio(about_text.strip()[:2000])
    if len(bio) < 30:
        return None
    return _strip_bio_quotes(bio)


def _extract_tattooing_since_from_about(about_text: str) -> Optional[str]:
    """Extract 'tattooing since YYYY' or 'since YYYY' from About text."""
    if not about_text:
        return None
    m = re.search(r"tattooing\s+since\s+(\d{4})\b", about_text, re.IGNORECASE)
    if m:
        return m.group(1)
    m = re.search(r"\bsince\s+(\d{4})\b", about_text, re.IGNORECASE)
    if m:
        return m.group(1)
    return None


def _dismiss_consent_banner(driver) -> None:
    """Click the consent/cookie banner button so the page (e.g. About tab) is visible."""
    try:
        time.sleep(1)
        for label in ("consent", "accept", "accept all", "allow all", "i agree", "agree"):
            try:
                # Match by element's full text (including descendants)
                xpath = (
                    "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '%s')]"
                    " | //a[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '%s')]"
                    " | //*[@role='button'][contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '%s')]"
                ) % (label, label, label)
                els = driver.find_elements(By.XPATH, xpath)
                for el in els[:3]:
                    try:
                        if el.is_displayed() and el.is_enabled():
                            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
                            time.sleep(0.3)
                            driver.execute_script("arguments[0].click();", el)
                            time.sleep(2)
                            return
                    except Exception:
                        continue
            except Exception:
                continue
        # Fallback: any button/link whose .text is exactly "Consent"
        for tag in ("button", "a"):
            for el in driver.find_elements(By.TAG_NAME, tag):
                try:
                    if (el.text or "").strip().lower() == "consent" and el.is_displayed() and el.is_enabled():
                        driver.execute_script("arguments[0].click();", el)
                        time.sleep(2)
                        return
                except Exception:
                    continue
    except Exception:
        pass


def parse_artist_page(
    url: str,
    headless: bool = True,
    max_images: int = 50,
    metadata_only: bool = False,
    debug: bool = False,
) -> Optional[ParsedArtist]:
    """
    Parse a tattooswizard artist page. Returns None if Instagram is not found (skip artist).
    Uses advanced image extraction (scroll + Load More + multi-method) from download_artist.
    If metadata_only=True, skips image extraction (for JSON-only updates).
    If debug=True, prints intermediate extraction values to stderr.
    """
    driver = None
    try:
        driver = _create_driver(headless=headless)
        driver.get(url)
        time.sleep(random.uniform(4, 6))

        # Dismiss cookie/consent banner so artist content and About tab are visible
        _dismiss_consent_banner(driver)

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

        # Use Instagram handle if found, else URL slug as ID (include artists without Instagram)
        if instagram_url:
            handle = _extract_instagram_handle(instagram_url)
            if handle:
                handle = re.sub(r"[^a-z0-9._]", "", handle)[:30]
        if not instagram_url or not handle:
            # Fallback: use slug from URL (e.g. /artists/0.5na -> 0.5na)
            slug = url.rstrip("/").split("/")[-1]
            handle = re.sub(r"[^a-z0-9._-]", "", slug.lower().replace("-", "_"))[:30]
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
            except Exception:
                pass

        # Styles: wait for page to be ready (any of: "add message", Tattoos tab, About tab).
        try:
            def _page_ready(d):
                if d.find_elements(
                    By.XPATH,
                    "//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'add message')]",
                ):
                    return True
                if d.find_elements(By.PARTIAL_LINK_TEXT, "Tattoos"):
                    return True
                if d.find_elements(By.PARTIAL_LINK_TEXT, "About"):
                    return True
                return False

            WebDriverWait(driver, 15).until(_page_ready)
            # Give header/style pills time to render (they can load after the tab row)
            time.sleep(1.5)
        except Exception as e:
            if debug:
                import sys
                print(f"[DEBUG] Wait failed: {e}", file=sys.stderr)
            pass
        header_segment = _get_header_segment_for_styles(driver)
        header_styles = _extract_styles_from_dom(driver)
        if debug:
            import sys
            body_preview = (driver.find_element(By.TAG_NAME, "body").text or "")[:2000]
            print(f"[DEBUG] body.text length={len(body_preview)}", file=sys.stderr)
            print(f"[DEBUG] body.text preview:\n{body_preview!r}", file=sys.stderr)
            print(f"[DEBUG] header_segment={header_segment!r}", file=sys.stderr)
            print(f"[DEBUG] header_styles={header_styles}", file=sys.stderr)

        # About text lives on the About tab — must click it to load content
        about_section_text = ""
        try:
            # Dismiss consent again if still visible so About tab is findable/clickable
            _dismiss_consent_banner(driver)
            # Prefer the artist tab "About" (exact text), not footer "About Us"
            about_tabs = driver.find_elements(
                By.XPATH,
                "//a[normalize-space(.)='About' or normalize-space(.)='About ']",
            )
            if not about_tabs:
                about_tabs = driver.find_elements(By.PARTIAL_LINK_TEXT, "About")
            if debug:
                import sys
                print(f"[DEBUG] about_tabs count={len(about_tabs)}", file=sys.stderr)
            if about_tabs:
                driver.execute_script("arguments[0].click();", about_tabs[0])
                time.sleep(3)  # give About panel time to render
                about_section_text = _get_about_section_text(driver.page_source)
                if not about_section_text or len(about_section_text) < 50:
                    about_section_text = _get_about_text_via_selenium(driver)
            if debug:
                import sys
                print(f"[DEBUG] about_section_text length={len(about_section_text)}", file=sys.stderr)
                print(f"[DEBUG] about_section_text preview:\n{(about_section_text or '')[:800]!r}", file=sys.stderr)
        except Exception as e:
            if debug:
                import sys
                print(f"[DEBUG] About section error: {e}", file=sys.stderr)
            pass

        # Prefer header pills (they're the visible source of truth); fallback to About text
        styles = header_styles if header_styles else _extract_styles_from_about(about_section_text)
        normalized = [_normalize_style(s) for s in styles if s]
        styles = list(dict.fromkeys(s for s in normalized if s))

        bio = _extract_bio_from_about(about_section_text)
        tattooing_since = _extract_tattooing_since_from_about(about_section_text)

        # Now switch to Tattoos tab for image extraction (or just for consistent state)
        try:
            tabs = driver.find_elements(By.PARTIAL_LINK_TEXT, "Tattoos")
            if tabs:
                tabs[0].click()
                time.sleep(random.uniform(2, 3))
        except Exception:
            pass
        page_source = driver.page_source

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

        image_urls = []
        if not metadata_only:
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
            bio=bio,
            tattooing_since=tattooing_since,
        )
    except Exception as e:
        raise RuntimeError(f"Parse error for {url}: {e}") from e
    finally:
        if driver:
            driver.quit()
