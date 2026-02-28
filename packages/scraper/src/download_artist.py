#!/usr/bin/env python3
__version__ = "2.4.0"

import sys
import requests
import os
import time
import re
import argparse
import traceback
import random
import json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
try:
    from webdriver_manager.chrome import ChromeDriverManager
    USE_WEBDRIVER_MANAGER = True
except ImportError:
    USE_WEBDRIVER_MANAGER = False
import datetime

def download_artist_portfolio(url, output_folder, headless=True, interactive=False, debug=True):
    """
    Download all tattoo images from an artist's page using our proven approach
    
    Args:
        url (str): URL of the artist's page
        output_folder (str): Folder to save images
        headless (bool): Run browser in headless mode
        interactive (bool): Wait for user input at key steps
        debug (bool): Save debug information
    """
    start_time = datetime.datetime.now()
    print(f"🕒 Script started at: {start_time}")
    print(f"📁 Script version: {__version__}")
    
    os.makedirs(output_folder, exist_ok=True)
    
    # Setup Chrome options with enhanced headless support
    chrome_options = Options()
    if headless:
        chrome_options.add_argument('--headless=new')  # Use new headless mode
        chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    chrome_options.add_argument('--disable-extensions')
    chrome_options.add_argument('--disable-software-rasterizer')
    chrome_options.add_argument('--disable-background-timer-throttling')
    chrome_options.add_argument('--disable-backgrounding-occluded-windows')
    chrome_options.add_argument('--disable-renderer-backgrounding')
    chrome_options.add_argument('--disable-features=TranslateUI')
    chrome_options.add_argument('--disable-ipc-flooding-protection')
    # Enable JavaScript and images (needed for tattoo images)
    prefs = {
        'profile.managed_default_content_settings.images': 1,
        'profile.default_content_setting_values.notifications': 2,
    }
    chrome_options.add_experimental_option('prefs', prefs)
    
    # Enable performance logging to capture network requests
    chrome_options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})
    
    driver = None
    try:
        print(f"🚀 Loading artist page: {url}")
        # Use ChromeDriverManager if available, otherwise use system ChromeDriver
        if USE_WEBDRIVER_MANAGER:
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)
        else:
            driver = webdriver.Chrome(options=chrome_options)
        driver.get(url)
        # Random initial wait to avoid detection patterns
        time.sleep(random.uniform(2, 4))
        
        # Click on Tattoos tab
        try:
            tattoos_links = driver.find_elements(By.PARTIAL_LINK_TEXT, "Tattoos")
            if tattoos_links:
                print("👉 Clicking on Tattoos tab...")
                tattoos_links[0].click()
                # Random wait after clicking
                time.sleep(random.uniform(2, 4))
        except Exception as e:
            print(f"⚠ Could not click Tattoos tab: {e}")
        
        # Intelligent scrolling to load all images - checks for new images
        print("🔄 Scrolling to load all images (intelligent detection)...")
        
        def get_current_image_count():
            """Helper function to count current tattoo images - improved detection"""
            js_script = """
            var urls = new Set();
            // Get all img elements - be more permissive
            document.querySelectorAll('img').forEach(function(img) {
                var src = img.src || img.dataset.src || img.dataset.lazySrc || img.dataset.original || 
                         img.getAttribute('data-original') || img.dataset.lazy || img.dataset.url;
                if (src && src.length > 0 && !src.startsWith('data:')) {
                    var lowerSrc = src.toLowerCase();
                    // Exclude only obvious non-images
                    if (!lowerSrc.includes('logo') && 
                        !lowerSrc.includes('icon') && 
                        !lowerSrc.includes('avatar') &&
                        !lowerSrc.includes('badge') &&
                        !lowerSrc.includes('favicon') &&
                        !lowerSrc.endsWith('.svg') &&
                        !lowerSrc.endsWith('.ico')) {
                        // Check if image is visible and has reasonable size
                        try {
                            var rect = img.getBoundingClientRect();
                            if (rect.width > 50 && rect.height > 50) {  // Lowered threshold
                                urls.add(src);
                            }
                        } catch(e) {
                            // If we can't get size, include it anyway if it looks like an image
                            if (lowerSrc.match(/\\.(jpg|jpeg|png|webp)/i) || lowerSrc.includes('tattooswizard') || lowerSrc.includes('cdn')) {
                                urls.add(src);
                            }
                        }
                    }
                }
            });
            // Also check background images
            var allElements = document.querySelectorAll('*');
            allElements.forEach(function(el) {
                try {
                    var bg = window.getComputedStyle(el).backgroundImage;
                    if (bg && bg !== 'none' && bg !== 'initial') {
                        var match = bg.match(/url\\(["']?([^"']*)["']?\\)/);
                        if (match && match[1] && !match[1].startsWith('data:')) {
                            var bgUrl = match[1];
                            var lowerBgUrl = bgUrl.toLowerCase();
                            if (!lowerBgUrl.includes('logo') && 
                                !lowerBgUrl.includes('icon') &&
                                (lowerBgUrl.includes('/tattoos/') || lowerBgUrl.includes('tattooswizard') || lowerBgUrl.match(/\\.(jpg|jpeg|png|webp)/i))) {
                                urls.add(bgUrl);
                            }
                        }
                    }
                } catch(e) {}
            });
            return urls.size;
            """
            return driver.execute_script(js_script)
        
        # Initial wait for page to load
        time.sleep(2)
        previous_count = get_current_image_count()
        print(f"  Initial image count: {previous_count}")
        
        max_scrolls = 200  # Maximum scroll attempts
        no_change_count = 0
        no_change_threshold = 20  # Increased threshold - don't stop too early
        scroll_attempts = 0
        min_scrolls = 30  # Always scroll at least this many times (same as diagnostic)
        
        # Scroll down intelligently
        while scroll_attempts < max_scrolls:
            # Scroll down
            driver.execute_script("window.scrollBy(0, 500);")
            time.sleep(random.uniform(0.4, 0.8))  # Random delay to avoid detection
            
            # Check for new images (but don't stop too early)
            if scroll_attempts >= min_scrolls:  # Only check after minimum scrolls
                current_count = get_current_image_count()
                
                if current_count > previous_count:
                    print(f"  Found {current_count} images (was {previous_count})...")
                    previous_count = current_count
                    no_change_count = 0  # Reset counter when we find new images
                else:
                    no_change_count += 1
                    if no_change_count >= no_change_threshold:
                        print(f"  No new images found after {no_change_count} scrolls")
                        break
            
            scroll_attempts += 1
            
            # Periodically scroll to bottom to trigger any lazy loading
            if scroll_attempts % 20 == 0:
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)
                # Check again after scrolling to bottom
                current_count = get_current_image_count()
                if current_count > previous_count:
                    print(f"  Found {current_count} images after scrolling to bottom...")
                    previous_count = current_count
                    no_change_count = 0
        
        # Scroll back to top and do one more pass
        print("  Final verification pass...")
        driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(2)
        
        # One more scroll down to catch any remaining images
        for i in range(30):
            driver.execute_script("window.scrollBy(0, 500);")
            time.sleep(0.3)
        
        # Final scroll to bottom
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)
        
        final_count = get_current_image_count()
        print(f"  Final image count: {final_count}")
        print(f"  Total scrolls: {scroll_attempts}")
        
        # Wait a bit more for all images to load
        print("\n⏳ Waiting for all images to fully load...")
        time.sleep(3)
        
        # Aggressive approach: Continuous scrolling + "Load More" clicking + periodic extraction
        print("\n🔄 Aggressively loading all images (scrolling + Load More + extraction)...")
        
        # Helper function to extract tattoo IDs from page source
        def extract_tattoo_ids():
            """Extract all tattoo IDs from page source"""
            page_source = driver.page_source
            tattoo_id_pattern = r'/tattoos/([a-f0-9]{24})'
            tattoo_ids = set(re.findall(tattoo_id_pattern, page_source, re.IGNORECASE))
            return tattoo_ids
        
        # Helper function to count current images
        def count_loaded_images():
            return len(extract_tattoo_ids())
        
        previous_tattoo_ids = extract_tattoo_ids()
        previous_image_count = len(previous_tattoo_ids)
        print(f"  Initial tattoo IDs found: {previous_image_count}")
        
        max_iterations = 500  # Increased significantly
        load_more_clicks = 0
        consecutive_no_change = 0
        max_consecutive_no_change = 20  # Need 20 consecutive failures before stopping
        
        for iteration in range(max_iterations):
            # ALWAYS try to click "Load More" button first (it might reappear)
            clicked_load_more = False
            
            # Try multiple strategies to find and click "Load More"
            # Strategy 1: XPath selectors
            load_more_selectors = [
                "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'load more')]",
                "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'show more')]",
                "//a[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'load more')]",
                "//*[@class='load-more']",
                "//*[@id='load-more']",
                "//button[contains(@class, 'load')]",
                "//*[contains(@class, 'load-more')]",
                "//*[contains(@class, 'show-more')]",
                "//button[contains(@class, 'more')]",
            ]
            
            for selector in load_more_selectors:
                try:
                    buttons = driver.find_elements(By.XPATH, selector)
                    for btn in buttons:
                        try:
                            # Check if button exists and is interactable
                            if btn and btn.is_displayed():
                                # Try to enable it if disabled
                                try:
                                    if not btn.is_enabled():
                                        driver.execute_script("arguments[0].disabled = false;", btn)
                                except:
                                    pass
                                
                                driver.execute_script("arguments[0].scrollIntoView({behavior: 'instant', block: 'center'});", btn)
                                time.sleep(0.5)
                                
                                # Try multiple click methods
                                try:
                                    btn.click()
                                except:
                                    driver.execute_script("arguments[0].click();", btn)
                                
                                time.sleep(5)  # Wait longer for new content to load
                                load_more_clicks += 1
                                clicked_load_more = True
                                
                                # Scroll after clicking
                                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                                time.sleep(3)
                                
                                # Scroll back up a bit and down again to trigger lazy loading
                                driver.execute_script("window.scrollBy(0, -500);")
                                time.sleep(1)
                                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                                time.sleep(2)
                                
                                # Check for new tattoo IDs
                                current_tattoo_ids = extract_tattoo_ids()
                                current_count = len(current_tattoo_ids)
                                if current_count > previous_image_count:
                                    print(f"  Click #{load_more_clicks}: Found {current_count} tattoo IDs (was {previous_image_count})")
                                    previous_tattoo_ids = current_tattoo_ids
                                    previous_image_count = current_count
                                    consecutive_no_change = 0
                                
                                if load_more_clicks % 5 == 0:
                                    print(f"  Clicked 'Load More' {load_more_clicks} times...")
                                break
                        except Exception as e:
                            pass
                    if clicked_load_more:
                        break
                except:
                    pass
            
            # Strategy 2: Try finding by partial link text
            if not clicked_load_more:
                try:
                    load_more_links = driver.find_elements(By.PARTIAL_LINK_TEXT, "Load More")
                    load_more_links.extend(driver.find_elements(By.PARTIAL_LINK_TEXT, "Show More"))
                    load_more_links.extend(driver.find_elements(By.PARTIAL_LINK_TEXT, "More"))
                    for link in load_more_links:
                        try:
                            if link.is_displayed():
                                driver.execute_script("arguments[0].scrollIntoView(true);", link)
                                time.sleep(0.5)
                                driver.execute_script("arguments[0].click();", link)
                                time.sleep(5)
                                load_more_clicks += 1
                                clicked_load_more = True
                                print(f"  Clicked 'Load More' link #{load_more_clicks}")
                                break
                        except:
                            pass
                except:
                    pass
            
            # Strategy 3: Try JavaScript to trigger load more - CHECK EVERY ITERATION
            if not clicked_load_more:
                try:
                    # Scroll to bottom first to ensure button is visible
                    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(0.5)
                    
                    # Try to find and click via JavaScript (more comprehensive)
                    clicked = driver.execute_script("""
                        // Scroll to bottom to ensure button is visible
                        window.scrollTo(0, document.body.scrollHeight);
                        
                        var buttons = document.querySelectorAll('button, a, div[role="button"], span[role="button"]');
                        for (var i = 0; i < buttons.length; i++) {
                            var btn = buttons[i];
                            var text = (btn.textContent || btn.innerText || '').toLowerCase();
                            var className = (btn.className || '').toLowerCase();
                            var id = (btn.id || '').toLowerCase();
                            var ariaLabel = (btn.getAttribute('aria-label') || '').toLowerCase();
                            
                            if (text.includes('load more') || 
                                text.includes('show more') ||
                                (text.includes('more') && (text.includes('load') || text.includes('show'))) ||
                                className.includes('load-more') ||
                                className.includes('loadmore') ||
                                className.includes('show-more') ||
                                id.includes('load-more') ||
                                id.includes('loadmore') ||
                                ariaLabel.includes('load more') ||
                                ariaLabel.includes('show more')) {
                                
                                // Check if visible
                                var rect = btn.getBoundingClientRect();
                                var isVisible = btn.offsetParent !== null && 
                                               rect.width > 0 && 
                                               rect.height > 0 &&
                                               rect.top >= 0 &&
                                               rect.left >= 0 &&
                                               rect.bottom <= (window.innerHeight || document.documentElement.clientHeight) &&
                                               rect.right <= (window.innerWidth || document.documentElement.clientWidth);
                                
                                if (isVisible) {
                                    btn.scrollIntoView({behavior: 'instant', block: 'center'});
                                    // Enable if disabled
                                    if (btn.disabled) {
                                        btn.disabled = false;
                                    }
                                    btn.click();
                                    return true;
                                }
                            }
                        }
                        return false;
                    """)
                    if clicked:
                        time.sleep(5)
                        load_more_clicks += 1
                        clicked_load_more = True
                        print(f"  Clicked 'Load More' via JavaScript (#{load_more_clicks})")
                        
                        # Scroll after clicking
                        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                        time.sleep(3)
                        
                        # Check for new tattoo IDs
                        current_tattoo_ids = extract_tattoo_ids()
                        current_count = len(current_tattoo_ids)
                        if current_count > previous_image_count:
                            print(f"  Click #{load_more_clicks}: Found {current_count} tattoo IDs (was {previous_image_count})")
                            previous_tattoo_ids = current_tattoo_ids
                            previous_image_count = current_count
                            consecutive_no_change = 0
                except Exception as e:
                    pass
            
            # Always scroll (infinite scroll might be loading images)
            # Scroll more aggressively
            driver.execute_script("window.scrollBy(0, 1000);")
            time.sleep(0.2)
            
            # Also try scrolling to bottom periodically to trigger lazy loading
            if iteration % 3 == 0:
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(1)
            
            # Every 5 iterations, scroll to bottom and check for new tattoo IDs
            if iteration % 5 == 0:
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(1)
                
                # Extract tattoo IDs from page source
                current_tattoo_ids = extract_tattoo_ids()
                current_count = len(current_tattoo_ids)
                
                if current_count > previous_image_count:
                    print(f"  Progress: Found {current_count} tattoo IDs (was {previous_image_count})")
                    previous_tattoo_ids = current_tattoo_ids
                    previous_image_count = current_count
                    consecutive_no_change = 0
                else:
                    consecutive_no_change += 1
                
                # Don't stop too early - keep trying even if no change
                # Only stop if we've tried many times AND clicked Load More many times AND have many IDs
                if consecutive_no_change >= max_consecutive_no_change:
                    # If we haven't clicked Load More much, keep trying
                    if load_more_clicks < 50:  # Increased threshold
                        print(f"  No new IDs for {consecutive_no_change * 5} iterations, but only {load_more_clicks} clicks. Continuing...")
                        consecutive_no_change = max_consecutive_no_change - 10  # Reset counter to keep trying
                    # If we have very few IDs compared to expected (127), keep trying
                    elif current_count < 100:  # If we have less than 100, probably not done
                        print(f"  Only {current_count} IDs found (expected ~127), continuing to search...")
                        consecutive_no_change = max_consecutive_no_change - 5  # Reset counter
                    else:
                        print(f"  No new tattoo IDs found for {consecutive_no_change * 5} iterations, stopping...")
                        print(f"  Final tattoo ID count: {current_count}")
                        break
            
            # Every 20 iterations, scroll back to top and down again to trigger lazy loading
            if iteration % 20 == 0 and iteration > 0:
                driver.execute_script("window.scrollTo(0, 0);")
                time.sleep(1)
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)
        
        print(f"  Total 'Load More' clicks: {load_more_clicks}")
        print(f"  Total iterations: {iteration + 1}")
        final_tattoo_ids = extract_tattoo_ids()
        final_count = len(final_tattoo_ids)
        print(f"  Tattoo IDs found in page source: {final_count}")
        
        # Final aggressive scroll to ensure ALL images are loaded
        print("  Final aggressive scroll and extraction...")
        # Scroll to top first
        driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(2)
        
        # Scroll down very slowly to trigger all lazy loading
        print("  Scrolling down very slowly (200 steps)...")
        for i in range(200):
            driver.execute_script("window.scrollBy(0, 200);")
            time.sleep(0.1)
            
            # Check for "Load More" buttons every 20 scrolls
            if i % 20 == 0:
                try:
                    buttons = driver.find_elements(By.XPATH, "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'load more')]")
                    for btn in buttons:
                        if btn.is_displayed() and btn.is_enabled():
                            driver.execute_script("arguments[0].click();", btn)
                            time.sleep(2)
                            load_more_clicks += 1
                except:
                    pass
        
        # Final scroll to bottom
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(5)
        
        # One more pass - scroll back up and down
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight / 3);")
        time.sleep(1)
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight * 2 / 3);")
        time.sleep(1)
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(5)
        
        final_tattoo_ids_after_scroll = extract_tattoo_ids()
        final_count_after_scroll = len(final_tattoo_ids_after_scroll)
        print(f"  Final tattoo ID count after all scrolling: {final_count_after_scroll}")
        
        # Use the maximum count we found
        all_tattoo_ids = previous_tattoo_ids | final_tattoo_ids | final_tattoo_ids_after_scroll
        print(f"  Total unique tattoo IDs collected: {len(all_tattoo_ids)}")
        
        # Extract image URLs using comprehensive method (same as diagnostic script)
        print("\n🔍 Extracting image URLs using comprehensive methods...")
        all_urls = set()
        
        # Primary method: Comprehensive JavaScript extraction (EXACT same as diagnostic script)
        print("  Method 1: Comprehensive JavaScript extraction...")
        extraction_js = """
        var results = {
            img_sources: [],
            background_images: [],
            all_urls: new Set()
        };
        
        // Get all img sources - check all possible attributes (EXACT same as diagnostic)
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
                img.getAttribute('data-original'),
                img.getAttribute('data-lazy'),
                img.getAttribute('data-url')
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
        
        return {
            img_sources: Array.from(new Set(results.img_sources)),
            background_images: Array.from(new Set(results.background_images)),
            all_unique_urls: Array.from(results.all_urls)
        };
        """
        
        js_result = driver.execute_script(extraction_js)
        js_urls = js_result.get('all_unique_urls', [])
        print(f"    Found {len(js_result.get('img_sources', []))} img sources")
        print(f"    Found {len(js_result.get('background_images', []))} background images")
        print(f"    Total unique URLs: {len(js_urls)}")
        for url in js_urls:
            if url and url.strip():
                all_urls.add(url.strip())
        
        # Method 2: Direct img element inspection (backup)
        print("  Method 1: Checking <img> tags...")
        img_elements = driver.find_elements(By.TAG_NAME, "img")
        print(f"    Found {len(img_elements)} img tags")
        for img in img_elements:
            # Check multiple possible attributes
            src = (img.get_attribute('src') or 
                   img.get_attribute('data-src') or 
                   img.get_attribute('data-lazy-src') or
                   img.get_attribute('data-original') or
                   img.get_attribute('data-lazy') or
                   img.get_attribute('data-url'))
            if src and src.strip():
                # Convert relative URLs to absolute
                if src.startswith('//'):
                    src = 'https:' + src
                elif src.startswith('/'):
                    src = 'https://tattooswizard.com' + src
                all_urls.add(src)
        
        # Method 2 already done above, skipping duplicate
        
        # Method 3: Regex on page source (enhanced patterns)
        print("  Method 3: Regex on page source...")
        page_source = driver.page_source
        patterns = [
            # Tattooswizard CDN patterns
            r'https?://cdn\.tattooswizard\.com/[^"\'\s<>]+',
            r'https?://[^"\'\s<>]*tattooswizard[^"\'\s<>]*/artists/[^"\'\s<>]+/tattoos/[^"\'\s<>]+',
            r'https?://storage\.googleapis\.com/[^"\'\s<>]+/artists/[^"\'\s<>]+/tattoos/[^"\'\s<>]+',
            # General image URLs that might be tattoo images
            r'https?://[^"\'\s<>]+\.(jpg|jpeg|png|webp)(\?[^"\'\s<>]*)?',
            # Data URLs and base64 (less common but possible)
            r'data:image/[^;]+;base64,[^"\'\s<>]+',
        ]
        for pattern in patterns:
            matches = re.findall(pattern, page_source, re.IGNORECASE)
            print(f"    Pattern found {len(matches)} matches")
            for match in matches:
                if isinstance(match, tuple):
                    match = match[0] if match[0] else ''
                if match:
                clean_url = re.sub(r'[,;)}>\]]+$', '', match)
                    if clean_url.startswith('http'):
                all_urls.add(clean_url)
        
        # Method 4: Extract from network logs (API responses)
        print("  Method 4: Checking network logs for API responses...")
        try:
            logs = driver.get_log('performance')
            api_urls = set()
            for log in logs:
                try:
                    message = json.loads(log['message'])
                    if message.get('message', {}).get('method') == 'Network.responseReceived':
                        response_url = message.get('message', {}).get('params', {}).get('response', {}).get('url', '')
                        if '/tattoos/' in response_url.lower():
                            api_urls.add(response_url)
                except:
                    pass
            print(f"    Found {len(api_urls)} URLs from network logs")
            all_urls.update(api_urls)
        except Exception as e:
            print(f"    Could not access network logs: {e}")
        
        # Method 5: Use tattoo IDs we collected during scrolling
        print("  Method 5: Using tattoo IDs collected during scrolling...")
        # Extract artist ID from the URL or page source
        artist_id_match = re.search(r'/artists/([a-f0-9]{24})', url)
        if not artist_id_match:
            # Try to find it in page source
            artist_id_match = re.search(r'/artists/([a-f0-9]{24})', page_source)
        
        if artist_id_match:
            artist_id = artist_id_match.group(1)
            base_url = 'https://cdn.tattooswizard.com'
            
            # Use the tattoo IDs we collected during scrolling
            for tattoo_id in all_tattoo_ids:
                constructed_url = f"{base_url}/artists/{artist_id}/tattoos/{tattoo_id}"
                all_urls.add(constructed_url)
            print(f"    Constructed {len(all_tattoo_ids)} URLs from collected tattoo IDs")
        
        # Also extract any additional tattoo IDs from final page source
        print("  Method 5b: Extracting additional tattoo IDs from final page source...")
        tattoo_id_pattern = r'/tattoos/([a-f0-9]{24})'
        additional_tattoo_ids = set(re.findall(tattoo_id_pattern, page_source, re.IGNORECASE))
        print(f"    Found {len(additional_tattoo_ids)} tattoo IDs in final page source")
        
        # Add any new ones we didn't already have
        if artist_id_match:
            artist_id = artist_id_match.group(1)
            base_url = 'https://cdn.tattooswizard.com'
            for tattoo_id in additional_tattoo_ids:
                constructed_url = f"{base_url}/artists/{artist_id}/tattoos/{tattoo_id}"
                all_urls.add(constructed_url)
            print(f"    Added {len(additional_tattoo_ids)} additional URLs")
        
        # Method 6: Check for JSON data in page source (API responses)
        print("  Method 6: Checking for JSON/API data in page source...")
        # Look for JSON arrays containing image URLs
        json_patterns = [
            r'"images":\s*\[([^\]]+)\]',
            r'"photos":\s*\[([^\]]+)\]',
            r'"gallery":\s*\[([^\]]+)\]',
            r'images:\s*\[([^\]]+)\]',
        ]
        for pattern in json_patterns:
            matches = re.findall(pattern, page_source, re.IGNORECASE | re.DOTALL)
            for match in matches:
                # Extract URLs from JSON-like strings
                url_matches = re.findall(r'https?://[^"\'\s,<>]+/tattoos/[^"\'\s,<>]+', match, re.IGNORECASE)
                for url_match in url_matches:
                    all_urls.add(url_match)
        
        print(f"\n📊 Total URLs collected before filtering: {len(all_urls)}")
        
        # Debug: Show sample URLs before filtering
        if len(all_urls) > 0:
            print("\n📋 Sample URLs collected (first 10):")
            for i, url in enumerate(list(all_urls)[:10], 1):
                print(f"  {i}. {url[:100]}...")
        
        # Filter for tattoo images (improved logic)
        print("\n🔍 Filtering URLs...")
        tattoo_images = []
        excluded_count = 0
        excluded_reasons = {}
        
        for url in all_urls:
            url_lower = url.lower()
            
            # Skip data URLs (base64) - they're usually small icons
            if url.startswith('data:'):
                excluded_count += 1
                continue
            
            # Skip obvious UI elements
            ui_keywords = ['logo', 'icon', 'badge', 'marker', 'vector', 'bag', 'static/common', 'avatar', 
                          'placeholder', 'loading', 'spinner', 'arrow', 'button', 'close', 'menu']
            if any(keyword in url_lower for keyword in ui_keywords):
                excluded_count += 1
                continue
            
            # Skip very small images (likely icons) - check file extension patterns
            if any(ext in url_lower for ext in ['.svg', '.ico', 'favicon']):
                excluded_count += 1
                continue
            
            # Much more permissive filtering - if it's from tattooswizard and looks like an image, include it
            is_tattoo_image = False
            
            # Filtering logic (same as diagnostic script - proven to find 62 images)
            # Direct match: contains /tattoos/ in path
            if '/tattoos/' in url_lower:
                is_tattoo_image = True
            # From tattooswizard domain - exclude only obvious UI elements
            elif 'tattooswizard' in url_lower:
                # Exclude only obvious UI elements (same as diagnostic script)
                if not any(skip in url_lower for skip in ['logo', 'icon', 'badge', 'avatar', 'favicon', 'placeholder', 'static/common']):
                    is_tattoo_image = True
            # Has image extension - check if it's not a thumbnail
            elif re.search(r'\.(jpg|jpeg|png|webp)', url_lower):
                # Exclude thumbnails
                if not re.search(r'[_-](thumb|icon|small|mini|tiny|50x50|100x100|150x150)[_-]', url_lower):
                    # If from CDN/storage, likely an image
                    if any(indicator in url_lower for indicator in ['cdn', 'storage', 'images', 'photos', 'media']):
                        is_tattoo_image = True
            
            if is_tattoo_image:
            tattoo_images.append(url)
            else:
                excluded_count += 1
                # Track why URLs are excluded for debugging
                reason = 'unknown'
                if url.startswith('data:'):
                    reason = 'data_url'
                elif any(keyword in url_lower for keyword in ui_keywords):
                    reason = 'ui_element'
                elif any(ext in url_lower for ext in ['.svg', '.ico', 'favicon']):
                    reason = 'icon_format'
                elif not is_tattoo_image:
                    reason = 'not_tattoo_pattern'
                excluded_reasons[reason] = excluded_reasons.get(reason, 0) + 1
        
        print(f"  Excluded {excluded_count} URLs")
        if excluded_reasons:
            print("  Exclusion breakdown:")
            for reason, count in excluded_reasons.items():
                print(f"    - {reason}: {count}")
        
        print(f"\n✅ Found {len(tattoo_images)} unique tattoo image URLs")
        
        # Display found URLs if in debug mode
        if debug:
            if tattoo_images:
                print("\n📸 Tattoo image URLs found:")
            for i, url in enumerate(sorted(tattoo_images), 1):
                print(f"  {i}. {url}")
            else:
                print("\n⚠️  No tattoo images found! Showing sample of all URLs collected:")
                sample_urls = list(all_urls)[:20]  # Show first 20 URLs
                for i, url in enumerate(sample_urls, 1):
                    print(f"  {i}. {url}")
                if len(all_urls) > 20:
                    print(f"  ... and {len(all_urls) - 20} more URLs")
        
        # Handle case where no images are found
        if not tattoo_images:
            print("\n⚠ No tattoo images found after filtering!")
            print(f"   Total URLs collected: {len(all_urls)}")
            print(f"   URLs excluded: {excluded_count}")
            print("\n   This might mean:")
            print("   - Images are loaded differently than expected")
            print("   - Filtering is too strict")
            print("   - Page structure has changed")
            
            # Save debug info
            print("\n💾 Saving debug info...")
            with open(os.path.join(output_folder, 'debug_page.html'), 'w', encoding='utf-8') as f:
                f.write(page_source)
            with open(os.path.join(output_folder, 'debug_urls.txt'), 'w', encoding='utf-8') as f:
                f.write("All URLs found (before filtering):\n")
                f.write("=" * 80 + "\n\n")
                for url in sorted(all_urls):
                    f.write(f"{url}\n")
            print("   Debug files saved: debug_page.html, debug_urls.txt")
            driver.save_screenshot(os.path.join(output_folder, 'debug_screenshot.png'))
            print("   Screenshot saved: debug_screenshot.png")
            
            # Try a less strict filter as fallback
            print("\n🔄 Trying less strict filtering...")
            fallback_images = []
            for url in all_urls:
                url_lower = url.lower()
                # Only exclude obvious non-images
                if not any(skip in url_lower for skip in ['logo', 'icon', 'badge', 'avatar', 'favicon', '.svg', '.ico']):
                    if re.search(r'\.(jpg|jpeg|png|webp)', url_lower) or 'tattooswizard' in url_lower:
                        fallback_images.append(url)
            
            if fallback_images:
                print(f"   Found {len(fallback_images)} images with relaxed filtering")
                tattoo_images = fallback_images[:50]  # Limit to 50 to avoid downloading everything
                print(f"   Using first {len(tattoo_images)} images")
            else:
                pass  # No fallback images found
            
            if interactive:
                input("\nPress Enter to close browser and exit...")
            return
        
        # Save debug info if enabled
        if debug:
            print("\n⚠ Debug mode enabled. Saving debug info...")
            with open(os.path.join(output_folder, 'debug_page.html'), 'w', encoding='utf-8') as f:
                f.write(driver.page_source)
            print("Saved page source to debug_page.html")
            print("📸 Capturing screenshot...")
            driver.save_screenshot(os.path.join(output_folder, 'debug_screenshot.png'))
            print("Saved screenshot to debug_screenshot.png")
            with open(os.path.join(output_folder, 'debug_urls.txt'), 'w', encoding='utf-8') as f:
                f.write("All URLs found:\n")
                for url in sorted(all_urls):
                    f.write(f"{url}\n")
            print("Saved all URLs to debug_urls.txt")
        
        # Download images with throttling prevention
        print(f"\n{'='*60}")
        print(f"⬇️ Downloading images to {output_folder}...")
        print(f"{'='*60}\n")
        
        # User agent rotation to avoid detection
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
        ]
        
        downloaded = 0
        failed_downloads = 0
        max_retries = 3
        
        for idx, img_url in enumerate(sorted(tattoo_images), start=1):
            retry_count = 0
            success = False
            
            while retry_count < max_retries and not success:
                try:
                    # Random user agent for each request
                    headers = {
                        'User-Agent': random.choice(user_agents),
                        'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
                        'Accept-Language': 'en-US,en;q=0.9',
                        'Referer': url,
                    }
                    
                print(f"[{idx}/{len(tattoo_images)}] Downloading...")
                
                    # Random delay between requests (0.5-2 seconds) to avoid throttling
                    if idx > 1:
                        delay = random.uniform(0.5, 2.0)
                        time.sleep(delay)
                    
                    img_response = requests.get(img_url, headers=headers, timeout=15)
                img_response.raise_for_status()
                
                output_path = os.path.join(output_folder, f"{idx}.jpg")
                with open(output_path, 'wb') as f:
                    f.write(img_response.content)
                
                file_size = len(img_response.content)
                print(f"  ✓ Saved as {idx}.jpg ({file_size:,} bytes)")
                downloaded += 1
                    success = True
                    
                    # Longer delay after every 10 images to avoid rate limiting
                    if idx % 10 == 0:
                        extra_delay = random.uniform(2, 5)
                        print(f"  ⏸ Pausing {extra_delay:.1f}s to avoid rate limiting...")
                        time.sleep(extra_delay)
                    
                except requests.exceptions.HTTPError as e:
                    if e.response.status_code == 429:  # Too Many Requests
                        wait_time = random.uniform(5, 10)
                        print(f"  ⚠ Rate limited! Waiting {wait_time:.1f}s before retry...")
                        time.sleep(wait_time)
                        retry_count += 1
                    elif e.response.status_code >= 500:  # Server error
                        wait_time = random.uniform(2, 5)
                        print(f"  ⚠ Server error {e.response.status_code}, waiting {wait_time:.1f}s...")
                        time.sleep(wait_time)
                        retry_count += 1
                    else:
                        print(f"  ✗ Failed: {e}")
                        failed_downloads += 1
                        break
            except Exception as e:
                    if retry_count < max_retries - 1:
                        wait_time = random.uniform(1, 3) * (retry_count + 1)  # Exponential backoff
                        print(f"  ⚠ Error: {e}, retrying in {wait_time:.1f}s...")
                        time.sleep(wait_time)
                        retry_count += 1
                    else:
                        print(f"  ✗ Failed after {max_retries} attempts: {e}")
                        failed_downloads += 1
                        break
        
        print(f"\n{'='*60}")
        print(f"🎉 Successfully downloaded {downloaded}/{len(tattoo_images)} images")
        print(f"{'='*60}")
        
    except Exception as e:
        print(f"\n❌ Critical error: {e}")
        traceback.print_exc()
    finally:
        if driver:
            if interactive:
                input("\nPress Enter to close browser...")
            driver.quit()
    
    end_time = datetime.datetime.now()
    print(f"🕒 Script completed at: {end_time}")
    print(f"⏱ Total runtime: {end_time - start_time}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=f"Tattoo Artist Portfolio Downloader v{__version__}")
    parser.add_argument("artist_url", help="URL of the artist's page")
    parser.add_argument("output_folder", help="Folder to save images")
    parser.add_argument("--visible", action="store_true", help="Show browser window (non-headless mode)")
    parser.add_argument("--interactive", action="store_true", help="Wait for user input at key steps")
    parser.add_argument("--no-debug", action="store_true", help="Disable debug mode")
    
    args = parser.parse_args()
    
    download_artist_portfolio(
        url=args.artist_url,
        output_folder=args.output_folder,
        headless=not args.visible,
        interactive=args.interactive,
        debug=not args.no_debug
    )
