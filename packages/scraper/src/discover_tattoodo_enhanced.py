#!/usr/bin/env python3
"""
Enhanced script to discover all artist pages on tattoodo.com
- Checks for API endpoints
- Discovers more location pages
- Finds additional entry points
"""

import requests
import re
import json
import time
from urllib.parse import urljoin, urlparse, parse_qs
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities

class EnhancedTattoodoDiscoverer:
    def __init__(self, base_url="https://www.tattoodo.com"):
        self.base_url = base_url
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        self.driver = None
        self.api_endpoints = set()
        self.all_artist_urls = set()
        
    def setup_selenium_with_logging(self):
        """Setup Selenium with network logging to capture API calls"""
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--window-size=1920,1080')
        
        # Enable performance logging to capture network requests
        caps = DesiredCapabilities.CHROME
        caps['goog:loggingPrefs'] = {'performance': 'ALL'}
        
        self.driver = webdriver.Chrome(options=chrome_options, desired_capabilities=caps)
        return self.driver
    
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
    
    def discover_api_endpoints(self):
        """Try common API endpoint patterns"""
        print("\n🔍 Checking for API endpoints...")
        
        api_endpoints = set()
        
        # Try common API endpoint patterns
        common_patterns = [
            f"{self.base_url}/api/artists",
            f"{self.base_url}/api/v1/artists",
            f"{self.base_url}/api/v2/artists",
            f"{self.base_url}/graphql",
            f"{self.base_url}/rest/artists",
            f"{self.base_url}/api/search/artists",
        ]
        
        for endpoint in common_patterns:
            try:
                response = requests.get(endpoint, headers=self.headers, timeout=5)
                if response.status_code == 200:
                    api_endpoints.add(endpoint)
                    print(f"    ✓ Found working endpoint: {endpoint}")
                    # Try to extract artist data
                    try:
                        data = response.json()
                        json_str = json.dumps(data)
                        artist_matches = re.findall(r'/artists/[a-zA-Z0-9_-]+', json_str)
                        if artist_matches:
                            print(f"      Found {len(set(artist_matches))} artist references")
                    except:
                        pass
            except:
                pass
        
        self.api_endpoints = api_endpoints
        return api_endpoints
    
    def query_api_endpoint(self, endpoint):
        """Try to query an API endpoint for artist data"""
        print(f"\n  Trying to query: {endpoint[:80]}...")
        artist_urls = set()
        
        try:
            # Try different query parameters
            params_variations = [
                {},
                {'limit': 1000},
                {'page': 1, 'limit': 1000},
                {'offset': 0, 'limit': 1000},
            ]
            
            for params in params_variations:
                try:
                    response = requests.get(endpoint, params=params, headers=self.headers, timeout=10)
                    if response.status_code == 200:
                        data = response.json()
                        # Try to extract artist URLs from JSON response
                        json_str = json.dumps(data)
                        artist_matches = re.findall(r'/artists/[a-zA-Z0-9_-]+', json_str)
                        for match in artist_matches:
                            artist_urls.add(f"{self.base_url}{match}")
                        if artist_urls:
                            print(f"    ✓ Found {len(artist_urls)} artist URLs from API")
                            return artist_urls
                except:
                    continue
        except Exception as e:
            print(f"    ✗ Error querying API: {e}")
        
        return artist_urls
    
    def discover_all_locations(self):
        """Discover all location pages from various sources"""
        print("\n🔍 Discovering all location pages...")
        
        location_urls = set()
        
        # Method 1: From sitemap
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
                        location_urls.add(url)
        except Exception as e:
            print(f"  ⚠ Error reading sitemap: {e}")
        
        # Method 2: From main artists page
        if not self.driver:
            self.setup_selenium()
        
        try:
            print("  Checking main artists page for location links...")
            self.driver.get(f"{self.base_url}/tattoo-artists")
            time.sleep(3)
            
            # Find all location links
            links = self.driver.find_elements(By.TAG_NAME, "a")
            for link in links:
                try:
                    href = link.get_attribute('href')
                    if href and '/tattoo-artists/' in href:
                        location_urls.add(href)
                except:
                    continue
        except Exception as e:
            print(f"  ⚠ Error checking main page: {e}")
        
        # Method 3: Try common city names and check if they exist
        print("  Trying common city names...")
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
        
        # Check which cities actually have pages
        print(f"  Checking {len(common_cities)} city pages...")
        valid_locations = 0
        for city in common_cities:
            url = f"{self.base_url}/tattoo-artists/{city}"
            try:
                response = requests.head(url, headers=self.headers, timeout=5, allow_redirects=False)
                if response.status_code == 200:
                    location_urls.add(url)
                    valid_locations += 1
            except:
                location_urls.add(url)  # Add anyway, might work with Selenium
        
        print(f"    ✓ Found {valid_locations} valid city pages")
        
        print(f"  ✓ Found {len(location_urls)} location pages")
        return location_urls
    
    def discover_artists_from_location(self, location_url):
        """Discover artists from a location page"""
        artist_urls = set()
        try:
            if not self.driver:
                self.setup_selenium()
            
            self.driver.get(location_url)
            time.sleep(3)
            
            # Scroll to load content
            for i in range(30):
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
            
            # Final scroll
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            
        except Exception as e:
            pass
        
        return artist_urls
    
    def discover_all(self):
        """Discover all artists using multiple methods"""
        print("=" * 60)
        print("🔎 Enhanced discovery of all artist pages on tattoodo.com")
        print("=" * 60)
        
        all_artist_urls = set()
        
        # Method 1: Discover API endpoints
        api_endpoints = self.discover_api_endpoints()
        if api_endpoints:
            print(f"\n  Found {len(api_endpoints)} potential API endpoints")
            for endpoint in api_endpoints:
                artist_urls = self.query_api_endpoint(endpoint)
                all_artist_urls.update(artist_urls)
        
        # Method 2: Discover all location pages
        location_urls = self.discover_all_locations()
        
        # Method 3: Crawl all location pages
        print(f"\n🔍 Crawling {len(location_urls)} location pages...")
        for i, location_url in enumerate(sorted(location_urls), 1):
            if i % 10 == 0:
                print(f"  [{i}/{len(location_urls)}] Crawled {i} pages, found {len(all_artist_urls)} artists so far...")
            artist_urls = self.discover_artists_from_location(location_url)
            all_artist_urls.update(artist_urls)
        
        # Clean up
        self.close_selenium()
        
        self.all_artist_urls = all_artist_urls
        return all_artist_urls
    
    def save_results(self, output_file="TATTOODO/discovered_pages_enhanced.json"):
        from _repo_root import repo_path
        from pathlib import Path
        p = Path(output_file) if Path(output_file).is_absolute() else repo_path(output_file)
        output_file = str(p)
        p.parent.mkdir(parents=True, exist_ok=True)
        
        categories = {
            'artists': sorted(self.all_artist_urls),
            'api_endpoints': sorted(self.api_endpoints)
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(categories, f, indent=2, ensure_ascii=False)
        
        txt_file = output_file.replace('.json', '.txt')
        with open(txt_file, 'w', encoding='utf-8') as f:
            f.write(f"Total artists discovered: {len(self.all_artist_urls)}\n")
            f.write(f"API endpoints found: {len(self.api_endpoints)}\n")
            f.write("=" * 60 + "\n\n")
            f.write("ARTISTS:\n")
            f.write("-" * 60 + "\n")
            for url in sorted(self.all_artist_urls):
                f.write(f"{url}\n")
        
        print(f"\n✅ Results saved to:")
        print(f"   - {output_file}")
        print(f"   - {txt_file}")
        print(f"\n📊 Summary:")
        print(f"   Artists: {len(self.all_artist_urls)}")
        print(f"   API endpoints: {len(self.api_endpoints)}")


def main():
    discoverer = EnhancedTattoodoDiscoverer()
    
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

