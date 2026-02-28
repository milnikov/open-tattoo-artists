#!/usr/bin/env python3
"""
Summarize tattoodo.com artist discovery results. Run from repo root.
"""
import json
from _repo_root import repo_path

def main():
    # Load results
    try:
        with open(repo_path('TATTOODO', 'discovered_pages.json'), 'r') as f:
            data = json.load(f)
        artists = set(data.get('artists', []))
    except Exception as e:
        print(f"Error loading discovered_pages.json: {e}")
        return
    
    # Filter out sub-pages
    clean_artists = set()
    for url in artists:
        if '/artists/' in url:
            parts = url.split('/artists/')
            if len(parts) > 1:
                path_after = parts[1].split('/')[0]
                if path_after and path_after not in ['', 'artists', 'book', 'portfolio', 'nearest']:
                    clean_artists.add(url)
    
    print("=" * 60)
    print("TATTOODO.COM ARTIST DISCOVERY SUMMARY")
    print("=" * 60)
    print(f"\nTotal artist URLs found: {len(artists)}")
    print(f"Clean artist URLs (no sub-pages): {len(clean_artists)}")
    print(f"\nSources:")
    print(f"  - sitemap-partners.xml: ~886 artists")
    print(f"  - Location/style pages: ~264 artists")
    print(f"  - Main artists directory: ~12 artists")
    print(f"\nNote: Some artists may appear in multiple sources")
    
    # Save clean list
    clean_data = {
        'artists': sorted(clean_artists),
        'total': len(clean_artists)
    }
    
    with open(repo_path('TATTOODO', 'discovered_pages_clean.json'), 'w', encoding='utf-8') as f:
        json.dump(clean_data, f, indent=2, ensure_ascii=False)
    
    with open(repo_path('TATTOODO', 'discovered_pages_clean.txt'), 'w', encoding='utf-8') as f:
        f.write(f"Total clean artist URLs: {len(clean_artists)}\n")
        f.write("=" * 60 + "\n\n")
        for url in sorted(clean_artists):
            f.write(f"{url}\n")
    
    print(f"\n✅ Clean results saved to TATTOODO/discovered_pages_clean.json and .txt")
    
    print(f"\nSample artists:")
    for url in sorted(clean_artists)[:10]:
        print(f"  {url}")

if __name__ == "__main__":
    main()


