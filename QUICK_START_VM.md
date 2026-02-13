# Quick Start Guide for VM Processing

## TL;DR - Get Started in 5 Minutes

```bash
# 1. SSH into your VM
gcloud compute ssh YOUR_VM_NAME

# 2. Upload files (from local machine)
gcloud compute scp discovered_pages.json *.py requirements.txt setup_vm.sh YOUR_VM_NAME:~/

# 3. Run setup (on VM)
chmod +x setup_vm.sh && ./setup_vm.sh

# 4. Test with 5 artists
python3 batch_process_artists.py --limit 5

# 5. Start full processing in background
screen -S processing
python3 batch_process_artists.py
# Press Ctrl+A then D to detach
```

## Common Commands

```bash
# Process all artists
python3 batch_process_artists.py

# Process with limit
python3 batch_process_artists.py --limit 1000

# Resume from index
python3 batch_process_artists.py --start-index 500

# Check progress
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

See `VM_SETUP_GUIDE.md` for detailed instructions.

