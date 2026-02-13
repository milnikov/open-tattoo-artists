#!/usr/bin/env python3
"""
Comprehensive script to discover all location and style pages on tattoodo.com
Uses cities_over_100k.json to find many more locations
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

class ComprehensiveTattoodoDiscoverer:
    def __init__(self, base_url="https://www.tattoodo.com"):
        self.base_url = base_url
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        self.driver = None
        self.all_artist_urls = set()
        self.all_locations = set()
        self.all_styles = set()
        
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
    
    def normalize_city_name(self, city_name):
        """Convert city name to URL-friendly slug"""
        # Convert to lowercase
        slug = city_name.lower()
        # Replace spaces and special chars with hyphens
        slug = re.sub(r'[^a-z0-9]+', '-', slug)
        # Remove leading/trailing hyphens
        slug = slug.strip('-')
        # Handle common abbreviations
        replacements = {
            'new-york': 'nyc',
            'los-angeles': 'la',
            'san-francisco': 'sf',
        }
        return replacements.get(slug, slug)
    
    def load_cities_from_file(self, filename='cities_over_100k.json'):
        """Load cities from JSON file and convert to location slugs"""
        print(f"\n🔍 Loading cities from {filename}...")
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                cities_data = json.load(f)
            
            location_slugs = set()
            
            if isinstance(cities_data, list):
                for city in cities_data:
                    # Try both name and ascii_name
                    if 'name' in city:
                        slug = self.normalize_city_name(city['name'])
                        if slug:
                            location_slugs.add(slug)
                    if 'ascii_name' in city and city['ascii_name'] != city.get('name'):
                        slug = self.normalize_city_name(city['ascii_name'])
                        if slug:
                            location_slugs.add(slug)
            elif isinstance(cities_data, dict):
                for city in cities_data.values():
                    if isinstance(city, dict):
                        if 'name' in city:
                            slug = self.normalize_city_name(city['name'])
                            if slug:
                                location_slugs.add(slug)
            
            print(f"  ✓ Generated {len(location_slugs)} location slugs from cities")
            return location_slugs
            
        except Exception as e:
            print(f"  ⚠ Error loading cities file: {e}")
            return set()
    
    def discover_styles_from_sitemap(self):
        """Discover style patterns from existing sitemap pages"""
        print("\n🔍 Discovering style patterns from sitemap...")
        styles = set()
        
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
                        # Extract style from URLs like /tattoo-artists/la/neo-traditional-29
                        parts = url.split('/tattoo-artists/')
                        if len(parts) > 1:
                            path_parts = parts[1].split('/')
                            if len(path_parts) > 1:
                                # Style is the part before the number
                                style_with_num = path_parts[1]
                                # Remove trailing numbers
                                style = re.sub(r'-\d+$', '', style_with_num)
                                if style:
                                    styles.add(style)
        except Exception as e:
            print(f"  ⚠ Error: {e}")
        
        print(f"  ✓ Found {len(styles)} style patterns: {sorted(styles)}")
        return styles
    
    def check_page_exists(self, url):
        """Check if a page exists and returns 200"""
        try:
            response = requests.head(url, headers=self.headers, timeout=3, allow_redirects=False)
            return response.status_code == 200
        except:
            return False
    
    def discover_artists_from_page(self, url, timeout=15):
        """Discover artists from a single page"""
        artist_urls = set()
        
        if not self.driver:
            self.setup_selenium()
        
        try:
            self.driver.set_page_load_timeout(timeout)
            self.driver.get(url)
            time.sleep(2)  # Reduced wait time
            
            # Scroll to load content (fewer scrolls)
            for i in range(10):  # Reduced from 20
                self.driver.execute_script("window.scrollBy(0, 500);")
                time.sleep(0.2)  # Reduced from 0.3
                
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
            
            # Final scroll
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            
            # Final extraction
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
    
    def discover_styles_for_location(self, location_slug):
        """Discover available styles for a location by checking the location page"""
        styles = set()
        
        if not self.driver:
            self.setup_selenium()
        
        try:
            location_url = f"{self.base_url}/tattoo-artists/{location_slug}"
            self.driver.get(location_url)
            time.sleep(3)
            
            # Find style links on the page
            links = self.driver.find_elements(By.TAG_NAME, "a")
            for link in links:
                try:
                    href = link.get_attribute('href')
                    if href and f'/tattoo-artists/{location_slug}/' in href:
                        # Extract style from URL
                        parts = href.split(f'/tattoo-artists/{location_slug}/')
                        if len(parts) > 1:
                            style_with_num = parts[1].split('/')[0]
                            # Remove trailing numbers
                            style = re.sub(r'-\d+$', '', style_with_num)
                            if style and style != location_slug:
                                styles.add(style)
                except:
                    continue
        except:
            pass
        
        return styles
    
    def discover_all(self, max_locations=500, check_existence=True):
        """Discover all artists using comprehensive methods"""
        print("=" * 60)
        print("🔎 Comprehensive discovery of all artist pages on tattoodo.com")
        print("=" * 60)
        
        # Load existing results
        try:
            with open('TATTOODO/discovered_pages.json', 'r') as f:
                existing_data = json.load(f)
                self.all_artist_urls = set(existing_data.get('artists', []))
                print(f"\n📊 Starting with {len(self.all_artist_urls)} existing artists")
        except:
            pass
        
        # Discover styles from sitemap
        known_styles = self.discover_styles_from_sitemap()
        self.all_styles.update(known_styles)
        
        # Load cities and generate location slugs
        city_slugs = self.load_cities_from_file()
        
        # Also get locations from sitemap
        sitemap_locations = set()
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
                                sitemap_locations.add(location_slug)
        except:
            pass
        
        # Combine all locations
        all_location_slugs = city_slugs | sitemap_locations
        print(f"\n🔍 Total location slugs to check: {len(all_location_slugs)}")
        
        # Limit to max_locations for performance
        if len(all_location_slugs) > max_locations:
            print(f"  Limiting to first {max_locations} locations...")
            all_location_slugs = list(all_location_slugs)[:max_locations]
        
        # Check which locations actually exist (faster batch checking)
        print(f"\n🔍 Checking which locations exist...")
        valid_locations = []
        
        # Use threading or batch requests for faster checking
        import concurrent.futures
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        def check_location(location_slug):
            location_url = f"{self.base_url}/tattoo-artists/{location_slug}"
            if check_existence:
                if self.check_page_exists(location_url):
                    return location_slug
            else:
                return location_slug
            return None
        
        # Check locations in parallel (max 10 workers)
        with ThreadPoolExecutor(max_workers=10) as executor:
            future_to_location = {executor.submit(check_location, slug): slug for slug in all_location_slugs}
            
            for i, future in enumerate(as_completed(future_to_location), 1):
                if i % 50 == 0:
                    print(f"  [{i}/{len(all_location_slugs)}] Checked {i} locations, found {len(valid_locations)} valid...")
                
                result = future.result()
                if result:
                    valid_locations.append(result)
        
        print(f"  ✓ Found {len(valid_locations)} valid location pages")
        
        # Crawl all valid locations
        print(f"\n🔍 Crawling {len(valid_locations)} location pages...")
        if not self.driver:
            self.setup_selenium()
        
        total_pages_crawled = 0
        for i, location_slug in enumerate(valid_locations, 1):
            if i % 5 == 0:  # More frequent updates
                print(f"  [{i}/{len(valid_locations)}] Processed {i} locations, found {len(self.all_artist_urls)} artists so far...")
            
            try:
                # Crawl base location page
                base_url = f"{self.base_url}/tattoo-artists/{location_slug}"
                artists = self.discover_artists_from_page(base_url, timeout=10)
                self.all_artist_urls.update(artists)
                total_pages_crawled += 1
                
                # Only check styles for locations that had artists (to save time)
                if artists:
                    # Discover and crawl style pages for this location
                    styles = self.discover_styles_for_location(location_slug)
                    if not styles:
                        # If no styles found, try known styles (but limit to 3 most common)
                        styles = list(known_styles)[:3]
                    
                    for style in styles[:5]:  # Limit to 5 styles per location
                        # Try different style URL patterns
                        style_urls = [
                            f"{self.base_url}/tattoo-artists/{location_slug}/{style}",
                            f"{self.base_url}/tattoo-artists/{location_slug}/{style}-1",
                        ]
                        
                        for style_url in style_urls:
                            if self.check_page_exists(style_url):
                                artists = self.discover_artists_from_page(style_url, timeout=10)
                                self.all_artist_urls.update(artists)
                                total_pages_crawled += 1
                                break  # Found valid style page, no need to try other patterns
            except Exception as e:
                print(f"    ⚠ Error processing {location_slug}: {e}")
                continue
        
        self.close_selenium()
        
        print(f"\n✓ Crawled {total_pages_crawled} pages total")
        return self.all_artist_urls
    
    def save_results(self, output_file="TATTOODO/discovered_pages_comprehensive.json"):
        """Save discovered URLs"""
        import os
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        categories = {
            'artists': sorted(self.all_artist_urls),
            'total_artists': len(self.all_artist_urls),
            'locations_found': len(self.all_locations),
            'styles_found': sorted(self.all_styles)
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(categories, f, indent=2, ensure_ascii=False)
        
        txt_file = output_file.replace('.json', '.txt')
        with open(txt_file, 'w', encoding='utf-8') as f:
            f.write(f"Total artists discovered: {len(self.all_artist_urls)}\n")
            f.write(f"Locations found: {len(self.all_locations)}\n")
            f.write(f"Styles found: {len(self.all_styles)}\n")
            f.write("=" * 60 + "\n\n")
            f.write("ARTISTS:\n")
            f.write("-" * 60 + "\n")
            for url in sorted(self.all_artist_urls):
                f.write(f"{url}\n")
        
        print(f"\n✅ Results saved to:")
        print(f"   - {output_file}")
        print(f"   - {txt_file}")
        print(f"\n📊 Final Summary:")
        print(f"   Artists: {len(self.all_artist_urls)}")
        print(f"   Locations: {len(self.all_locations)}")
        print(f"   Styles: {len(self.all_styles)}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Comprehensive tattoodo.com artist discovery')
    parser.add_argument('--max-locations', type=int, default=500, help='Maximum locations to check (default: 500)')
    parser.add_argument('--skip-check', action='store_true', help='Skip existence check (faster but may crawl invalid pages)')
    
    args = parser.parse_args()
    
    discoverer = ComprehensiveTattoodoDiscoverer()
    
    try:
        discoverer.discover_all(max_locations=args.max_locations, check_existence=not args.skip_check)
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
