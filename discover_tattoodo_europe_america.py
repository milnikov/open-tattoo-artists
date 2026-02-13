#!/usr/bin/env python3
"""
Discover artists by checking the 500 biggest cities in Europe and America
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
from concurrent.futures import ThreadPoolExecutor, as_completed

# European country codes
EUROPE_CODES = {
    'GB', 'FR', 'DE', 'IT', 'ES', 'PL', 'RO', 'NL', 'BE', 'GR', 'PT', 'CZ', 'HU', 'SE', 'AT', 'BG', 'DK', 'FI', 'SK', 'IE', 'HR', 'LT', 'SI', 'LV', 'EE', 'LU', 'MT', 'CY',
    'RU', 'UA', 'TR', 'CH', 'NO', 'IS', 'AL', 'BA', 'MK', 'ME', 'RS', 'XK', 'BY', 'MD', 'GE', 'AM', 'AZ', 'KZ', 'UZ', 'TM', 'TJ', 'KG', 'MN'
}

# American country codes (North and South America)
AMERICA_CODES = {
    'US', 'CA', 'MX', 'BR', 'AR', 'CO', 'PE', 'VE', 'CL', 'EC', 'GT', 'CU', 'BO', 'HT', 'DO', 'HN', 'PY', 'SV', 'NI', 'CR', 'PA', 'UY', 'JM', 'TT', 'BS', 'BB', 'BZ', 'SR', 'GY', 'GF', 'FK', 'PM', 'GL', 'AW', 'CW', 'SX', 'VG', 'VI', 'PR', 'GP', 'MQ', 'BL', 'MF', 'KY', 'BM', 'TC', 'AI', 'MS', 'VG', 'AG', 'DM', 'LC', 'VC', 'GD', 'KN'
}

class EuropeAmericaDiscoverer:
    def __init__(self, base_url="https://www.tattoodo.com"):
        self.base_url = base_url
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        self.driver = None
        self.all_artist_urls = set()
        self.valid_cities = []
        
    def setup_selenium(self):
        """Setup Selenium driver"""
        try:
            from selenium.webdriver.chrome.service import Service
            from webdriver_manager.chrome import ChromeDriverManager
        except ImportError:
            # Fallback to manual setup
            pass
        
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        
        try:
            # Try with webdriver-manager if available
            try:
                from selenium.webdriver.chrome.service import Service
                from webdriver_manager.chrome import ChromeDriverManager
                service = Service(ChromeDriverManager().install())
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
            except:
                # Fallback to default
                self.driver = webdriver.Chrome(options=chrome_options)
        except Exception as e:
            print(f"  ⚠ Warning: Could not setup Chrome driver: {e}")
            print(f"  Continuing with requests-only mode (may miss some artists)")
            self.driver = None
        
        return self.driver
    
    def close_selenium(self):
        """Close Selenium driver"""
        if self.driver:
            self.driver.quit()
            self.driver = None
    
    def normalize_city_name(self, city_name):
        """Convert city name to URL-friendly slug"""
        slug = city_name.lower()
        slug = re.sub(r'[^a-z0-9]+', '-', slug)
        slug = slug.strip('-')
        replacements = {
            'new-york': 'nyc',
            'los-angeles': 'la',
            'san-francisco': 'sf',
        }
        return replacements.get(slug, slug)
    
    def filter_cities_by_region(self, filename='cities_over_100k.json', max_cities=500):
        """Filter cities to only Europe and America, sorted by population"""
        print(f"\n🔍 Filtering cities from {filename}...")
        print(f"  Looking for top {max_cities} cities in Europe and America")
        
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                cities_data = json.load(f)
            
            # Filter to Europe and America
            filtered_cities = []
            for city in cities_data:
                country_code = city.get('country_code', '')
                if country_code in EUROPE_CODES or country_code in AMERICA_CODES:
                    filtered_cities.append(city)
            
            # Sort by population (descending) and take top N
            filtered_cities.sort(key=lambda x: x.get('population', 0), reverse=True)
            filtered_cities = filtered_cities[:max_cities]
            
            print(f"  ✓ Found {len(filtered_cities)} cities in Europe and America")
            
            # Convert to location slugs
            location_slugs = []
            seen_slugs = set()
            
            for city in filtered_cities:
                for name_field in ['name', 'ascii_name']:
                    if name_field in city:
                        slug = self.normalize_city_name(city[name_field])
                        if slug and slug not in seen_slugs:
                            location_slugs.append({
                                'slug': slug,
                                'name': city.get('name', ''),
                                'country': city.get('country_code', ''),
                                'population': city.get('population', 0),
                                'region': 'Europe' if city.get('country_code') in EUROPE_CODES else 'America'
                            })
                            seen_slugs.add(slug)
                            break
            
            print(f"  ✓ Generated {len(location_slugs)} unique location slugs")
            
            # Show breakdown
            europe_count = sum(1 for c in location_slugs if c['region'] == 'Europe')
            america_count = sum(1 for c in location_slugs if c['region'] == 'America')
            print(f"    - Europe: {europe_count} cities")
            print(f"    - America: {america_count} cities")
            
            return location_slugs
            
        except Exception as e:
            print(f"  ⚠ Error loading cities file: {e}")
            return []
    
    def check_city_page_exists(self, city_slug):
        """Check if a city page exists"""
        url = f"{self.base_url}/tattoo-artists/{city_slug}"
        try:
            response = requests.head(url, headers=self.headers, timeout=3, allow_redirects=False)
            return response.status_code == 200
        except:
            return False
    
    def find_valid_cities(self, city_data_list, max_workers=20):
        """Find which cities have pages on tattoodo.com"""
        print(f"\n🔍 Checking which cities have pages (using {max_workers} workers)...")
        valid_cities = []
        
        def check_city(city_info):
            if self.check_city_page_exists(city_info['slug']):
                return city_info
            return None
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_city = {executor.submit(check_city, city): city for city in city_data_list}
            
            for i, future in enumerate(as_completed(future_to_city), 1):
                if i % 50 == 0:
                    print(f"  [{i}/{len(city_data_list)}] Checked {i} cities, found {len(valid_cities)} valid...")
                
                result = future.result()
                if result:
                    valid_cities.append(result)
        
        print(f"  ✓ Found {len(valid_cities)} cities with pages")
        return valid_cities
    
    def discover_artists_from_city(self, city_slug):
        """Discover artists from a city page"""
        artist_urls = set()
        
        if not self.driver:
            self.setup_selenium()
        
        try:
            city_url = f"{self.base_url}/tattoo-artists/{city_slug}"
            self.driver.set_page_load_timeout(8)
            self.driver.get(city_url)
            time.sleep(1.5)
            
            # Scroll to load content
            for i in range(10):
                self.driver.execute_script("window.scrollBy(0, 500);")
                time.sleep(0.2)
                
                # Extract artist URLs
                links = self.driver.find_elements(By.TAG_NAME, "a")
                for link in links:
                    try:
                        href = link.get_attribute('href')
                        if href and '/artists/' in href:
                            parsed = urlparse(href)
                            if parsed.netloc == urlparse(self.base_url).netloc:
                                clean_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
                                if '/artists/' in clean_url and '/tattoo-artists/' not in clean_url:
                                    parts = clean_url.split('/artists/')
                                    if len(parts) > 1:
                                        path_after = parts[1].split('/')[0]
                                        if path_after and path_after not in ['', 'artists', 'book', 'portfolio', 'nearest']:
                                            artist_urls.add(clean_url)
                    except:
                        continue
            
            # Final scroll and extraction
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1)
            
            links = self.driver.find_elements(By.TAG_NAME, "a")
            for link in links:
                try:
                    href = link.get_attribute('href')
                    if href and '/artists/' in href:
                        parsed = urlparse(href)
                        if parsed.netloc == urlparse(self.base_url).netloc:
                            clean_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
                            if '/artists/' in clean_url and '/tattoo-artists/' not in clean_url:
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
    
    def load_existing_artists(self):
        """Load existing discovered artists"""
        try:
            with open('TATTOODO/discovered_pages_cities.json', 'r') as f:
                data = json.load(f)
                self.all_artist_urls = set(data.get('artists', []))
                print(f"📊 Loaded {len(self.all_artist_urls)} existing artists")
        except:
            try:
                with open('TATTOODO/discovered_pages_final.json', 'r') as f:
                    data = json.load(f)
                    self.all_artist_urls = set(data.get('artists', []))
                    print(f"📊 Loaded {len(self.all_artist_urls)} existing artists")
            except:
                pass
    
    def discover_all(self, max_cities=500, check_existence=True):
        """Discover all artists by checking city pages"""
        print("=" * 60)
        print("🔎 Discovering artists from top cities in Europe and America")
        print("=" * 60)
        
        # Load existing artists
        self.load_existing_artists()
        initial_count = len(self.all_artist_urls)
        
        # Filter and load cities
        city_data_list = self.filter_cities_by_region(max_cities=max_cities)
        
        if not city_data_list:
            print("  ⚠ No cities loaded, exiting")
            return self.all_artist_urls
        
        # Find valid cities
        if check_existence:
            valid_cities = self.find_valid_cities(city_data_list)
        else:
            valid_cities = city_data_list
        
        self.valid_cities = valid_cities
        print(f"\n🔍 Crawling {len(valid_cities)} city pages to find artists...")
        
        if not self.driver:
            self.setup_selenium()
        
        total_new = 0
        for i, city_info in enumerate(valid_cities, 1):
            city_slug = city_info['slug']
            city_name = city_info.get('name', city_slug)
            city_region = city_info.get('region', '')
            
            if i % 5 == 0:
                print(f"  [{i}/{len(valid_cities)}] Processed {i} cities, found {len(self.all_artist_urls)} artists ({len(self.all_artist_urls) - initial_count} new)...")
            
            try:
                artists = self.discover_artists_from_city(city_slug)
                before_count = len(self.all_artist_urls)
                self.all_artist_urls.update(artists)
                new_count = len(self.all_artist_urls) - before_count
                
                if new_count > 0:
                    print(f"    ✓ {city_name} ({city_slug}) [{city_region}]: {new_count} new artists")
                    total_new += new_count
            except Exception as e:
                print(f"    ⚠ Error processing {city_name}: {e}")
                continue
        
        self.close_selenium()
        
        print(f"\n✅ Discovery complete!")
        print(f"   Started with: {initial_count} artists")
        print(f"   Total artists: {len(self.all_artist_urls)}")
        print(f"   New artists found: {len(self.all_artist_urls) - initial_count}")
        print(f"   Valid cities found: {len(valid_cities)}")
        
        return self.all_artist_urls
    
    def save_results(self, output_file="TATTOODO/discovered_pages_europe_america.json"):
        """Save results"""
        import os
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        # Count by region
        europe_cities = [c for c in self.valid_cities if c.get('region') == 'Europe']
        america_cities = [c for c in self.valid_cities if c.get('region') == 'America']
        
        data = {
            'artists': sorted(self.all_artist_urls),
            'total': len(self.all_artist_urls),
            'valid_cities': len(self.valid_cities),
            'europe_cities': len(europe_cities),
            'america_cities': len(america_cities),
            'cities': [{'slug': c['slug'], 'name': c['name'], 'country': c['country'], 'region': c.get('region', '')} for c in self.valid_cities[:100]]
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        txt_file = output_file.replace('.json', '.txt')
        with open(txt_file, 'w', encoding='utf-8') as f:
            f.write(f"Total artists: {len(self.all_artist_urls)}\n")
            f.write(f"Valid cities: {len(self.valid_cities)} (Europe: {len(europe_cities)}, America: {len(america_cities)})\n")
            f.write("=" * 60 + "\n\n")
            f.write("ARTISTS:\n")
            f.write("-" * 60 + "\n")
            for url in sorted(self.all_artist_urls):
                f.write(f"{url}\n")
        
        print(f"\n✅ Results saved to:")
        print(f"   - {output_file}")
        print(f"   - {txt_file}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Discover artists from top cities in Europe and America')
    parser.add_argument('--max-cities', type=int, default=500, help='Maximum cities to check (default: 500)')
    parser.add_argument('--skip-check', action='store_true', help='Skip existence check (faster but may crawl invalid pages)')
    
    args = parser.parse_args()
    
    discoverer = EuropeAmericaDiscoverer()
    
    try:
        discoverer.discover_all(max_cities=args.max_cities, check_existence=not args.skip_check)
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

