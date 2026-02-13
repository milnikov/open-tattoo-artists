# VM Setup Guide for Batch Processing Tattoo Artists

This guide explains how to set up a Google Cloud VM to run the batch processing script headlessly.

## Why Headless Mode?

The scripts use Selenium with Chrome to scrape JavaScript-rendered content. Previously, they required a visible browser, but we've enhanced them to work in headless mode for VM deployment. The key improvements include:

1. **Enhanced Chrome options** for better headless performance
2. **Automatic ChromeDriver management** via webdriver-manager
3. **Better wait strategies** and JavaScript execution
4. **Proper user agent** to avoid bot detection

## Prerequisites

- Google Cloud Platform account
- Basic knowledge of GCP VM creation
- SSH access to your VM

## Step 1: Create a Google Cloud VM

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Navigate to Compute Engine > VM instances
3. Click "Create Instance"
4. Recommended settings:
   - **Machine type**: `e2-standard-4` (4 vCPUs, 16 GB RAM) or higher
   - **Boot disk**: Ubuntu 22.04 LTS (or newer)
   - **Disk size**: At least 100 GB (you'll be downloading many images)
   - **Firewall**: Allow HTTP/HTTPS traffic
5. Click "Create"

## Step 2: Upload Files to VM

You have several options:

### Option A: Using gcloud CLI (Recommended)

```bash
# From your local machine
gcloud compute scp discovered_pages.json VM_NAME:~/
gcloud compute scp *.py VM_NAME:~/
gcloud compute scp requirements.txt VM_NAME:~/
gcloud compute scp setup_vm.sh VM_NAME:~/
```

### Option B: Using Git

```bash
# On VM
git clone YOUR_REPO_URL
cd Tattoo_artists
```

### Option C: Using Google Cloud Storage

```bash
# Upload files to GCS bucket
gsutil cp discovered_pages.json gs://YOUR_BUCKET/
gsutil cp *.py gs://YOUR_BUCKET/
gsutil cp requirements.txt gs://YOUR_BUCKET/

# On VM, download from bucket
gsutil cp gs://YOUR_BUCKET/* ./
```

## Step 3: SSH into VM

```bash
gcloud compute ssh VM_NAME
```

## Step 4: Run Setup Script

```bash
# Make script executable (if not already)
chmod +x setup_vm.sh

# Run setup script
./setup_vm.sh
```

This script will:
- Install Python 3 and pip
- Install Google Chrome
- Install ChromeDriver dependencies
- Install Python packages
- Set up virtual environment (optional)

**Expected time**: 5-10 minutes

## Step 5: Test the Setup

Before processing all 18,932 artists, test with a small batch:

```bash
# Activate virtual environment (if created)
source venv/bin/activate

# Test with 5 artists
python3 batch_process_artists.py --limit 5 --no-headless

# If that works, try headless mode
python3 batch_process_artists.py --limit 5 --headless
```

## Step 6: Start Batch Processing

### Basic Usage

```bash
# Process all artists (headless mode)
python3 batch_process_artists.py

# Process first 100 artists
python3 batch_process_artists.py --limit 100

# Resume from artist 500
python3 batch_process_artists.py --start-index 500
```

### Advanced Options

```bash
# Skip already processed artists (default)
python3 batch_process_artists.py --skip-existing

# Process all artists even if already downloaded
python3 batch_process_artists.py --no-skip-existing

# Custom output directory
python3 batch_process_artists.py --output-dir /path/to/output

# Custom progress file
python3 batch_process_artists.py --progress-file my_progress.json
```

## Step 7: Monitor Progress

### Check Progress File

```bash
# View progress
cat batch_progress.json | python3 -m json.tool | tail -50

# Count successful downloads
grep -c '"status": "success"' batch_progress.json

# Count failed downloads
grep -c '"status": "failed"' batch_progress.json
```

### Monitor in Real-Time

```bash
# Watch progress file
watch -n 30 'tail -20 batch_progress.json'

# Or use tail
tail -f batch_progress.json
```

### Check Disk Space

```bash
# Monitor disk usage
df -h

# Count downloaded images
find . -name "*.jpg" | wc -l
```

## Step 8: Run in Background (Recommended)

For long-running processes, use `screen` or `tmux`:

### Using screen

```bash
# Install screen
sudo apt-get install screen

# Start a screen session
screen -S tattoo_processing

# Run your script
python3 batch_process_artists.py

# Detach: Press Ctrl+A, then D
# Reattach: screen -r tattoo_processing
```

### Using tmux

```bash
# Install tmux
sudo apt-get install tmux

# Start a tmux session
tmux new -s tattoo_processing

# Run your script
python3 batch_process_artists.py

# Detach: Press Ctrl+B, then D
# Reattach: tmux attach -t tattoo_processing
```

### Using nohup

```bash
# Run in background with output logging
nohup python3 batch_process_artists.py > batch_output.log 2>&1 &

# Check if running
ps aux | grep batch_process

# View output
tail -f batch_output.log
```

## Troubleshooting

### Chrome/ChromeDriver Issues

```bash
# Check Chrome version
google-chrome --version

# Check ChromeDriver
chromedriver --version

# If ChromeDriver is missing, webdriver-manager will install it automatically
# Or install manually:
sudo apt-get install chromium-chromedriver
```

### Out of Memory

If you encounter memory issues:

1. Increase VM memory (e.g., `e2-standard-8` with 32 GB RAM)
2. Process in smaller batches:
   ```bash
   python3 batch_process_artists.py --limit 1000
   ```

### Network Issues

```bash
# Test connectivity
curl -I https://tattooswizard.com

# Check DNS
nslookup tattooswizard.com
```

### Python Package Issues

```bash
# Reinstall packages
pip install --upgrade -r requirements.txt

# Or recreate virtual environment
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Performance Tips

1. **Use appropriate VM size**: More RAM = better performance
2. **Process in batches**: Use `--limit` to process manageable chunks
3. **Monitor resources**: Use `htop` to monitor CPU/memory usage
4. **Save progress frequently**: The script saves every 10 artists
5. **Resume capability**: Use `--start-index` to resume from where you left off

## Estimated Processing Time

- **Per artist**: ~10-30 seconds (depending on number of images)
- **18,932 artists**: ~50-150 hours (2-6 days)
- **With 4 vCPU VM**: Can process ~100-200 artists/hour

## Cost Estimation

- **VM cost**: ~$0.15-0.30/hour for e2-standard-4
- **Total for 18,932 artists**: ~$15-50 (depending on processing time)
- **Storage**: ~$0.02-0.05/GB/month (estimate 50-100 GB for all images)

## Backup Strategy

1. **Regular progress saves**: `batch_progress.json` is saved every 10 artists
2. **Downloaded images**: Consider syncing to Google Cloud Storage periodically
3. **Progress file**: Backup `batch_progress.json` regularly

```bash
# Backup progress to GCS
gsutil cp batch_progress.json gs://YOUR_BUCKET/backups/

# Backup images (example for one artist folder)
gsutil -m cp -r "Artist Name" gs://YOUR_BUCKET/artists/
```

## Stopping and Resuming

The script saves progress automatically. To stop:

1. Press `Ctrl+C` (if running in foreground)
2. Or kill the process: `pkill -f batch_process_artists.py`

To resume:

```bash
# Check last processed index
python3 -c "import json; data=json.load(open('batch_progress.json')); print(f'Processed: {len(data[\"results\"])}')"

# Resume from that index
python3 batch_process_artists.py --start-index LAST_INDEX
```

## Support

If you encounter issues:

1. Check `batch_progress.json` for error details
2. Review debug files in artist folders (if `--no-debug` was not used)
3. Check VM logs: `journalctl -u YOUR_SERVICE` (if running as service)

## Next Steps

After processing completes:

1. Verify all artists were processed: `grep -c '"status": "success"' batch_progress.json`
2. Download results to local machine
3. Review failed artists and retry if needed
4. Clean up VM or keep it for future processing

