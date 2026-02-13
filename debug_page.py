#!/usr/bin/env python3
"""
Debug script to inspect what images are on a page
"""

import sys
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import time
import json

def debug_page(url):
    chrome_options = Options()
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--window-size=1920,1080')
    
    driver = webdriver.Chrome(options=chrome_options)
    
    try:
        print(f"Loading: {url}")
        driver.get(url)
        time.sleep(5)
        
        # Click Tattoos tab
        try:
            tattoos_links = driver.find_elements(By.PARTIAL_LINK_TEXT, "Tattoos")
            if tattoos_links:
                print("Clicking Tattoos tab...")
                tattoos_links[0].click()
                time.sleep(3)
        except:
            pass
        
        # Scroll a bit
        for i in range(20):
            driver.execute_script("window.scrollBy(0, 500);")
            time.sleep(0.5)
        
        # Get all images
        print("\n=== ALL IMG ELEMENTS ===")
        img_elements = driver.find_elements(By.TAG_NAME, "img")
        print(f"Total img tags: {len(img_elements)}")
        
        all_sources = []
        for i, img in enumerate(img_elements[:50], 1):  # First 50
            src = img.get_attribute('src')
            data_src = img.get_attribute('data-src')
            data_lazy = img.get_attribute('data-lazy-src')
            data_original = img.get_attribute('data-original')
            
            sources = [s for s in [src, data_src, data_lazy, data_original] if s]
            
            if sources:
                print(f"\n{i}. Image element:")
                for s in sources:
                    print(f"   - {s[:150]}")
                    all_sources.append(s)
        
        # JavaScript extraction
        print("\n=== JAVASCRIPT EXTRACTION ===")
        js_result = driver.execute_script("""
        var results = {
            img_srcs: [],
            bg_images: [],
            all_elements: []
        };
        
        // All img srcs
        document.querySelectorAll('img').forEach(function(img) {
            if (img.src) results.img_srcs.push(img.src);
            if (img.dataset.src) results.img_srcs.push(img.dataset.src);
            if (img.dataset.lazySrc) results.img_srcs.push(img.dataset.lazySrc);
        });
        
        // Background images
        document.querySelectorAll('*').forEach(function(el) {
            var bg = window.getComputedStyle(el).backgroundImage;
            if (bg && bg !== 'none') {
                var match = bg.match(/url\\(["']?([^"']*)["']?\\)/);
                if (match && match[1]) results.bg_images.push(match[1]);
            }
        });
        
        return results;
        """)
        
        print(f"JS found {len(js_result['img_srcs'])} img sources")
        print(f"JS found {len(js_result['bg_images'])} background images")
        
        # Filter for tattoo images
        print("\n=== FILTERING FOR TATTOO IMAGES ===")
        tattoo_urls = []
        for src in js_result['img_srcs']:
            src_lower = src.lower()
            if '/tattoos/' in src_lower or 'tattooswizard' in src_lower:
                if not any(skip in src_lower for skip in ['logo', 'icon', 'badge', 'avatar']):
                    tattoo_urls.append(src)
                    print(f"  ✓ {src[:150]}")
        
        print(f"\nFound {len(tattoo_urls)} tattoo image URLs")
        
        # Save to file
        with open('debug_output.json', 'w') as f:
            json.dump({
                'url': url,
                'total_img_tags': len(img_elements),
                'js_img_sources': js_result['img_srcs'][:100],
                'js_bg_images': js_result['bg_images'][:50],
                'tattoo_urls': tattoo_urls
            }, f, indent=2)
        
        print("\nSaved to debug_output.json")
        
        input("\nPress Enter to close...")
        
    finally:
        driver.quit()

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python debug_page.py <url>")
        sys.exit(1)
    
    debug_page(sys.argv[1])

