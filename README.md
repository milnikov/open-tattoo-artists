# Tattoo Artist Portfolio Downloader

## Approach Documentation

This documents the proven approach for downloading tattoo artist portfolios from tattooswizard.com:

### Key Features
- **Handles JavaScript-rendered content** using Selenium
- **Aggressive scrolling** to trigger lazy-loaded images
- **Multiple extraction methods** to capture all possible image URLs
- **Smart filtering** to exclude UI elements and logos
- **Automatic organization** into numbered JPG files

### How It Works
1. **Initialize browser**: Launches Chrome in headless mode
2. **Navigate to artist URL**: Loads the artist's profile page
3. **Click 'Tattoos' tab**: Activates the portfolio section
4. **Scroll multiple times**: Triggers lazy loading of all images
5. **Extract image URLs** using:
   - `<img>` tag sources
   - JavaScript image collectors
   - Background images
   - Regex pattern matching
6. **Filter URLs**: Keeps only tattoo images, excludes UI elements
7. **Download images**: Saves as sequentially numbered JPG files

### Requirements
- Python 3
- Selenium, requests, beautifulsoup4, lxml, webdriver-manager
- ChromeDriver (automatically managed by webdriver-manager)

### Setup (Local Development)
```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate  # On macOS/Linux
# OR
venv\Scripts\activate  # On Windows

# Install dependencies
pip install -r requirements.txt
```

**Note**: Always activate the virtual environment before running scripts. All scraper scripts live under `packages/scraper/` and must be run **from repo root**:

```bash
./run.sh python packages/scraper/src/download_artist.py "URL" "folder"
```

## Usage

Scraper scripts are in **`packages/scraper/src/`**. Run them from the **repo root**. The main artist list the batch processor uses is `packages/scraper/discovered_pages.json`; other paths (`TATTOODO/`, `artists_examples/`, etc.) are relative to repo root. See `packages/scraper/README.md` for details.

### Batch processing (from repo root)

```bash
# Process all artists headlessly
python packages/scraper/src/batch_process_artists.py

# Process first 100 artists (for testing)
python packages/scraper/src/batch_process_artists.py --limit 100

# Resume from a specific index
python packages/scraper/src/batch_process_artists.py --start-index 500
```

See `docs/VM_SETUP_GUIDE.md` for complete Hostinger VPS setup instructions.

### Combined workflow (download + bio)

```bash
python packages/scraper/src/download_artist_with_bio.py "https://tattooswizard.com/artists/artistname" "output_folder"
```

**IMPORTANT: The browser will be visible by default!** This ensures maximum image collection.

Options: `--debug`, `--headless`.

### Single-script usage (from repo root)

- **Download portfolio only:**  
  `python packages/scraper/src/download_artist.py "URL" "output_folder"`  
  Options: `--visible`, `--interactive`, `--no-debug`
- **Create bio files only:**  
  `python packages/scraper/src/create_artist_bio.py "URL" "output_folder"`
- **Discovery (Tattoodo):**  
  `python packages/scraper/src/discover_tattoodo.py`  
  (writes to `TATTOODO/discovered_pages.json` and `.txt`)

### URL Variations
Some artists may have multiple URL formats. If you're not getting enough images, try these variations:

1. With underscore: `https://tattooswizard.com/artists/artist_name`
2. Without underscore: `https://tattooswizard.com/artists/artistname`

Examples:
- Megan Massacre: Try both `megan_massacre` and `meganmassacre`
- Doctor Woo: Try both `_dr_woo_` and `drwoo`

## Troubleshooting
### Incomplete Downloads
If you're not getting all images:
1. Increase scroll iterations in the script (line 40)
2. Add more regex patterns (line 100)
3. Check for alternative artist URLs
4. Run script multiple times with different URLs

### Common Errors
- **ChromeDriver issues**: Run `brew install --cask chromedriver`
- **ModuleNotFound**: Run `pip3 install -r requirements.txt`
- **Empty results**: Check website structure changes

- If downloads fail, check ChromeDriver installation
- For empty results, increase scroll iterations in script
- For partial downloads, check network connectivity

### Escalation Procedure
1. After 3 failed download attempts:
   - Save debug_page.html
   - Capture browser screenshot
   - Contact support@tattooswizard.com
2. Include in email:
   - Artist URL
   - debug_page.html
   - Screenshot
   - Script version

### Support Contact
- Email: support@tattooswizard.com
- Include:
  1. Artist URL
  2. Script version
  3. debug_page.html
  4. debug_screenshot.png
  5. debug_urls.txt (if available)

### Case Study: Megan Massacre
- With the enhanced script, we successfully downloaded 3 images from Megan Massacre's portfolio
- The improved approach includes:
  1. More aggressive scrolling (double pass with longer pauses)
  2. Better extraction methods
  3. Improved debugging output
- Solution: Use the enhanced script with visible browser mode for artists with fewer images
