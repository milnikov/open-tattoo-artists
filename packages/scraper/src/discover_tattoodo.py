#!/usr/bin/env python3
"""
Script to discover all artist pages on tattoodo.com
"""

import requests
import re
import json
import time
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

class TattoodoPageDiscoverer:
    def __init__(self, base_url="https://www.tattoodo.com", use_selenium=True):
        self.base_url = base_url
        self.use_selenium = use_selenium
        self.discovered_urls = set()
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        self.driver = None
        
    def setup_selenium(self):
        """Setup Selenium driver"""
        if not self.use_selenium:
            return None
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--window-size=1920,1080')
        self.driver = webdriver.Chrome(options=chrome_options)
        return self.driver
    
    def close_selenium(self):
        """Close Selenium driver"""
        if self.driver:
            self.driver.quit()
            self.driver = None
    
    def check_sitemap(self):
        """Check for sitemap.xml files"""
        print("🔍 Checking for sitemap.xml...")
        sitemap_urls = [
            f"{self.base_url}/sitemap.xml",
            f"{self.base_url}/sitemaps/sitemap-tattoo-artists.xml",
        ]
        
        found_urls = set()
        sitemap_index_urls = set()
        
        for sitemap_url in sitemap_urls:
            try:
                response = requests.get(sitemap_url, headers=self.headers, timeout=10)
                if response.status_code == 200:
                    print(f"  ✓ Found: {sitemap_url}")
                    try:
                        soup = BeautifulSoup(response.text, 'xml')
                    except Exception:
                        soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # Check if this is a sitemap index
                    sitemaps = soup.find_all('sitemap')
                    if sitemaps:
                        print(f"    Found sitemap index with {len(sitemaps)} sitemaps")
                        for sitemap in sitemaps:
                            loc = sitemap.find('loc')
                            if loc:
                                sitemap_index_urls.add(loc.text.strip())
                    else:
                        # Regular sitemap with URLs
                        for loc in soup.find_all('loc'):
                            url = loc.text.strip()
                            found_urls.add(url)
                        print(f"    Found {len(found_urls)} URLs in sitemap")
            except Exception as e:
                print(f"  ✗ {sitemap_url}: {e}")
        
        # Process sitemap index URLs
        if sitemap_index_urls:
            print(f"\n  Processing {len(sitemap_index_urls)} sitemap files from index...")
            for sitemap_url in sitemap_index_urls:
                try:
                    print(f"    Fetching {sitemap_url}...")
                    response = requests.get(sitemap_url, headers=self.headers, timeout=30)
                    if response.status_code == 200:
                        try:
                            soup = BeautifulSoup(response.text, 'xml')
                        except Exception:
                            soup = BeautifulSoup(response.text, 'html.parser')
                        
                        urls_in_sitemap = 0
                        artist_count = 0
                        for loc in soup.find_all('loc'):
                            url = loc.text.strip()
                            found_urls.add(url)
                            urls_in_sitemap += 1
                            if '/artists/' in url:
                                artist_count += 1
                        print(f"      ✓ Found {urls_in_sitemap} URLs ({artist_count} artists)")
                except Exception as e:
                    print(f"      ✗ Error: {e}")
        
        return found_urls
    
    def check_robots_txt(self):
        """Check robots.txt for sitemap references"""
        print("\n🔍 Checking robots.txt...")
        robots_url = f"{self.base_url}/robots.txt"
        sitemap_urls = set()
        
        try:
            response = requests.get(robots_url, headers=self.headers, timeout=10)
            if response.status_code == 200:
                print(f"  ✓ Found robots.txt")
                for line in response.text.split('\n'):
                    if line.lower().startswith('sitemap:'):
                        sitemap_url = line.split(':', 1)[1].strip()
                        sitemap_urls.add(sitemap_url)
                        print(f"    Found sitemap reference: {sitemap_url}")
        except Exception as e:
            print(f"  ✗ robots.txt: {e}")
        
        return set()
    
    def get_page_with_selenium(self, url):
        """Get page content using Selenium"""
        if not self.driver:
            self.setup_selenium()
        
        try:
            self.driver.get(url)
            time.sleep(3)  # Wait for page to load
            
            # Scroll to load lazy content
            for i in range(10):
                self.driver.execute_script(f"window.scrollBy(0, 500);")
                time.sleep(0.5)
            
            return self.driver.page_source
        except Exception as e:
            print(f"  Error loading {url} with Selenium: {e}")
            return None
    
    def extract_links_from_html(self, html, base_url):
        """Extract all links from HTML"""
        if not html:
            return set()
        
        soup = BeautifulSoup(html, 'html.parser')
        links = set()
        
        # Find all <a> tags
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href']
            absolute_url = urljoin(base_url, href)
            parsed = urlparse(absolute_url)
            if parsed.netloc == urlparse(base_url).netloc:
                clean_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
                if parsed.query:
                    clean_url += f"?{parsed.query}"
                links.add(clean_url)
        
        return links
    
    def discover_artist_pages_from_location(self, location_url):
        """Discover artist pages from a location page"""
        artist_urls = set()
        try:
            print(f"    Loading {location_url}...")
            self.driver.get(location_url)
            time.sleep(3)
            
            # Scroll to load content
            for i in range(20):
                self.driver.execute_script("window.scrollBy(0, 500);")
                time.sleep(0.3)
                
                # Extract artist URLs
                current_urls = self._extract_artist_urls_from_page()
                artist_urls.update(current_urls)
            
            # Final scroll to bottom
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            final_urls = self._extract_artist_urls_from_page()
            artist_urls.update(final_urls)
            
        except Exception as e:
            print(f"      ⚠ Error loading {location_url}: {e}")
        
        return artist_urls
    
    def discover_artist_pages(self):
        """Discover all artist pages from the artists directory and location pages"""
        print("\n🔍 Discovering artist pages...")
        artists_url = f"{self.base_url}/tattoo-artists"  # Use the actual redirect target
        
        if not self.driver:
            self.setup_selenium()
        
        artist_urls = set()
        previous_count = 0
        no_change_count = 0
        
        try:
            print(f"  Loading {artists_url}...")
            self.driver.get(artists_url)
            time.sleep(5)  # Wait for initial page load
            
            # Aggressive scrolling with "Load More" button checking
            print("  Scrolling and checking for 'Load More' buttons...")
            scroll_attempts = 0
            max_scroll_attempts = 300  # Increased limit for large directories
            load_more_clicked = 0
            max_load_more_clicks = 200
            
            while scroll_attempts < max_scroll_attempts:
                # Check for "Load More" button before scrolling
                if load_more_clicked < max_load_more_clicks:
                    try:
                        load_more_selectors = [
                            "//button[contains(text(), 'Load More')]",
                            "//a[contains(text(), 'Load More')]",
                            "//button[contains(text(), 'Show More')]",
                            "//a[contains(text(), 'Show More')]",
                            "//*[contains(@class, 'load-more')]",
                            "//*[contains(@class, 'loadMore')]",
                            "//*[contains(@class, 'load-more-button')]",
                            "//button[contains(@aria-label, 'Load')]",
                        ]
                        
                        for selector in load_more_selectors:
                            try:
                                load_more_btn = self.driver.find_element(By.XPATH, selector)
                                if load_more_btn.is_displayed() and load_more_btn.is_enabled():
                                    print(f"    Clicking 'Load More' button (attempt {load_more_clicked + 1})...")
                                    self.driver.execute_script("arguments[0].scrollIntoView(true);", load_more_btn)
                                    time.sleep(0.5)
                                    self.driver.execute_script("arguments[0].click();", load_more_btn)
                                    time.sleep(3)  # Wait for content to load
                                    load_more_clicked += 1
                                    break
                            except:
                                continue
                    except:
                        pass
                
                # Scroll down
                self.driver.execute_script("window.scrollBy(0, 500);")
                time.sleep(0.3)
                
                # Extract current artist URLs
                current_urls = self._extract_artist_urls_from_page()
                artist_urls.update(current_urls)
                
                # Check if we found new artists
                current_count = len(artist_urls)
                if current_count == previous_count:
                    no_change_count += 1
                    if no_change_count >= 15:  # Increased threshold
                        # Try scrolling to very bottom one more time
                        self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                        time.sleep(3)
                        # Check one more time
                        final_urls = self._extract_artist_urls_from_page()
                        artist_urls.update(final_urls)
                        if len(artist_urls) == previous_count:
                            print(f"    No new artists found after {no_change_count} scrolls, stopping...")
                            break
                        else:
                            no_change_count = 0
                else:
                    no_change_count = 0
                    if current_count % 50 == 0 or scroll_attempts % 30 == 0:
                        print(f"    Found {current_count} artists so far...")
                
                previous_count = len(artist_urls)
                scroll_attempts += 1
                
                # Scroll to bottom periodically
                if scroll_attempts % 30 == 0:
                    self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(2)
            
            if load_more_clicked > 0:
                print(f"  ✓ Clicked 'Load More' {load_more_clicked} times")
            print(f"  ✓ Scrolled {scroll_attempts} times")
            
            # Final extraction from page source
            print("  Extracting URLs from final page source...")
            html = self.driver.page_source
            final_urls = self._extract_artist_urls_from_html(html, artists_url)
            artist_urls.update(final_urls)
            
            print(f"  ✓ Total unique artist URLs found: {len(artist_urls)}")
            
        except Exception as e:
            print(f"  ⚠ Error during discovery: {e}")
            import traceback
            traceback.print_exc()
            # Still try to extract from current page
            try:
                html = self.driver.page_source if self.driver else None
                if html:
                    final_urls = self._extract_artist_urls_from_html(html, artists_url)
                    artist_urls.update(final_urls)
            except:
                pass
        
        return artist_urls
    
    def _extract_artist_urls_from_page(self):
        """Extract artist URLs from current DOM"""
        artist_urls = set()
        try:
            # Find all links
            links = self.driver.find_elements(By.TAG_NAME, "a")
            for link in links:
                try:
                    href = link.get_attribute('href')
                    if href and '/artists/' in href:
                        parsed = urlparse(href)
                        if parsed.netloc == urlparse(self.base_url).netloc:
                            clean_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
                            # Filter for individual artist pages (not directory pages)
                            if '/artists/' in clean_url and clean_url != f"{self.base_url}/artists":
                                # Exclude filter/search pages and sub-pages like /book
                                if not any(skip in clean_url for skip in ['?', '#', '/tattoo-artists/']):
                                    # Only include if it looks like an artist page (has a slug after /artists/)
                                    parts = clean_url.split('/artists/')
                                    if len(parts) > 1 and parts[1]:
                                        # Check if it's a direct artist page (not a sub-page like /artists/name/book)
                                        path_after_artists = parts[1].split('/')[0]
                                        # Exclude sub-pages like /book, /portfolio, etc.
                                        if path_after_artists and path_after_artists not in ['', 'artists', 'book', 'portfolio', 'nearest']:
                                            artist_urls.add(clean_url)
                except:
                    continue
        except:
            pass
        return artist_urls
    
    def _extract_artist_urls_from_html(self, html, base_url):
        """Extract artist URLs from HTML source"""
        artist_urls = set()
        
        if not html:
            return artist_urls
        
        # Method 1: Extract from links
        all_links = self.extract_links_from_html(html, base_url)
        for link in all_links:
            if '/artists/' in link and link != base_url:
                # Filter for individual artist pages
                if not any(skip in link for skip in ['?', '#', '/tattoo-artists/']):
                    parts = link.split('/artists/')
                    if len(parts) > 1 and parts[1]:
                        # Check if it's a direct artist page (not a sub-page)
                        path_after_artists = parts[1].split('/')[0]
                        # Exclude sub-pages like /book, /portfolio, etc.
                        if path_after_artists and path_after_artists not in ['', 'artists', 'book', 'portfolio', 'nearest']:
                            artist_urls.add(link)
        
        # Method 2: Regex pattern matching
        artist_patterns = [
            r'/artists/[a-zA-Z0-9_-]+',
            r'href=["\']([^"\']*\/artists\/[a-zA-Z0-9_-]+)["\']',
            r'https?://[^/]+/artists/[a-zA-Z0-9_-]+',
        ]
        
        for pattern in artist_patterns:
            matches = re.findall(pattern, html)
            for match in matches:
                if isinstance(match, tuple):
                    match = match[0] if match else ''
                if match:
                    full_url = urljoin(self.base_url, match) if not match.startswith('http') else match
                    parsed = urlparse(full_url)
                    if parsed.netloc == urlparse(self.base_url).netloc:
                        clean_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
                        if '/artists/' in clean_url and clean_url != f"{self.base_url}/artists":
                            if not any(skip in clean_url for skip in ['?', '#', '/tattoo-artists/']):
                                parts = clean_url.split('/artists/')
                                if len(parts) > 1 and parts[1]:
                                    # Check if it's a direct artist page (not a sub-page)
                                    path_after_artists = parts[1].split('/')[0]
                                    # Exclude sub-pages like /book, /portfolio, etc.
                                    if path_after_artists and path_after_artists not in ['', 'artists', 'book', 'portfolio', 'nearest']:
                                        artist_urls.add(clean_url)
        
        return artist_urls
    
    def discover_artists_from_location_pages(self):
        """Discover artists from location-based pages"""
        print("\n🔍 Discovering artists from location pages...")
        
        # Get location URLs from sitemap
        location_urls = set()
        try:
            response = requests.get(f"{self.base_url}/sitemaps/sitemap-tattoo-artists.xml", headers=self.headers, timeout=10)
            if response.status_code == 200:
                try:
                    soup = BeautifulSoup(response.text, 'xml')
                except:
                    soup = BeautifulSoup(response.text, 'html.parser')
                
                for loc in soup.find_all('loc'):
                    url = loc.text.strip()
                    # Get all location pages (including style-specific ones)
                    if '/tattoo-artists/' in url:
                        # Include both base location pages and style-specific pages
                        location_urls.add(url)
        except Exception as e:
            print(f"  ⚠ Error getting location URLs: {e}")
        
        print(f"  Found {len(location_urls)} location pages to crawl")
        
        if not self.driver:
            self.setup_selenium()
        
        all_artist_urls = set()
        for i, location_url in enumerate(sorted(location_urls), 1):
            print(f"  [{i}/{len(location_urls)}] Crawling {location_url}...")
            artist_urls = self.discover_artist_pages_from_location(location_url)
            all_artist_urls.update(artist_urls)
            if artist_urls:
                print(f"      ✓ Found {len(artist_urls)} artists")
        
        print(f"  ✓ Total artists from location pages: {len(all_artist_urls)}")
        return all_artist_urls
    
    def discover_all(self):
        """Discover all pages using multiple methods"""
        print("=" * 60)
        print("🔎 Discovering all artist pages on tattoodo.com")
        print("=" * 60)
        
        all_urls = set()
        
        # Method 1: Check sitemap
        sitemap_urls = self.check_sitemap()
        all_urls.update(sitemap_urls)
        
        # Method 2: Check robots.txt
        robots_urls = self.check_robots_txt()
        all_urls.update(robots_urls)
        
        # Method 3: Discover artist pages by crawling main directory
        artist_urls = self.discover_artist_pages()
        all_urls.update(artist_urls)
        
        # Method 4: Discover artists from location pages
        location_artist_urls = self.discover_artists_from_location_pages()
        all_urls.update(location_artist_urls)
        
        # Clean up
        self.close_selenium()
        
        return all_urls
    
    def save_results(self, urls, output_file="TATTOODO/discovered_pages.json"):
        """Save discovered URLs to a file (path relative to repo root unless absolute)"""
        from _repo_root import repo_path
        from pathlib import Path
        p = Path(output_file) if Path(output_file).is_absolute() else repo_path(output_file)
        output_file = str(p)
        Path(output_file).parent.mkdir(parents=True, exist_ok=True)
        
        # Categorize URLs
        categories = {
            'artists': [],
            'other': []
        }
        
        for url in sorted(urls):
            if '/artists/' in url:
                categories['artists'].append(url)
            else:
                categories['other'].append(url)
        
        # Save as JSON
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(categories, f, indent=2, ensure_ascii=False)
        
        # Also save as text file
        txt_file = output_file.replace('.json', '.txt')
        with open(txt_file, 'w', encoding='utf-8') as f:
            f.write(f"Total URLs discovered: {len(urls)}\n")
            f.write("=" * 60 + "\n\n")
            
            for category, category_urls in categories.items():
                if category_urls:
                    f.write(f"\n{category.upper()} ({len(category_urls)} URLs):\n")
                    f.write("-" * 60 + "\n")
                    for url in category_urls:
                        f.write(f"{url}\n")
        
        print(f"\n✅ Results saved to:")
        print(f"   - {output_file} (JSON)")
        print(f"   - {txt_file} (Text)")
        print(f"\n📊 Summary:")
        print(f"   Total URLs: {len(urls)}")
        for category, category_urls in categories.items():
            if category_urls:
                print(f"   {category.capitalize()}: {len(category_urls)}")


def main():
    discoverer = TattoodoPageDiscoverer()
    
    try:
        urls = discoverer.discover_all()
        discoverer.save_results(urls)
    except KeyboardInterrupt:
        print("\n\n⚠ Interrupted by user")
        discoverer.close_selenium()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        discoverer.close_selenium()


if __name__ == "__main__":
    main()

