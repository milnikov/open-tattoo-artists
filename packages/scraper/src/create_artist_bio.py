#!/usr/bin/env python3
"""
Script to create both artist-bio.txt and artistname.md files for tattoo artists
"""

import sys
import os
import requests
import re
from bs4 import BeautifulSoup

def create_artist_bio(artist_url, output_folder):
    """
    Create artist-bio.txt and artistname.md files with information from the artist's page
    
    Args:
        artist_url (str): URL of the artist's page
        output_folder (str): Folder to save the files
    """
    print(f"Fetching artist info from: {artist_url}")
    
    # Make sure the output folder exists
    os.makedirs(output_folder, exist_ok=True)
    
    # Get the page content
    headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'}
    try:
        response = requests.get(artist_url, headers=headers, timeout=10)
        response.raise_for_status()
    except Exception as e:
        print(f"Error fetching artist page: {e}")
        return False
    
    # Parse the HTML
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Extract the artist name from the URL
    artist_slug = artist_url.split('/')[-1]
    artist_name = artist_slug.replace('_', ' ').title()
    
    # Find the About section - try different approaches
    bio_content = None
    
    # Approach 1: Look for h2 with 'About' text
    about_section = soup.find('h2', string='About')
    if about_section:
        # Get the paragraph after the About heading
        bio_text = about_section.find_next('p')
        if bio_text:
            bio_content = bio_text.text.strip()
    
    # Approach 2: Look for any element containing 'About' and then find nearby paragraphs
    if not bio_content:
        about_elements = soup.find_all(string=lambda text: text and 'About' in text)
        for element in about_elements:
            parent = element.parent
            if parent:
                # Look for paragraphs near this element
                paragraphs = parent.find_all_next('p', limit=3)
                if paragraphs:
                    for p in paragraphs:
                        if len(p.text.strip()) > 50:  # Likely a bio paragraph if it's long enough
                            bio_content = p.text.strip()
                            break
                    if bio_content:
                        break
    
    # Approach 3: Just find all paragraphs and look for one that seems like a bio
    if not bio_content:
        paragraphs = soup.find_all('p')
        for p in paragraphs:
            text = p.text.strip()
            # A bio paragraph is usually long and contains words like 'artist', 'tattoo', etc.
            if len(text) > 100 and ('artist' in text.lower() or 'tattoo' in text.lower()):
                bio_content = text
                break
            
    # Extract additional information
    location = None
    price_range = None
    style = []
    instagram_followers = None
    
    # Try to find location
    location_section = soup.find(string=re.compile('Current location:', re.IGNORECASE))
    if location_section and location_section.parent:
        location_text = location_section.parent.get_text()
        location_match = re.search(r'Current location:\s*([^\n]+)', location_text)
        if location_match:
            location = location_match.group(1).strip()
    
    # Try to find price range
    price_section = soup.find(string=re.compile('Price:', re.IGNORECASE))
    if price_section and price_section.parent:
        price_text = price_section.parent.get_text()
        price_match = re.search(r'Price:\s*([^\n]+)', price_text)
        if price_match:
            price_range = price_match.group(1).strip()
    
    # Try to extract style from bio
    if bio_content:
        # Common tattoo styles to look for
        styles = ['traditional', 'neo-traditional', 'realism', 'watercolor', 'tribal', 
                 'japanese', 'blackwork', 'dotwork', 'geometric', 'illustrative', 
                 'minimalist', 'portrait', 'anime', 'fineline', 'script', 'lettering',
                 'black and grey', 'color', 'surrealism', 'abstract']
        
        bio_lower = bio_content.lower()
        for s in styles:
            if s in bio_lower:
                style.append(s.title())
        
        # Look for Instagram followers mention
        follower_patterns = [
            r'(\d+)\s*million\s*followers',
            r'(\d+)\s*m\s*followers',
            r'over\s*(\d+)\s*million',
            r'(\d+(?:\.\d+)?)\s*million',
            r'(\d+)\s*k\s*followers',
            r'(\d+,\d+)\s*followers'
        ]
        
        for pattern in follower_patterns:
            match = re.search(pattern, bio_lower)
            if match:
                instagram_followers = match.group(1)
                if 'million' in pattern or 'm followers' in pattern:
                    instagram_followers += ' million'
                elif 'k followers' in pattern:
                    instagram_followers += 'k'
                break
    
    # Create artist-bio.txt file
    if bio_content:
        bio_file_path = os.path.join(output_folder, 'artist-bio.txt')
        with open(bio_file_path, 'w', encoding='utf-8') as f:
            f.write(bio_content)
        print(f"✅ Created artist-bio.txt for {artist_name}")
    else:
        print(f"❌ Could not find bio information for {artist_name}")
        return False
    
    # Create artistname.md file
    md_file_name = os.path.basename(output_folder) + '.md'
    md_file_path = os.path.join(output_folder, md_file_name)
    
    with open(md_file_path, 'w', encoding='utf-8') as f:
        f.write(f"# {artist_name}\n\n")
        
        f.write("## Artist Information\n")
        f.write(f"- **Name:** {artist_name}\n")
        if location:
            f.write(f"- **Location:** {location}\n")
        if style:
            f.write(f"- **Style:** {', '.join(style)}\n")
        if instagram_followers:
            f.write(f"- **Instagram:** {instagram_followers} followers\n")
        f.write(f"- **Website:** {artist_url}\n")
        if price_range:
            f.write(f"- **Price Range:** {price_range}\n")
        
        f.write("\n## Bio\n")
        f.write(f"{bio_content}\n\n")
        
        f.write("## Gallery\n")
        f.write("This folder contains images of the artist's work, downloaded from their portfolio on tattooswizard.com.\n\n")
        
        f.write("## Notes\n")
        if style:
            for s in style:
                f.write(f"- Specializes in {s.lower()} style\n")
        if instagram_followers:
            f.write(f"- Has a significant social media presence with {instagram_followers} followers\n")
        if location:
            f.write(f"- Based in {location}\n")
    
    print(f"✅ Created {md_file_name} for {artist_name}")
    return True

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python create_artist_bio.py <artist_url> <output_folder>")
        sys.exit(1)
        
    artist_url = sys.argv[1]
    output_folder = sys.argv[2]
    
    create_artist_bio(artist_url, output_folder)
