#!/usr/bin/env python3
"""
Focused script to discover more artists by:
1. Using known working locations from sitemap
2. Discovering all style variations for those locations
3. Trying major cities from cities file
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

class StyleLocationDiscoverer:
    def __init__(self, base_url="https://www.tattoodo.com"):
        self.base_url = base_url
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        self.driver = None
        self.all_artist_urls = set()
        
    def setup_selenium(self):
        """Setup Selenium driver"""
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
    
    def load_existing_artists(self):
        """Load existing discovered artists"""
        from _repo_root import repo_path
        try:
            with open(repo_path('TATTOODO', 'discovered_pages.json'), 'r') as f:
                data = json.load(f)
                self.all_artist_urls = set(data.get('artists', []))
                print(f"📊 Loaded {len(self.all_artist_urls)} existing artists")
        except:
            pass
    
    def get_known_locations(self):
        """Get known working locations from sitemap"""
        locations = set()
        try:
            response = requests.get(f"{self.base_url}/sitemaps/sitemap-tattoo-artists.xml", headers=self.headers, timeout=10)
            if response.status_code == 200:
                try:
                    soup = BeautifulSoup(response.text, 'xml')
                except:
                    soup = BeautifulSoup(response.text, 'html.parser')
                
                for loc in soup.find_all('loc'):
                    url = loc.text.strip()
                    if '/tattoo-artists/' in url:
                        parts = url.split('/tattoo-artists/')
                        if len(parts) > 1:
                            location_slug = parts[1].split('/')[0]
                            if location_slug and not any(char.isdigit() for char in location_slug):
                                locations.add(location_slug)
        except Exception as e:
            print(f"  ⚠ Error: {e}")
        
        return locations
    
    def discover_all_styles_for_location(self, location_slug):
        """Discover all style pages for a location by checking the location page"""
        styles = set()
        
        if not self.driver:
            self.setup_selenium()
        
        try:
            location_url = f"{self.base_url}/tattoo-artists/{location_slug}"
            self.driver.get(location_url)
            time.sleep(3)
            
            # Scroll to load content
            for i in range(5):
                self.driver.execute_script("window.scrollBy(0, 500);")
                time.sleep(0.5)
            
            # Find all style links
            links = self.driver.find_elements(By.TAG_NAME, "a")
            for link in links:
                try:
                    href = link.get_attribute('href')
                    if href and f'/tattoo-artists/{location_slug}/' in href:
                        # Extract style from URL
                        parts = href.split(f'/tattoo-artists/{location_slug}/')
                        if len(parts) > 1:
                            style_with_num = parts[1].split('/')[0].split('?')[0]
                            # Remove trailing numbers
                            style = re.sub(r'-\d+$', '', style_with_num)
                            if style and style != location_slug and len(style) > 2:
                                styles.add(style)
                except:
                    continue
            
            # Also check page source
            page_source = self.driver.page_source
            style_pattern = rf'/tattoo-artists/{re.escape(location_slug)}/([a-z-]+)'
            matches = re.findall(style_pattern, page_source, re.IGNORECASE)
            for match in matches:
                style = re.sub(r'-\d+$', '', match)
                if style and style != location_slug and len(style) > 2:
                    styles.add(style)
                    
        except Exception as e:
            print(f"    ⚠ Error discovering styles for {location_slug}: {e}")
        
        return styles
    
    def discover_artists_from_page(self, url):
        """Discover artists from a page"""
        artist_urls = set()
        
        if not self.driver:
            self.setup_selenium()
        
        try:
            self.driver.set_page_load_timeout(10)
            self.driver.get(url)
            time.sleep(2)
            
            # Scroll to load content
            for i in range(15):
                self.driver.execute_script("window.scrollBy(0, 500);")
                time.sleep(0.3)
                
                # Extract artist URLs
                links = self.driver.find_elements(By.TAG_NAME, "a")
                for link in links:
                    try:
                        href = link.get_attribute('href')
                        if href and '/artists/' in href:
                            parsed = urlparse(href)
                            if parsed.netloc == urlparse(self.base_url).netloc:
                                clean_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
                                if '/artists/' in clean_url:
                                    parts = clean_url.split('/artists/')
                                    if len(parts) > 1:
                                        path_after = parts[1].split('/')[0]
                                        if path_after and path_after not in ['', 'artists', 'book', 'portfolio', 'nearest']:
                                            artist_urls.add(clean_url)
                    except:
                        continue
            
            # Final scroll and extraction
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            
            links = self.driver.find_elements(By.TAG_NAME, "a")
            for link in links:
                try:
                    href = link.get_attribute('href')
                    if href and '/artists/' in href:
                        parsed = urlparse(href)
                        if parsed.netloc == urlparse(self.base_url).netloc:
                            clean_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
                            if '/artists/' in clean_url:
                                parts = clean_url.split('/artists/')
                                if len(parts) > 1:
                                    path_after = parts[1].split('/')[0]
                                    if path_after and path_after not in ['', 'artists', 'book', 'portfolio', 'nearest']:
                                        artist_urls.add(clean_url)
                except:
                    continue
                    
        except Exception as e:
            pass
        
        return artist_urls
    
    def discover_all(self):
        """Discover all artists by exploring styles for known locations"""
        print("=" * 60)
        print("🔎 Discovering artists from location/style pages")
        print("=" * 60)
        
        # Load existing artists
        self.load_existing_artists()
        
        # Get known locations
        known_locations = self.get_known_locations()
        print(f"\n🔍 Found {len(known_locations)} known locations: {sorted(known_locations)}")
        
        if not self.driver:
            self.setup_selenium()
        
        total_new_artists = 0
        
        # For each location, discover all styles and crawl them
        for i, location_slug in enumerate(sorted(known_locations), 1):
            print(f"\n[{i}/{len(known_locations)}] Processing {location_slug}...")
            
            # Discover all styles for this location
            styles = self.discover_all_styles_for_location(location_slug)
            print(f"  Found {len(styles)} styles: {sorted(styles)[:10]}")
            
            # Crawl base location page
            base_url = f"{self.base_url}/tattoo-artists/{location_slug}"
            artists = self.discover_artists_from_page(base_url)
            before_count = len(self.all_artist_urls)
            self.all_artist_urls.update(artists)
            new_count = len(self.all_artist_urls) - before_count
            if new_count > 0:
                print(f"  ✓ Found {new_count} new artists from base page")
                total_new_artists += new_count
            
            # Crawl each style page (skip generic 'artists' and 'styles' links)
            for style in styles:
                if style in ['artists', 'styles']:
                    continue  # Skip generic links
                
                # Try style URL patterns
                style_patterns = [
                    f"{self.base_url}/tattoo-artists/{location_slug}/{style}",
                    f"{self.base_url}/tattoo-artists/{location_slug}/{style}-1",
                ]
                
                for style_url in style_patterns:
                    try:
                        # Quick check if page exists
                        response = requests.head(style_url, headers=self.headers, timeout=3)
                        if response.status_code == 200:
                            artists = self.discover_artists_from_page(style_url)
                            before_count = len(self.all_artist_urls)
                            self.all_artist_urls.update(artists)
                            new_count = len(self.all_artist_urls) - before_count
                            if new_count > 0:
                                print(f"    ✓ Style '{style}': {new_count} new artists")
                                total_new_artists += new_count
                            break  # Found valid page, no need to try other patterns
                    except:
                        continue
        
        self.close_selenium()
        
        print(f"\n✅ Discovery complete!")
        print(f"   Total artists: {len(self.all_artist_urls)}")
        print(f"   New artists found: {total_new_artists}")
        
        return self.all_artist_urls
    
    def save_results(self, output_file="TATTOODO/discovered_pages_final.json"):
        """Save results (path relative to repo root unless absolute)"""
        from _repo_root import repo_path
        from pathlib import Path
        p = Path(output_file) if Path(output_file).is_absolute() else repo_path(output_file)
        output_file = str(p)
        p.parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            'artists': sorted(self.all_artist_urls),
            'total': len(self.all_artist_urls)
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        txt_file = output_file.replace('.json', '.txt')
        with open(txt_file, 'w', encoding='utf-8') as f:
            f.write(f"Total artists: {len(self.all_artist_urls)}\n")
            f.write("=" * 60 + "\n\n")
            for url in sorted(self.all_artist_urls):
                f.write(f"{url}\n")
        
        print(f"\n✅ Results saved to:")
        print(f"   - {output_file}")
        print(f"   - {txt_file}")


def main():
    discoverer = StyleLocationDiscoverer()
    
    try:
        discoverer.discover_all()
        discoverer.save_results()
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

