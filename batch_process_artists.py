#!/usr/bin/env python3
"""
Batch processing script for downloading tattoo artist portfolios from discovered_pages.json
Designed to run headlessly on a VM without requiring browser interaction.

Usage:
    python batch_process_artists.py [--start-index N] [--limit M] [--skip-existing] [--headless]
"""

import json
import os
import sys
import time
import argparse
import traceback
import random
from datetime import datetime
from pathlib import Path
import subprocess

def load_artists(json_file='discovered_pages.json'):
    """Load artist URLs from JSON file"""
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('artists', [])
    except Exception as e:
        print(f"❌ Error loading {json_file}: {e}")
        sys.exit(1)

def get_artist_folder_name(url):
    """Extract artist folder name from URL"""
    artist_slug = url.split('/')[-1]
    # Convert slug to readable name (e.g., "megan_massacre" -> "Megan Massacre")
    artist_name = artist_slug.replace('_', ' ').title()
    return artist_name

def artist_already_processed(output_folder):
    """Check if artist folder exists and has images"""
    if not os.path.exists(output_folder):
        return False
    
    # Check if folder has at least one image file
    jpg_files = list(Path(output_folder).glob('*.jpg'))
    return len(jpg_files) > 0

def process_artist(artist_url, base_output_dir='.', headless=True, skip_existing=True):
    """Process a single artist"""
    artist_name = get_artist_folder_name(artist_url)
    output_folder = os.path.join(base_output_dir, artist_name)
    
    # Skip if already processed
    if skip_existing and artist_already_processed(output_folder):
        print(f"⏭️  Skipping {artist_name} (already processed)")
        return {'status': 'skipped', 'artist': artist_name, 'url': artist_url}
    
    print(f"\n{'='*80}")
    print(f"🎨 Processing: {artist_name}")
    print(f"📎 URL: {artist_url}")
    print(f"{'='*80}")
    
    start_time = time.time()
    
    try:
        # Build command for download_artist_with_bio.py
        cmd = [
            sys.executable,
            'download_artist_with_bio.py',
            artist_url,
            output_folder,
            '--no-debug'
        ]
        
        if headless:
            cmd.append('--headless')
        
        # Run the download script
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout per artist
        )
        
        elapsed = time.time() - start_time
        
        if result.returncode == 0:
            # Count downloaded images
            jpg_files = list(Path(output_folder).glob('*.jpg'))
            image_count = len(jpg_files)
            
            print(f"✅ Successfully processed {artist_name}")
            print(f"   Images downloaded: {image_count}")
            print(f"   Time taken: {elapsed:.1f}s")
            
            return {
                'status': 'success',
                'artist': artist_name,
                'url': artist_url,
                'images': image_count,
                'time': elapsed
            }
        else:
            print(f"❌ Failed to process {artist_name}")
            print(f"   Error output: {result.stderr[:500]}")
            
            return {
                'status': 'failed',
                'artist': artist_name,
                'url': artist_url,
                'error': result.stderr[:500],
                'time': elapsed
            }
            
    except subprocess.TimeoutExpired:
        elapsed = time.time() - start_time
        print(f"⏱️  Timeout processing {artist_name} (exceeded 5 minutes)")
        return {
            'status': 'timeout',
            'artist': artist_name,
            'url': artist_url,
            'time': elapsed
        }
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"❌ Exception processing {artist_name}: {e}")
        traceback.print_exc()
        return {
            'status': 'error',
            'artist': artist_name,
            'url': artist_url,
            'error': str(e),
            'time': elapsed
        }

def save_progress(results, progress_file='batch_progress.json'):
    """Save progress to JSON file"""
    with open(progress_file, 'w', encoding='utf-8') as f:
        json.dump({
            'last_updated': datetime.now().isoformat(),
            'total_processed': len(results),
            'results': results
        }, f, indent=2)

