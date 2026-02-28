"""
Reusable image extraction logic from download_artist.py.
Used by both download_artist and parse.py to ensure consistent tattoo image discovery.
"""

import json
import re
import time
import random
from selenium.webdriver.common.by import By


def extract_tattoo_ids(driver) -> set[str]:
    """Extract all tattoo IDs (MongoDB-style) from page source."""
    page_source = driver.page_source
    return set(re.findall(r"/tattoos/([a-f0-9]{24})", page_source, re.IGNORECASE))


def try_click_load_more(driver) -> bool:
    """Try to find and click Load More / Show More. Returns True if clicked."""
    try:
        # Scroll to bottom first so button is likely in view
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(0.5)
        # Strategy 1: XPath (aligned with download_artist - more selectors)
        for selector in [
            "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'load more')]",
            "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'show more')]",
            "//a[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'load more')]",
            "//*[@class='load-more']",
            "//*[@id='load-more']",
            "//button[contains(@class, 'load')]",
            "//*[contains(@class, 'load-more')]",
            "//*[contains(@class, 'show-more')]",
            "//button[contains(@class, 'more')]",
        ]:
            try:
                buttons = driver.find_elements(By.XPATH, selector)
                for btn in buttons:
                    if btn.is_displayed():
                        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btn)
                        time.sleep(0.5)
                        try:
                            btn.click()
                        except Exception:
                            driver.execute_script("arguments[0].click();", btn)
                        return True
            except Exception:
                pass
        # Strategy 2: Partial link text
        for text in ["Load More", "Show More"]:
            try:
                links = driver.find_elements(By.PARTIAL_LINK_TEXT, text)
                for link in links:
                    if link.is_displayed():
                        driver.execute_script("arguments[0].click();", link)
                        return True
            except Exception:
                pass
        # Strategy 3: JavaScript
        clicked = driver.execute_script("""
            var buttons = document.querySelectorAll('button, a, div[role="button"]');
            for (var i = 0; i < buttons.length; i++) {
                var btn = buttons[i];
                var text = (btn.textContent || '').toLowerCase();
                if (text.includes('load more') || text.includes('show more')) {
                    var rect = btn.getBoundingClientRect();
                    if (rect.width > 0 && rect.height > 0) {
                        btn.click();
                        return true;
                    }
                }
            }
            return false;
        """)
        return bool(clicked)
    except Exception:
        return False


def scroll_and_load_all(driver, max_iterations: int = 500, max_load_more_clicks: int = 120) -> set[str]:
    """
    Scroll page, click Load More, and collect tattoo IDs until no new ones appear.
    Targets 50+ images: scroll to bottom first so Load More is visible, then click.
    """
    # Wait for Tattoos tab content to render
    time.sleep(2)

    # Scroll both window and any scrollable containers (Angular may use overflow divs)
    def do_scroll_down():
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        driver.execute_script("""
            document.querySelectorAll('*').forEach(function(el) {
                if (el.scrollHeight > el.clientHeight && getComputedStyle(el).overflow !== 'visible')
                    el.scrollTop = el.scrollHeight;
            });
        """)

    # Initial phase: scroll multiple times to trigger lazy load + reveal Load More
    for _ in range(15):
        do_scroll_down()
        time.sleep(random.uniform(0.5, 1))
    time.sleep(2)
    previous_ids = extract_tattoo_ids(driver)

    consecutive_no_change = 0
    load_more_clicks = 0
    min_iterations = 80  # Ensure we don't stop before giving Load More a real chance

    for iteration in range(max_iterations):
        # Scroll to bottom FIRST so Load More button is in view
        do_scroll_down()
        time.sleep(1)

        clicked = try_click_load_more(driver)
        if clicked:
            load_more_clicks += 1
            time.sleep(6)  # Wait for new batch to load
            do_scroll_down()
            time.sleep(3)
            driver.execute_script("window.scrollBy(0, -800);")
            time.sleep(1)
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(3)

        driver.execute_script("window.scrollBy(0, 400);")
        time.sleep(random.uniform(0.5, 1))

        if iteration % 6 == 0:
            do_scroll_down()
            time.sleep(2.5)

        current_ids = extract_tattoo_ids(driver)
        if len(current_ids) > len(previous_ids):
            previous_ids = current_ids
            consecutive_no_change = 0
        else:
            consecutive_no_change += 1
            if iteration >= min_iterations:
                if consecutive_no_change >= 30 and load_more_clicks >= 3:
                    break
                if consecutive_no_change >= 45:
                    break

    # Final scroll pass
    driver.execute_script("window.scrollTo(0, 0);")
    time.sleep(1)
    for _ in range(50):
        driver.execute_script("window.scrollBy(0, 400);")
        time.sleep(0.1)
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(2)

    return previous_ids | extract_tattoo_ids(driver)


