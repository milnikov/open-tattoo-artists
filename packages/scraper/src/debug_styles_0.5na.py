#!/usr/bin/env python3
"""One-off debug: load 0.5na, print header segment and extracted styles. Run from repo root."""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from selenium.webdriver.common.by import By

# Use same driver creation as parse.py (ChromeDriverManager for correct Chrome version)
from parse import _create_driver, _get_header_segment_for_styles, _extract_styles_from_dom

def main():
    driver = _create_driver(headless=True)
    try:
        url = "https://tattooswizard.com/artists/0.5na"
        driver.get(url)
        time.sleep(6)
        segment = _get_header_segment_for_styles(driver)
        styles = _extract_styles_from_dom(driver)
        print("=== Header segment (repr) ===")
        print(repr(segment))
        print("\n=== Extracted styles ===")
        print(styles)
        # Also dump body text snippet
        body = (driver.find_element(By.TAG_NAME, "body").text or "")[:1500]
        print("\n=== Body text (first 1500 chars) ===")
        print(repr(body))
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
