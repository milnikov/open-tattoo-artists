#!/usr/bin/env python3
"""Test location extraction from parse_artist_page."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from parse import parse_artist_page

url = "https://tattooswizard.com/artists/0.5na"
print("Parsing", url)
p = parse_artist_page(url, headless=True, max_images=5)
if p:
    print("City:", repr(p.city))
    print("Country:", repr(p.country))
else:
    print("Parse returned None")
