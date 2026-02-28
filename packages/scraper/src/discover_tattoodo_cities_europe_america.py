#!/usr/bin/env python3
"""
Discover artists by checking city pages. Run from repo root.
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
from concurrent.futures import ThreadPoolExecutor, as_completed

class CityBasedDiscoverer:
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
    
    def load_cities_from_file(self, filename='TATTOODO/cities_europe_america_500.json', max_cities=500):
        """Load cities from JSON file and convert to location slugs"""
        path = Path(filename) if Path(filename).is_absolute() else repo_path(filename)
        print(f"\n🔍 Loading cities from {path}...")
        try:
            with open(path, 'r', encoding='utf-8') as f:
                cities_data = json.load(f)
            
            location_slugs = []
            seen_slugs = set()
            
            if isinstance(cities_data, list):
                for city in cities_data[:max_cities]:
                    # Try both name and ascii_name
                    for name_field in ['name', 'ascii_name']:
                        if name_field in city:
                            slug = self.normalize_city_name(city[name_field])
                            if slug and slug not in seen_slugs:
                                location_slugs.append({
                                    'slug': slug,
                                    'name': city.get('name', ''),
                                    'country': city.get('country_code', ''),
                                    'population': city.get('population', 0)
                                })
                                seen_slugs.add(slug)
                                break  # Use first valid slug
            
            print(f"  ✓ Generated {len(location_slugs)} unique location slugs")
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
                if i % 100 == 0:
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
            self.driver.set_page_load_timeout(8)  # Reduced timeout
            self.driver.get(city_url)
            time.sleep(1.5)  # Reduced wait time
            
            # Scroll to load content (fewer scrolls)
            for i in range(10):  # Reduced from 15
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
                                # Only include actual artist pages, not location/style pages
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
            time.sleep(1)  # Reduced wait time
            
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
            with open(repo_path('TATTOODO', 'discovered_pages_final.json'), 'r') as f:
                data = json.load(f)
                self.all_artist_urls = set(data.get('artists', []))
                print(f"📊 Loaded {len(self.all_artist_urls)} existing artists")
        except:
            try:
                with open(repo_path('TATTOODO', 'discovered_pages.json'), 'r') as f:
                    data = json.load(f)
                    self.all_artist_urls = set(data.get('artists', []))
                    print(f"📊 Loaded {len(self.all_artist_urls)} existing artists")
            except:
                pass
    
    def discover_all(self, max_cities=500, check_existence=True):
        """Discover all artists by checking city pages"""
        print("=" * 60)
        print("🔎 Discovering artists by checking city pages")
        print("=" * 60)
        
        # Load existing artists
        self.load_existing_artists()
        initial_count = len(self.all_artist_urls)
        
        # Load cities
        city_data_list = self.load_cities_from_file(max_cities=max_cities)
        
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
            
            # More frequent progress updates
            if i % 5 == 0:
                print(f"  [{i}/{len(valid_cities)}] Processed {i} cities, found {len(self.all_artist_urls)} artists ({len(self.all_artist_urls) - initial_count} new)...")
            
            try:
                artists = self.discover_artists_from_city(city_slug)
                before_count = len(self.all_artist_urls)
                self.all_artist_urls.update(artists)
                new_count = len(self.all_artist_urls) - before_count
                
                if new_count > 0:
                    print(f"    ✓ {city_name} ({city_slug}): {new_count} new artists")
                    total_new += new_count
            except Exception as e:
                print(f"    ⚠ Error processing {city_name}: {e}")
                # Save progress periodically
                if i % 50 == 0:
                    self.save_results(f"TATTOODO/discovered_pages_cities_progress_{i}.json")
                continue
        
        self.close_selenium()
        
        print(f"\n✅ Discovery complete!")
        print(f"   Started with: {initial_count} artists")
        print(f"   Total artists: {len(self.all_artist_urls)}")
        print(f"   New artists found: {len(self.all_artist_urls) - initial_count}")
        print(f"   Valid cities found: {len(valid_cities)}")
        
        return self.all_artist_urls
    
    def save_results(self, output_file="TATTOODO/discovered_pages_cities.json"):
        """Save results (path relative to repo root unless absolute)"""
        p = Path(output_file) if Path(output_file).is_absolute() else repo_path(output_file)
        output_file = str(p)
        p.parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            'artists': sorted(self.all_artist_urls),
            'total': len(self.all_artist_urls),
            'valid_cities': len(self.valid_cities),
            'cities': [{'slug': c['slug'], 'name': c['name'], 'country': c['country']} for c in self.valid_cities[:50]]
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        txt_file = output_file.replace('.json', '.txt')
        with open(txt_file, 'w', encoding='utf-8') as f:
            f.write(f"Total artists: {len(self.all_artist_urls)}\n")
            f.write(f"Valid cities: {len(self.valid_cities)}\n")
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
    parser = argparse.ArgumentParser(description='Discover artists by checking city pages')
    parser.add_argument('--max-cities', type=int, default=500, help='Maximum cities to check (default: 500)')
    parser.add_argument('--skip-check', action='store_true', help='Skip existence check (faster but may crawl invalid pages)')
    
    args = parser.parse_args()
    
    discoverer = CityBasedDiscoverer()
    
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

