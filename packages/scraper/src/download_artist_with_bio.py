#!/usr/bin/env python3
"""
Combined script to download artist portfolio and create both artist-bio.txt and artistname.md files
"""

import sys
import os
import subprocess

def download_artist_with_bio(artist_url, output_folder, no_debug=True, headless=False):
    """
    Download artist portfolio and create both artist-bio.txt and artistname.md files
    
    Args:
        artist_url (str): URL of the artist's page
        output_folder (str): Folder to save images and bio files
        no_debug (bool): Whether to disable debug files (default: True to avoid creating debug files)
        headless (bool): Whether to hide the browser (default: False to always show browser)
    """
    # Make sure the output folder exists
    os.makedirs(output_folder, exist_ok=True)
    
    # Step 1: Download artist portfolio
    print(f"Step 1: Downloading portfolio for {artist_url}")
    download_cmd = ["python3", "download_artist.py", artist_url, output_folder]
    
    # Always show browser unless headless is specified
    if not headless:
        download_cmd.append("--visible")
        print("⚠️ Browser will be visible (recommended for maximum image collection)")
    
    # Don't create debug files if no_debug is specified
    if no_debug:
        download_cmd.append("--no-debug")
        print("ℹ️ Debug files will not be created")
    
    try:
        subprocess.run(download_cmd, check=True)
        print("✅ Portfolio download completed")
    except subprocess.CalledProcessError as e:
        print(f"❌ Error downloading portfolio: {e}")
        return False
    
    # Step 2: Create artist-bio.txt and artistname.md files
    print(f"\nStep 2: Creating artist-bio.txt and artistname.md files")
    bio_cmd = ["python3", "create_artist_bio.py", artist_url, output_folder]
    
    try:
        subprocess.run(bio_cmd, check=True)
        print("✅ Artist files creation completed")
    except subprocess.CalledProcessError as e:
        print(f"❌ Error creating artist files: {e}")
        return False
    
    print(f"\n🎉 All tasks completed successfully for {artist_url}")
    return True

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python download_artist_with_bio.py <artist_url> <output_folder> [OPTIONS]")
        print("Options:")
        print("  --no-debug    : Don't create debug files (default)")
        print("  --debug      : Create debug files (debug_page.html, debug_screenshot.png, etc.)")
        print("  --headless   : Hide the browser")
        print("NOTE: Browser is visible by default (recommended for maximum image collection)")
        sys.exit(1)
    
    artist_url = sys.argv[1]
    output_folder = sys.argv[2]
    
    # Parse options
    no_debug = "--debug" not in sys.argv  # Default is to NOT create debug files
    headless = "--headless" in sys.argv  # Default is to show browser
    
    download_artist_with_bio(artist_url, output_folder, no_debug, headless)
