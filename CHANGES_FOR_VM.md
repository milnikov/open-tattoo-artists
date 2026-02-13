# Changes Made for VM/Headless Processing

## Problem

The original scripts (`download_artist.py` and `download_artist_with_bio.py`) only worked when pages were opened in a visible browser. This was because:

1. **Basic headless configuration**: The Chrome headless mode wasn't properly configured
2. **Missing dependencies**: ChromeDriver management wasn't automated
3. **No batch processing**: No way to process multiple artists automatically
4. **JavaScript rendering issues**: Headless mode wasn't properly handling JavaScript-heavy sites

## Solution

### 1. Enhanced Headless Mode (`download_artist.py`)

**Changes made:**
- Added `--headless=new` (new headless mode is more stable)
- Added proper user agent string to avoid bot detection
- Added Chrome options for better JavaScript rendering:
  - `--disable-blink-features=AutomationControlled`
  - `--disable-background-timer-throttling`
  - `--disable-renderer-backgrounding`
  - And more performance optimizations
- Added automatic ChromeDriver management via `webdriver-manager`
- Enhanced wait strategies and JavaScript execution

**Key code changes:**
```python
# Before
chrome_options.add_argument('--headless')

# After
chrome_options.add_argument('--headless=new')
chrome_options.add_argument('--disable-blink-features=AutomationControlled')
chrome_options.add_argument('--user-agent=Mozilla/5.0...')
# ... more optimizations
```

### 2. Batch Processing Script (`batch_process_artists.py`)

**New features:**
- Reads artist URLs from `discovered_pages.json`
- Processes artists one by one automatically
- Progress tracking with JSON file
- Resume capability (can stop and continue)
- Skip already processed artists
- Error handling and timeout management
- Statistics and reporting

**Usage:**
```bash
python batch_process_artists.py --limit 100  # Process 100 artists
python batch_process_artists.py --start-index 500  # Resume from 500
```

### 3. VM Setup Script (`setup_vm.sh`)

**What it does:**
- Installs Python 3 and pip
- Installs Google Chrome
- Installs ChromeDriver dependencies
- Installs Python packages including `webdriver-manager`
- Sets up virtual environment (optional)
- Verifies installation

**Usage:**
```bash
chmod +x setup_vm.sh
./setup_vm.sh
```

### 4. Updated Dependencies (`requirements.txt`)

**Added:**
- `webdriver-manager>=4.0.0` - Automatically manages ChromeDriver

## Why It Works Now

### Headless Mode Improvements

1. **New Headless Mode**: Chrome's `--headless=new` is more stable and handles JavaScript better
2. **Proper User Agent**: Avoids detection as a bot
3. **JavaScript Execution**: Better handling of lazy-loaded content
4. **Wait Strategies**: Proper waits for content to load

### Automatic Driver Management

- `webdriver-manager` automatically downloads and manages ChromeDriver
- No manual ChromeDriver installation needed
- Works across different Chrome versions

### Batch Processing

- Processes artists sequentially
- Saves progress every 10 artists
- Can resume from any point
- Handles errors gracefully

## Testing

Before running on all 18,932 artists, test with a small batch:

```bash
# Test with 5 artists (visible browser for debugging)
python3 batch_process_artists.py --limit 5 --no-headless

# Test headless mode
python3 batch_process_artists.py --limit 5 --headless
```

## Performance

- **Per artist**: ~10-30 seconds
- **18,932 artists**: ~50-150 hours (2-6 days)
- **Memory usage**: ~2-4 GB RAM
- **Disk space**: ~50-100 GB for all images

## Files Created/Modified

### New Files:
- `batch_process_artists.py` - Batch processing script
- `setup_vm.sh` - VM setup script
- `VM_SETUP_GUIDE.md` - Complete VM setup guide
- `QUICK_START_VM.md` - Quick reference
- `CHANGES_FOR_VM.md` - This file

### Modified Files:
- `download_artist.py` - Enhanced headless mode
- `requirements.txt` - Added webdriver-manager
- `README.md` - Added batch processing section

## Next Steps

1. **Set up VM**: Follow `VM_SETUP_GUIDE.md`
2. **Test**: Run with `--limit 10` first
3. **Start processing**: Run `batch_process_artists.py`
4. **Monitor**: Check `batch_progress.json` regularly
5. **Resume if needed**: Use `--start-index` to continue

## Troubleshooting

If headless mode still doesn't work:

1. **Check Chrome version**: `google-chrome --version`
2. **Check ChromeDriver**: `chromedriver --version`
3. **Try visible mode**: Use `--no-headless` to debug
4. **Check logs**: Review `batch_progress.json` for errors
5. **Increase wait times**: Modify scroll delays in `download_artist.py`

## Notes

- Headless mode may collect slightly fewer images than visible mode, but should work for most cases
- If you encounter issues with specific artists, you can process them individually with visible mode
- Progress is saved automatically, so you can stop and resume anytime

