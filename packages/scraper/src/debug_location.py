#!/usr/bin/env python3
"""Debug location extraction - save page source and test patterns."""
import re
import sys
from pathlib import Path

# Add parent for imports
sys.path.insert(0, str(Path(__file__).resolve().parent))

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options

try:
    from webdriver_manager.chrome import ChromeDriverManager
    from selenium.webdriver.chrome.service import Service
    service = Service(ChromeDriverManager().install())
except ImportError:
    service = None

def main():
    url = sys.argv[1] if len(sys.argv) > 1 else "https://tattooswizard.com/artists/0.5na"
    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    driver = webdriver.Chrome(service=service, options=opts) if service else webdriver.Chrome(options=opts)
    try:
        driver.get(url)
        import time
        time.sleep(5)
        html = driver.page_source
        body_text = driver.find_element(By.TAG_NAME, "body").text
        # Save for inspection
        Path("/tmp/debug_page.html").write_text(html[:50000])
        Path("/tmp/debug_body.txt").write_text(body_text[:5000])
        print("=== Body text (first 2000 chars) ===")
        print(body_text[:2000])
        print("\n=== Searching for 'Current location' in HTML ===")
        if "Current location" in html:
            idx = html.find("Current location")
            print("FOUND at index", idx)
            print("Context:", repr(html[max(0,idx-50):idx+150]))
        else:
            print("NOT FOUND in HTML")
        if "Current location" in body_text:
            print("\nFOUND in body text")
        else:
            print("\nNOT FOUND in body text")
        # Test normalize
        norm = re.sub(r"<[^>]+>", " ", html)
        m = re.search(r"Current\s+location\s*:\s*([^\n<]+)", norm, re.IGNORECASE | re.DOTALL)
        if m:
            print("Regex match:", repr(m.group(1)[:100]))
        else:
            print("Regex: no match")
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