def load_progress(progress_file='batch_progress.json'):
    """Load previous progress"""
    if os.path.exists(progress_file):
        try:
            with open(progress_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('results', [])
        except:
            return []
    return []

def main():
    parser = argparse.ArgumentParser(
        description='Batch process tattoo artists from discovered_pages.json',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process all artists (headless mode)
  python batch_process_artists.py
  
  # Process first 100 artists
  python batch_process_artists.py --limit 100
  
  # Resume from artist 500
  python batch_process_artists.py --start-index 500
  
  # Skip already processed artists
  python batch_process_artists.py --skip-existing
  
  # Process with visible browser (for debugging)
  python batch_process_artists.py --no-headless --limit 10
        """
    )
    
    parser.add_argument(
        '--start-index',
        type=int,
        default=0,
        help='Start processing from this index (default: 0)'
    )
    
    parser.add_argument(
        '--limit',
        type=int,
        default=None,
        help='Limit number of artists to process (default: all)'
    )
    
    parser.add_argument(
        '--skip-existing',
        action='store_true',
        default=True,
        help='Skip artists that already have images downloaded (default: True)'
    )
    
    parser.add_argument(
        '--no-skip-existing',
        action='store_false',
        dest='skip_existing',
        help='Process all artists even if already downloaded'
    )
    
    parser.add_argument(
        '--headless',
        action='store_true',
        default=True,
        help='Run in headless mode (default: True)'
    )
    
    parser.add_argument(
        '--no-headless',
        action='store_false',
        dest='headless',
        help='Show browser window (for debugging)'
    )
    
    parser.add_argument(
        '--output-dir',
        type=str,
        default='.',
        help='Base directory for artist folders (default: current directory)'
    )
    
    parser.add_argument(
        '--progress-file',
        type=str,
        default='batch_progress.json',
        help='File to save progress (default: batch_progress.json)'
    )
    
    parser.add_argument(
        '--json-file',
        type=str,
        default='discovered_pages.json',
        help='JSON file with artist URLs (default: discovered_pages.json)'
    )
    
    args = parser.parse_args()
    
    # Load artists
    print(f"📂 Loading artists from {args.json_file}...")
    all_artists = load_artists(args.json_file)
    total_artists = len(all_artists)
    
    # Determine which artists to process
    start_idx = args.start_index
    end_idx = start_idx + args.limit if args.limit else total_artists
    artists_to_process = all_artists[start_idx:end_idx]
    
    print(f"\n📊 Processing Statistics:")
    print(f"   Total artists in file: {total_artists:,}")
    print(f"   Artists to process: {len(artists_to_process):,}")
    print(f"   Starting from index: {start_idx}")
    print(f"   Headless mode: {args.headless}")
    print(f"   Skip existing: {args.skip_existing}")
    print(f"   Output directory: {args.output_dir}")
    
    # Load previous progress
    previous_results = load_progress(args.progress_file)
    processed_urls = {r.get('url') for r in previous_results if r.get('status') == 'success'}
    
    if processed_urls:
        print(f"   Already processed: {len(processed_urls)}")
    
    # Confirm before starting
    if len(artists_to_process) > 10:
        print(f"\n⚠️  About to process {len(artists_to_process)} artists.")
        print("   Press Ctrl+C to cancel, or wait 5 seconds to continue...")
        try:
            time.sleep(5)
        except KeyboardInterrupt:
            print("\n❌ Cancelled by user")
            sys.exit(0)
    
    # Process artists
    results = previous_results.copy()
    start_time = time.time()
    
    for idx, artist_url in enumerate(artists_to_process, start=start_idx):
        # Skip if already successfully processed
        if artist_url in processed_urls and args.skip_existing:
            continue
        
        print(f"\n[{idx + 1}/{total_artists}] Processing artist {idx + 1}...")
        
        result = process_artist(
            artist_url,
            base_output_dir=args.output_dir,
            headless=args.headless,
            skip_existing=args.skip_existing
        )
        
        results.append(result)
        
        # Save progress every 10 artists
        if (idx + 1) % 10 == 0:
            save_progress(results, args.progress_file)
            elapsed = time.time() - start_time
            avg_time = elapsed / (idx + 1 - start_idx)
            remaining = (len(artists_to_process) - (idx + 1 - start_idx)) * avg_time
            print(f"\n💾 Progress saved. Estimated time remaining: {remaining/60:.1f} minutes")
        
        # Random delay between artists to avoid throttling (3-8 seconds)
        delay = random.uniform(3, 8)
        print(f"⏸ Waiting {delay:.1f}s before next artist to avoid rate limiting...")
        time.sleep(delay)
        
        # Longer delay after every 10 artists
        if (idx + 1) % 10 == 0:
            extra_delay = random.uniform(10, 20)
            print(f"⏸ Extended pause {extra_delay:.1f}s after {idx + 1} artists...")
            time.sleep(extra_delay)
    
    # Final save
    save_progress(results, args.progress_file)
    
    # Print summary
    total_time = time.time() - start_time
    successful = sum(1 for r in results if r.get('status') == 'success')
    failed = sum(1 for r in results if r.get('status') in ['failed', 'error', 'timeout'])
    skipped = sum(1 for r in results if r.get('status') == 'skipped')
    
    print(f"\n{'='*80}")
    print(f"📊 Batch Processing Complete!")
    print(f"{'='*80}")
    print(f"   Total processed: {len(results)}")
    print(f"   Successful: {successful}")
    print(f"   Failed: {failed}")
    print(f"   Skipped: {skipped}")
    print(f"   Total time: {total_time/3600:.2f} hours")
    print(f"   Average time per artist: {total_time/len(results):.1f}s")
    print(f"   Progress saved to: {args.progress_file}")
    print(f"{'='*80}")

if __name__ == '__main__':
    main()

