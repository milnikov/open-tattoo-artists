#!/usr/bin/env python3
"""
Script to fetch and compile a list of all cities in the world with population over 100,000.
Uses GeoNames database and other public sources.
"""

import requests
import json
import csv
import time
from pathlib import Path
from typing import List, Dict
from _repo_root import repo_path

# GeoNames provides free city data
# We'll download their cities15000.zip (cities with population > 15000)
# and filter for cities > 100000
GEONAMES_CITIES_URL = "https://download.geonames.org/export/dump/cities15000.zip"
GEONAMES_CITIES_FILE = "cities15000.txt"

# Alternative: Use GeoNames API (requires free account)
# For now, we'll use a direct download approach


def download_geonames_cities() -> List[Dict]:
    """
    Download cities data from GeoNames.
    Returns list of cities with population > 100000.
    """
    print("Downloading cities data from GeoNames...")
    
    try:
        # Download the cities file
        response = requests.get(GEONAMES_CITIES_URL, stream=True, timeout=30)
        response.raise_for_status()
        
        # Save to temporary file
        import zipfile
        import io
        
        zip_file = zipfile.ZipFile(io.BytesIO(response.content))
        cities_data = zip_file.read(GEONAMES_CITIES_FILE).decode('utf-8')
        
        cities = []
        for line in cities_data.strip().split('\n'):
            if not line.strip():
                continue
                
            parts = line.split('\t')
            if len(parts) < 15:
                continue
                
            try:
                geonameid = parts[0]
                name = parts[1]
                ascii_name = parts[2]
                alternate_names = parts[3]
                latitude = float(parts[4])
                longitude = float(parts[5])
                feature_class = parts[6]
                feature_code = parts[7]
                country_code = parts[8]
                cc2 = parts[9]
                admin1_code = parts[10]
                admin2_code = parts[11]
                admin3_code = parts[12]
                admin4_code = parts[13]
                population = int(parts[14]) if parts[14] else 0
                elevation = parts[15] if len(parts) > 15 else None
                dem = parts[16] if len(parts) > 16 else None
                timezone = parts[17] if len(parts) > 17 else None
                modification_date = parts[18] if len(parts) > 18 else None
                
                # Filter for cities with population > 100000
                if population >= 100000:
                    city = {
                        'geonameid': geonameid,
                        'name': name,
                        'ascii_name': ascii_name,
                        'country_code': country_code,
                        'latitude': latitude,
                        'longitude': longitude,
                        'population': population,
                        'timezone': timezone,
                        'admin1_code': admin1_code,
                        'admin2_code': admin2_code,
                    }
                    cities.append(city)
                    
            except (ValueError, IndexError) as e:
                continue
        
        print(f"Found {len(cities)} cities with population >= 100,000")
        return cities
        
    except Exception as e:
        print(f"Error downloading from GeoNames: {e}")
        print("Trying alternative approach...")
        return []


def get_cities_from_simplemaps() -> List[Dict]:
    """
    Alternative: Use SimpleMaps world cities database (free tier available)
    """
    print("Trying SimpleMaps world cities database...")
    
    # SimpleMaps provides a free CSV with world cities
    # URL: https://simplemaps.com/data/world-cities
    # For now, we'll note this as an alternative
    
    # You can download manually from: https://simplemaps.com/static/data/world-cities/basic/simplemaps_worldcities_basicv1.75.zip
    return []


def save_cities_json(cities: List[Dict], filename: str = "data/cities/cities_over_100k.json"):
    """Save cities to JSON file (path relative to repo root unless absolute)"""
    output_path = Path(filename) if Path(filename).is_absolute() else repo_path(filename)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Sort by population descending
    cities_sorted = sorted(cities, key=lambda x: x['population'], reverse=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(cities_sorted, f, indent=2, ensure_ascii=False)
    
    print(f"Saved {len(cities_sorted)} cities to {output_path}")
    return output_path


def save_cities_csv(cities: List[Dict], filename: str = "data/cities/cities_over_100k.csv"):
    """Save cities to CSV file (path relative to repo root unless absolute)"""
    output_path = Path(filename) if Path(filename).is_absolute() else repo_path(filename)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    if not cities:
        print("No cities to save")
        return None
    
    # Sort by population descending
    cities_sorted = sorted(cities, key=lambda x: x['population'], reverse=True)
    
    fieldnames = ['geonameid', 'name', 'ascii_name', 'country_code', 
                  'latitude', 'longitude', 'population', 'timezone', 
                  'admin1_code', 'admin2_code']
    
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(cities_sorted)
    
    print(f"Saved {len(cities_sorted)} cities to {output_path}")
    return output_path


def save_cities_txt(cities: List[Dict], filename: str = "data/cities/cities_over_100k.txt"):
    """Save cities to simple text file (path relative to repo root unless absolute)"""
    output_path = Path(filename) if Path(filename).is_absolute() else repo_path(filename)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Sort by population descending
    cities_sorted = sorted(cities, key=lambda x: x['population'], reverse=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(f"Total cities with population >= 100,000: {len(cities_sorted)}\n")
        f.write("=" * 80 + "\n\n")
        
        for city in cities_sorted:
            f.write(f"{city['name']}, {city['country_code']} - Population: {city['population']:,}\n")
            f.write(f"  Location: {city['latitude']}, {city['longitude']}\n")
            f.write(f"  GeoNames ID: {city['geonameid']}\n")
            if city.get('timezone'):
                f.write(f"  Timezone: {city['timezone']}\n")
            f.write("\n")
    
    print(f"Saved {len(cities_sorted)} cities to {output_path}")
    return output_path


def main():
    """Main function to fetch and save cities data"""
    print("=" * 80)
    print("Fetching cities with population >= 100,000")
    print("=" * 80)
    
    # Try to download from GeoNames
    cities = download_geonames_cities()
    
    if not cities:
        print("\nCould not download cities data automatically.")
        print("\nAlternative options:")
        print("1. Download manually from GeoNames:")
        print("   https://download.geonames.org/export/dump/cities15000.zip")
        print("   Extract and run this script with the cities15000.txt file")
        print("\n2. Use SimpleMaps world cities database:")
        print("   https://simplemaps.com/static/data/world-cities/basic/simplemaps_worldcities_basicv1.75.zip")
        print("\n3. Use GeoNames API (requires free account):")
        print("   https://www.geonames.org/export/web-services.html")
        return
    
    # Save in multiple formats
    print("\nSaving cities data...")
    save_cities_json(cities)
    save_cities_csv(cities)
    save_cities_txt(cities)
    
    # Print summary
    print("\n" + "=" * 80)
    print("Summary:")
    print(f"Total cities found: {len(cities)}")
    if cities:
        # Cities are sorted by population descending
        cities_sorted = sorted(cities, key=lambda x: x['population'], reverse=True)
        print(f"Largest city: {cities_sorted[0]['name']}, {cities_sorted[0]['country_code']} - {cities_sorted[0]['population']:,}")
        print(f"Smallest city: {cities_sorted[-1]['name']}, {cities_sorted[-1]['country_code']} - {cities_sorted[-1]['population']:,}")
    print("=" * 80)


if __name__ == "__main__":
    main()