def extract_image_urls_comprehensive(driver, page_source: str, url: str, all_tattoo_ids: set[str]) -> set[str]:
    """Apply all extraction methods from download_artist and return tattoo image URLs."""
    all_urls = set()

    # Method 1: Comprehensive JS extraction
    extraction_js = """
    var results = new Set();
    document.querySelectorAll('img').forEach(function(img) {
        var sources = [img.src, img.dataset.src, img.dataset.lazySrc, img.dataset.original,
            img.dataset.lazy, img.dataset.url, img.getAttribute('data-src'),
            img.getAttribute('data-lazy-src'), img.getAttribute('data-original'),
            img.getAttribute('data-lazy'), img.getAttribute('data-url')];
        sources.forEach(function(s) {
            if (s && s.trim() && !s.startsWith('data:')) results.add(s.trim());
        });
    });
    document.querySelectorAll('*').forEach(function(el) {
        try {
            var bg = window.getComputedStyle(el).backgroundImage;
            if (bg && bg !== 'none' && bg !== 'initial') {
                var m = bg.match(/url\\(["']?([^"']*)["']?\\)/);
                if (m && m[1] && !m[1].startsWith('data:')) results.add(m[1]);
            }
        } catch(e) {}
    });
    return Array.from(results);
    """
    for u in driver.execute_script(extraction_js) or []:
        if u and u.strip():
            all_urls.add(u.strip())

    # Method 2: Direct img inspection
    for img in driver.find_elements(By.TAG_NAME, "img"):
        src = (
            img.get_attribute("src")
            or img.get_attribute("data-src")
            or img.get_attribute("data-lazy-src")
            or img.get_attribute("data-original")
            or img.get_attribute("data-lazy")
            or img.get_attribute("data-url")
        )
        if src and src.strip():
            if src.startswith("//"):
                src = "https:" + src
            elif src.startswith("/"):
                src = "https://tattooswizard.com" + src
            all_urls.add(src)

    # Method 3: Regex on page source
    patterns = [
        r"https?://cdn\.tattooswizard\.com/[^\"'\s<>]+",
        r"https?://[^\"'\s<>]*tattooswizard[^\"'\s<>]*/artists/[^\"'\s<>]+/tattoos/[^\"'\s<>]+",
        r"https?://storage\.googleapis\.com/[^\"'\s<>]+/artists/[^\"'\s<>]+/tattoos/[^\"'\s<>]+",
    ]
    for pattern in patterns:
        for m in re.finditer(pattern, page_source, re.IGNORECASE):
            u = m.group(0)
            u = re.sub(r"[,;)}>\]]+$", "", u)
            if u.startswith("http"):
                all_urls.add(u)

    # Method 4: Network logs
    try:
        for log in driver.get_log("performance"):
            try:
                msg = json.loads(log["message"])
                if msg.get("message", {}).get("method") == "Network.responseReceived":
                    resp_url = (
                        msg.get("message", {})
                        .get("params", {})
                        .get("response", {})
                        .get("url", "")
                    )
                    if "/tattoos/" in resp_url.lower():
                        all_urls.add(resp_url)
            except Exception:
                pass
    except Exception:
        pass

    # Method 5: Construct from tattoo IDs + artist ID
    artist_m = re.search(r"/artists/([a-f0-9]{24})", url) or re.search(
        r"/artists/([a-f0-9]{24})", page_source
    )
    if artist_m:
        aid = artist_m.group(1)
        base = "https://cdn.tattooswizard.com"
        for tid in all_tattoo_ids:
            all_urls.add(f"{base}/artists/{aid}/tattoos/{tid}")
        for tid in re.findall(r"/tattoos/([a-f0-9]{24})", page_source, re.IGNORECASE):
            all_urls.add(f"{base}/artists/{aid}/tattoos/{tid}")

    return all_urls


def filter_tattoo_images(all_urls: set[str]) -> list[str]:
    """Filter URLs to tattoo images only (same logic as download_artist)."""
    result = []
    ui_keywords = [
        "logo", "icon", "badge", "marker", "vector", "bag", "static/common",
        "avatar", "placeholder", "loading", "spinner", "arrow", "button", "close", "menu",
    ]
    for u in all_urls:
        if not u or u.startswith("data:"):
            continue
        ul = u.lower()
        if any(k in ul for k in ui_keywords):
            continue
        if any(ext in ul for ext in [".svg", ".ico", "favicon"]):
            continue
        is_tattoo = False
        if "/tattoos/" in ul:
            is_tattoo = True
        elif "tattooswizard" in ul:
            if not any(s in ul for s in ["logo", "icon", "badge", "avatar", "favicon", "placeholder", "static/common"]):
                is_tattoo = True
        elif re.search(r"\.(jpg|jpeg|png|webp)", ul):
            if not re.search(r"[_-](thumb|icon|small|mini|tiny|50x50|100x100)[_-]", ul):
                if any(i in ul for i in ["cdn", "storage", "images", "photos", "media"]):
                    is_tattoo = True
        if is_tattoo:
            result.append(u)
    return result
