#!/usr/bin/env python3
"""
Enhanced script to discover all location and style pages on tattoodo.com
to find more artists
"""
from pathlib import Path
from _repo_root import repo_path

import requests
import re
import json
import time
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options

class LocationStyleDiscoverer:
    def __init__(self, base_url="https://www.tattoodo.com"):
        self.base_url = base_url
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        self.driver = None
        self.all_locations = set()
        self.all_styles = set()
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
    
    def discover_locations_from_sitemap(self):
        """Discover all locations from sitemap"""
        print("\n🔍 Discovering locations from sitemap...")
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
                        # Extract location slug
                        parts = url.split('/tattoo-artists/')
                        if len(parts) > 1:
                            location_slug = parts[1].split('/')[0]
                            if location_slug and not any(char.isdigit() for char in location_slug):
                                locations.add(location_slug)
        except Exception as e:
            print(f"  ⚠ Error: {e}")
        
        print(f"  ✓ Found {len(locations)} locations from sitemap")
        return locations
    
    def discover_locations_from_page(self):
        """Discover locations by crawling the main artists page"""
        print("\n🔍 Discovering locations from main artists page...")
        locations = set()
        
        if not self.driver:
            self.setup_selenium()
        
        try:
            self.driver.get(f"{self.base_url}/tattoo-artists")
            time.sleep(5)
            
            # Scroll to load content
            for i in range(10):
                self.driver.execute_script("window.scrollBy(0, 500);")
                time.sleep(0.5)
            
            # Find all location links
            links = self.driver.find_elements(By.TAG_NAME, "a")
            for link in links:
                try:
                    href = link.get_attribute('href')
                    if href and '/tattoo-artists/' in href:
                        parts = href.split('/tattoo-artists/')
                        if len(parts) > 1:
                            location_slug = parts[1].split('/')[0]
                            if location_slug and not any(char.isdigit() for char in location_slug):
                                locations.add(location_slug)
                except:
                    continue
            
            # Also extract from page source
            page_source = self.driver.page_source
            location_patterns = [
                r'/tattoo-artists/([a-z-]+)',
                r'href=["\']/tattoo-artists/([a-z-]+)',
            ]
            
            for pattern in location_patterns:
                matches = re.findall(pattern, page_source, re.IGNORECASE)
                for match in matches:
                    if match and not any(char.isdigit() for char in match):
                        locations.add(match)
        except Exception as e:
            print(f"  ⚠ Error: {e}")
        
        print(f"  ✓ Found {len(locations)} locations from page")
        return locations
    
    def discover_all_styles(self):
        """Discover all available styles by checking a few major locations"""
        print("\n🔍 Discovering all available styles...")
        all_styles = set()
        
        # Check a few major locations to get comprehensive style list
        major_locations = ['nyc', 'la', 'london', 'miami', 'chicago']
        
        for location in major_locations:
            try:
                styles_url = f"{self.base_url}/tattoo-artists/{location}/styles"
                response = requests.get(styles_url, headers=self.headers, timeout=10)
                if response.status_code == 200:
                    # Extract styles from HTML
                    style_pattern = rf'/styles/([a-z_]+)'
                    matches = re.findall(style_pattern, response.text, re.IGNORECASE)
                    for match in matches:
                        if match and match not in ['newest', 'featured']:
                            all_styles.add(match)
            except:
                continue
        
        print(f"  ✓ Found {len(all_styles)} unique styles")
        return all_styles
    
    def discover_styles_from_location_page(self, location):
        """Discover all styles available for a location (simplified)"""
        styles = set()
        
        try:
            # Quick check via requests first
            styles_url = f"{self.base_url}/tattoo-artists/{location}/styles"
            response = requests.get(styles_url, headers=self.headers, timeout=5)
            if response.status_code == 200:
                style_pattern = rf'/styles/([a-z_]+)'
                matches = re.findall(style_pattern, response.text, re.IGNORECASE)
                for match in matches:
                    if match and match not in ['newest', 'featured']:
                        styles.add(match)
        except:
            pass
        
        return styles
    
    def discover_artists_from_location_style(self, location, style=None):
        """Discover artists from a location/style page"""
        artist_urls = set()
        
        if not self.driver:
            self.setup_selenium()
        
        try:
            if style:
                url = f"{self.base_url}/tattoo-artists/{location}/styles/{style}"
            else:
                url = f"{self.base_url}/tattoo-artists/{location}"
            
            self.driver.get(url)
            time.sleep(3)
            
            # Scroll aggressively to load all content
            previous_count = 0
            no_change_count = 0
            
            for i in range(50):
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
                
                # Check if we're still finding new artists
                current_count = len(artist_urls)
                if current_count == previous_count:
                    no_change_count += 1
                    if no_change_count >= 5:
                        break
                else:
                    no_change_count = 0
                
                previous_count = current_count
            
            # Final scroll to bottom
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            
        except Exception as e:
            pass
        
        return artist_urls
    
    def discover_all(self):
        """Discover all locations, styles, and artists"""
        print("=" * 60)
        print("🔎 Discovering all locations, styles, and artists")
        print("=" * 60)
        
        # Step 1: Discover all locations
        locations_from_sitemap = self.discover_locations_from_sitemap()
        locations_from_page = self.discover_locations_from_page()
        all_locations = locations_from_sitemap | locations_from_page
        
        # Add common cities
        common_cities = [
            'new-york', 'nyc', 'los-angeles', 'la', 'chicago', 'houston', 'phoenix',
            'philadelphia', 'san-antonio', 'san-diego', 'dallas', 'san-jose',
            'austin', 'jacksonville', 'san-francisco', 'indianapolis', 'columbus',
            'fort-worth', 'charlotte', 'seattle', 'denver', 'washington', 'boston',
            'el-paso', 'detroit', 'nashville', 'portland', 'oklahoma-city', 'las-vegas',
            'memphis', 'louisville', 'baltimore', 'milwaukee', 'albuquerque', 'tucson',
            'fresno', 'sacramento', 'kansas-city', 'mesa', 'atlanta', 'omaha',
            'colorado-springs', 'raleigh', 'virginia-beach', 'miami', 'oakland',
            'minneapolis', 'tulsa', 'cleveland', 'wichita', 'arlington',
            'london', 'paris', 'berlin', 'madrid', 'rome', 'amsterdam', 'vienna',
            'prague', 'budapest', 'stockholm', 'copenhagen', 'oslo', 'helsinki',
            'dublin', 'lisbon', 'warsaw', 'athens', 'brussels', 'zurich', 'milan',
            'barcelona', 'manchester', 'birmingham', 'glasgow', 'edinburgh',
            'toronto', 'vancouver', 'montreal', 'calgary', 'ottawa', 'edmonton',
            'sydney', 'melbourne', 'brisbane', 'perth', 'adelaide', 'auckland',
            'tokyo', 'seoul', 'singapore', 'hong-kong', 'bangkok', 'manila',
            'mumbai', 'delhi', 'bangalore', 'chennai', 'kolkata', 'hyderabad',
            'sao-paulo', 'rio-de-janeiro', 'buenos-aires', 'lima', 'bogota',
            'santiago', 'montevideo', 'caracas', 'guatemala-city', 'havana',
        ]
        all_locations.update(common_cities)
        
        self.all_locations = all_locations
        print(f"\n✓ Total unique locations: {len(all_locations)}")
        
        # Step 2: Discover all available styles (check a few major locations)
        all_available_styles = self.discover_all_styles()
        self.all_styles = all_available_styles
        
        # For efficiency, assume all locations have the same styles
        # (we can verify this later if needed)
        location_style_map = {}
        for location in all_locations:
            location_style_map[location] = all_available_styles
        
        print(f"\n✓ Will check {len(all_available_styles)} styles for each location")
        
        # Step 3: Discover artists from location pages (no style filter)
        print(f"\n🔍 Discovering artists from location pages...")
        for i, location in enumerate(sorted(all_locations), 1):
            if i % 20 == 0:
                print(f"  [{i}/{len(all_locations)}] Crawled {i} locations, found {len(self.all_artist_urls)} artists...")
            artist_urls = self.discover_artists_from_location_style(location)
            self.all_artist_urls.update(artist_urls)
        
        # Step 4: Discover artists from location+style pages
        print(f"\n🔍 Discovering artists from location+style pages...")
        total_combinations = sum(len(styles) for styles in location_style_map.values())
        current = 0
        
        for location, styles in location_style_map.items():
            for style in styles:
                current += 1
                if current % 50 == 0:
                    print(f"  [{current}/{total_combinations}] Crawled {current} combinations, found {len(self.all_artist_urls)} artists...")
                artist_urls = self.discover_artists_from_location_style(location, style)
                self.all_artist_urls.update(artist_urls)
        
        self.close_selenium()
        return self.all_artist_urls
    
    def save_results(self, output_file="TATTOODO/discovered_pages_extended.json"):
        """Save discovered URLs (path relative to repo root unless absolute)"""
        p = Path(output_file) if Path(output_file).is_absolute() else repo_path(output_file)
        output_file = str(p)
        p.parent.mkdir(parents=True, exist_ok=True)
        
        # Load existing results
        try:
            with open(repo_path('TATTOODO', 'discovered_pages.json'), 'r') as f:
                existing = json.load(f)
            existing_artists = set(existing.get('artists', []))
        except:
            existing_artists = set()
        
        # Merge with new discoveries
        all_artists = existing_artists | self.all_artist_urls
        
        categories = {
            'artists': sorted(all_artists),
            'locations': sorted(self.all_locations),
            'styles': sorted(self.all_styles),
            'new_artists': sorted(self.all_artist_urls - existing_artists),
            'total_artists': len(all_artists),
            'new_artists_count': len(self.all_artist_urls - existing_artists)
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(categories, f, indent=2, ensure_ascii=False)
        
        txt_file = output_file.replace('.json', '.txt')
        with open(txt_file, 'w', encoding='utf-8') as f:
            f.write(f"Total artists discovered: {len(all_artists)}\n")
            f.write(f"New artists found: {len(self.all_artist_urls - existing_artists)}\n")
            f.write(f"Locations found: {len(self.all_locations)}\n")
            f.write(f"Styles found: {len(self.all_styles)}\n")
            f.write("=" * 60 + "\n\n")
            f.write("NEW ARTISTS:\n")
            f.write("-" * 60 + "\n")
            for url in sorted(self.all_artist_urls - existing_artists):
                f.write(f"{url}\n")
        
        print(f"\n✅ Results saved to:")
        print(f"   - {output_file}")
        print(f"   - {txt_file}")
        print(f"\n📊 Summary:")
        print(f"   Total artists: {len(all_artists)}")
        print(f"   New artists found: {len(self.all_artist_urls - existing_artists)}")
        print(f"   Locations: {len(self.all_locations)}")
        print(f"   Styles: {len(self.all_styles)}")


def main():
    discoverer = LocationStyleDiscoverer()
    
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

