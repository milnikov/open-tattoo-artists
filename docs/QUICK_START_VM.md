# Quick Start Guide for VM Processing (Hostinger VPS)

Run all commands from **repo root**. We use Hostinger VPS, not Google Cloud.

## TL;DR - Get Started in 5 Minutes

```bash
# 1. SSH into your Hostinger VPS
ssh root@YOUR_VPS_IP

# 2. Clone repo and cd into it
git clone YOUR_REPO_URL Tattoo_artists
cd Tattoo_artists

# 3. Run setup (from repo root)
chmod +x scripts/setup_vm.sh && ./scripts/setup_vm.sh

# 4. Test with 5 artists
source venv/bin/activate
python3 packages/scraper/src/batch_process_artists.py --limit 5

# 5. Start full processing in background
screen -S processing
source venv/bin/activate
python3 packages/scraper/src/batch_process_artists.py
# Press Ctrl+A then D to detach
```

## Common Commands

```bash
# Process all artists (run from repo root)
python3 packages/scraper/src/batch_process_artists.py

# Process with limit
python3 packages/scraper/src/batch_process_artists.py --limit 1000

# Resume from index
python3 packages/scraper/src/batch_process_artists.py --start-index 500

# Check progress (batch_progress.json is at repo root)
tail -f batch_progress.json

# Count successful downloads
grep -c '"status": "success"' batch_progress.json

# Reattach to screen session
screen -r processing
```

## Why It Works Now

The scripts were enhanced with:
- ✅ Better headless Chrome configuration
- ✅ Automatic ChromeDriver management
- ✅ Proper wait strategies for JavaScript content
- ✅ Progress tracking and resume capability

See `docs/VM_SETUP_GUIDE.md` for detailed instructions.
