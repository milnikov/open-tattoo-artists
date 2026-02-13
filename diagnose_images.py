#!/usr/bin/env python3
"""
Comprehensive diagnostic script to find all images on a tattooswizard artist page
"""

import sys
import re
import json
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import time

def diagnose_artist_page(url):
    chrome_options = Options()
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--window-size=1920,1080')
    
    driver = webdriver.Chrome(options=chrome_options)
    
    try:
        print(f"🔍 Diagnosing: {url}\n")
        driver.get(url)
        time.sleep(3)
        
        # Click Tattoos tab
        try:
            tattoos_links = driver.find_elements(By.PARTIAL_LINK_TEXT, "Tattoos")
            if tattoos_links:
                print("✅ Clicked Tattoos tab")
                tattoos_links[0].click()
                time.sleep(3)
        except:
            print("⚠️  Could not click Tattoos tab")
        
        # Scroll multiple times to trigger lazy loading
        print("\n📜 Scrolling to load images...")
        for i in range(30):
            driver.execute_script("window.scrollBy(0, 500);")
            time.sleep(0.3)
        
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)
        
        # Get page source
        page_source = driver.page_source
        
        # Method 1: All img elements
        print("\n" + "="*80)
        print("METHOD 1: Direct img element inspection")
        print("="*80)
        img_elements = driver.find_elements(By.TAG_NAME, "img")
        print(f"Total <img> tags found: {len(img_elements)}")
        
        img_sources = {}
        for i, img in enumerate(img_elements, 1):
            src = img.get_attribute('src')
            data_src = img.get_attribute('data-src')
            data_lazy = img.get_attribute('data-lazy-src')
            data_original = img.get_attribute('data-original')
            data_url = img.get_attribute('data-url')
            
            sources = {
                'src': src,
                'data-src': data_src,
                'data-lazy-src': data_lazy,
                'data-original': data_original,
                'data-url': data_url
            }
            
            # Get any non-empty source
            active_sources = [v for v in sources.values() if v and v.strip()]
            
            if active_sources:
                img_sources[i] = {
                    'sources': sources,
                    'active': active_sources[0] if active_sources else None
                }
        
        print(f"Images with valid sources: {len(img_sources)}")
        
        # Method 2: JavaScript comprehensive extraction
        print("\n" + "="*80)
        print("METHOD 2: JavaScript comprehensive extraction")
        print("="*80)
        
        js_result = driver.execute_script("""
        var results = {
            img_sources: [],
            background_images: [],
            data_attributes: [],
            all_urls: new Set()
        };
        
        // All img sources
        document.querySelectorAll('img').forEach(function(img) {
            var sources = [
                img.src,
                img.dataset.src,
                img.dataset.lazySrc,
                img.dataset.original,
                img.dataset.lazy,
                img.dataset.url,
                img.getAttribute('data-src'),
                img.getAttribute('data-lazy-src'),
                img.getAttribute('data-original')
            ];
            sources.forEach(function(s) {
                if (s && s.trim() && !s.startsWith('data:')) {
                    results.img_sources.push(s);
                    results.all_urls.add(s);
                }
            });
        });
        
        // Background images
        document.querySelectorAll('*').forEach(function(el) {
            try {
                var bg = window.getComputedStyle(el).backgroundImage;
                if (bg && bg !== 'none' && bg !== 'initial') {
                    var match = bg.match(/url\\(["']?([^"']*)["']?\\)/);
                    if (match && match[1] && !match[1].startsWith('data:')) {
                        results.background_images.push(match[1]);
                        results.all_urls.add(match[1]);
                    }
                }
            } catch(e) {}
        });
        
        // Check data attributes in containers
        document.querySelectorAll('[data-images], [data-gallery], [data-photos], [data-src]').forEach(function(el) {
            try {
                var data = el.dataset.images || el.dataset.gallery || el.dataset.photos || el.dataset.src;
                if (data && typeof data === 'string' && data.includes('http')) {
                    results.data_attributes.push(data);
                    results.all_urls.add(data);
                }
            } catch(e) {}
        });
        
        return {
            img_sources: Array.from(new Set(results.img_sources)),
            background_images: Array.from(new Set(results.background_images)),
            data_attributes: Array.from(new Set(results.data_attributes)),
            all_unique_urls: Array.from(results.all_urls)
        };
        """)
        
        print(f"JavaScript found {len(js_result['img_sources'])} img sources")
        print(f"JavaScript found {len(js_result['background_images'])} background images")
        print(f"JavaScript found {len(js_result['data_attributes'])} data attributes")
        print(f"Total unique URLs: {len(js_result['all_unique_urls'])}")
        
        # Method 3: Regex patterns in page source
        print("\n" + "="*80)
        print("METHOD 3: Regex patterns in page source")
        print("="*80)
        
        patterns = {
            'tattooswizard_cdn': r'https?://cdn\.tattooswizard\.com/[^"\'\s<>]+',
            'tattooswizard_any': r'https?://[^"\'\s<>]*tattooswizard[^"\'\s<>]+',
            'tattoos_path': r'https?://[^"\'\s<>]+/tattoos/[^"\'\s<>]+',
            'image_extensions': r'https?://[^"\'\s<>]+\.(jpg|jpeg|png|webp)(\?[^"\'\s<>]*)?',
        }
        
        regex_matches = {}
        for name, pattern in patterns.items():
            matches = re.findall(pattern, page_source, re.IGNORECASE)
            regex_matches[name] = matches
            print(f"{name}: {len(matches)} matches")
        
        # Combine all URLs
        all_urls = set()
        all_urls.update(js_result['all_unique_urls'])
        for matches in regex_matches.values():
            for match in matches:
                if isinstance(match, tuple):
                    match = match[0] if match[0] else ''
                if match and isinstance(match, str) and match.startswith('http'):
                    all_urls.add(match)
        
        print(f"\nTotal unique URLs from all methods: {len(all_urls)}")
        
        # Filter for tattoo images
        print("\n" + "="*80)
        print("FILTERING RESULTS")
        print("="*80)
        
        tattoo_urls = []
        excluded = []
        
        for url in sorted(all_urls):
            url_lower = url.lower()
            
            # Skip data URLs
            if url.startswith('data:'):
                excluded.append(('data_url', url))
                continue
            
            # Skip obvious UI elements
            ui_keywords = ['logo', 'icon', 'badge', 'avatar', 'favicon', 'placeholder', 'loading', 'spinner']
            if any(kw in url_lower for kw in ui_keywords):
                excluded.append(('ui_element', url))
                continue
            
            # Skip SVG/ICO
            if any(ext in url_lower for ext in ['.svg', '.ico']):
                excluded.append(('icon_format', url))
                continue
            
            # Check if it's a tattoo image
            is_tattoo = False
            
            if '/tattoos/' in url_lower:
                is_tattoo = True
            elif 'tattooswizard' in url_lower:
                if not any(kw in url_lower for kw in ['logo', 'icon', 'badge']):
                    is_tattoo = True
            elif re.search(r'\.(jpg|jpeg|png|webp)', url_lower):
                if not re.search(r'[_-](thumb|icon|small|mini|tiny)[_-]', url_lower):
                    is_tattoo = True
            
            if is_tattoo:
                tattoo_urls.append(url)
            else:
                excluded.append(('not_tattoo', url))
        
        print(f"\n✅ Tattoo image URLs found: {len(tattoo_urls)}")
        print(f"❌ Excluded URLs: {len(excluded)}")
        
        # Show tattoo URLs
        if tattoo_urls:
            print("\n📸 Tattoo Image URLs:")
            for i, url in enumerate(tattoo_urls, 1):
                print(f"  {i}. {url}")
        else:
            print("\n⚠️  No tattoo URLs found!")
            print("\nSample excluded URLs:")
            for reason, url in excluded[:10]:
                print(f"  [{reason}] {url[:100]}")
        
        # Save results
        results = {
            'url': url,
            'total_img_tags': len(img_elements),
            'js_img_sources': js_result['img_sources'],
            'js_background_images': js_result['background_images'],
            'regex_matches': {k: len(v) for k, v in regex_matches.items()},
            'all_urls_count': len(all_urls),
            'tattoo_urls': tattoo_urls,
            'excluded_count': len(excluded),
            'excluded_sample': excluded[:20]
        }
        
        with open('diagnosis_results.json', 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"\n💾 Results saved to diagnosis_results.json")
        
        return results
        
    finally:
        input("\nPress Enter to close browser...")
        driver.quit()

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python diagnose_images.py <artist_url>")
        print("Example: python diagnose_images.py 'https://tattooswizard.com/artists/youthless_'")
        sys.exit(1)
    
    diagnose_artist_page(sys.argv[1])

