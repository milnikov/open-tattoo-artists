# VM Setup Guide for Batch Processing Tattoo Artists

This guide explains how to set up a **Hostinger VPS** (or any Ubuntu VPS) to run the batch processing script headlessly. Run all commands from the **repo root**.

## Why Headless Mode?

The scripts use Selenium with Chrome to scrape JavaScript-rendered content. Previously, they required a visible browser, but we've enhanced them to work in headless mode for VM deployment. The key improvements include:

1. **Enhanced Chrome options** for better headless performance
2. **Automatic ChromeDriver management** via webdriver-manager
3. **Better wait strategies** and JavaScript execution
4. **Proper user agent** to avoid bot detection

## Prerequisites

- Hostinger VPS (or any Ubuntu 22.04+ VPS)
- SSH access to your VPS
- Git

## Step 1: Hostinger VPS Setup

1. Log into [Hostinger](https://www.hostinger.com/) and open your VPS panel
2. Ensure you have Ubuntu 22.04 LTS (or newer)
3. Recommended: At least 4 GB RAM, 100 GB disk (for many images)
4. Note your VPS IP address and SSH credentials

## Step 2: Clone the Repo

From your VPS, clone the repository (recommended over manual file upload):

```bash
# SSH into your Hostinger VPS
ssh root@YOUR_VPS_IP
# or: ssh u123456789@YOUR_VPS_IP

# Clone the repo
git clone https://github.com/milnikov/open-tattoo-artists.git Tattoo_artists
cd Tattoo_artists
```

## Step 3: Run Setup Script

**Important**: Run from **repo root**. The setup script expects `requirements.txt` in the current directory.

```bash
# Make script executable (if not already)
chmod +x scripts/setup_vm.sh

# Run setup script from repo root
./scripts/setup_vm.sh
```

This script will:
- Install Python 3 and pip
- Install Google Chrome
- Install ChromeDriver dependencies
- Install Python packages (including boto3, Pillow, PyYAML)
- Set up virtual environment

**Expected time**: 5-10 minutes

## Step 3b: Configure R2 Pipeline (Optional)

For the **R2 + Git pipeline** (outputs to `data/artists/*.json` and Cloudflare R2 instead of local JPG folders):

1. Copy the config and add your Cloudflare R2 credentials:
   ```bash
   cp packages/scraper/config.example.yaml packages/scraper/config.yaml
   # Edit config.yaml with: account_id, access_key_id, secret_access_key, bucket, public_url
   ```

2. Configure Git for commits (if the pipeline should push):
   ```bash
   git config user.name "your-name"
   git config user.email "your@email.com"
   # Ensure SSH key or token is set up for push
   ```

## Step 4: Test the Setup

### Option A: Legacy batch (local JPG folders)

```bash
source venv/bin/activate

# Test with 5 artists
python3 packages/scraper/src/batch_process_artists.py --limit 5 --headless
```

### Option B: R2 + Git pipeline (recommended)

```bash
source venv/bin/activate

# Dry run (no R2, no git) — tests parsing only
python3 packages/scraper/src/pipeline_main.py --limit 2 --no-r2

# Full run with R2 (requires config.yaml)
python3 packages/scraper/src/pipeline_main.py --limit 5
```

## Step 5: Start Batch Processing

### R2 + Git Pipeline (Recommended)

Outputs to `data/artists/*.json` and Cloudflare R2. Resumable via `scrape_state.json`.

```bash
# Process all artists (requires config.yaml with R2)
python3 packages/scraper/src/pipeline_main.py

# Process first 100 artists
python3 packages/scraper/src/pipeline_main.py --limit 100

# Resume from index 500
python3 packages/scraper/src/pipeline_main.py --start-index 500

# Commit and push every 100 artists (default)
python3 packages/scraper/src/pipeline_main.py --batch-size 100

# Skip git commit/push
python3 packages/scraper/src/pipeline_main.py --no-git
```

### Legacy Batch (Local JPG Folders)

Saves images to local folders. Use if you prefer not to use R2 yet.

```bash
# Process all artists
python3 packages/scraper/src/batch_process_artists.py

# Process first 100 artists
python3 packages/scraper/src/batch_process_artists.py --limit 100

# Resume from index 500
python3 packages/scraper/src/batch_process_artists.py --start-index 500
```

## Step 6: Monitor Progress

### Check Progress File

Progress is saved at repo root as `batch_progress.json`:

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

# Count downloaded images (run from repo root)
find . -name "*.jpg" | wc -l
```

## Step 7: Run in Background (Recommended)

For long-running processes, use `screen` or `tmux`:

### Using screen

```bash
# Install screen
sudo apt-get install screen

# Start a screen session
screen -S tattoo_processing

# Activate venv and run (from repo root)
source venv/bin/activate
# R2 + Git pipeline:
python3 packages/scraper/src/pipeline_main.py
# Or legacy batch:
# python3 packages/scraper/src/batch_process_artists.py

# Detach: Press Ctrl+A, then D
# Reattach: screen -r tattoo_processing
```

### Using tmux

```bash
# Install tmux
sudo apt-get install tmux

# Start a tmux session
tmux new -s tattoo_processing

# Activate venv and run (from repo root)
source venv/bin/activate
python3 packages/scraper/src/pipeline_main.py

# Detach: Press Ctrl+B, then D
# Reattach: tmux attach -t tattoo_processing
```

### Using nohup

```bash
# Run in background with output logging (from repo root)
source venv/bin/activate
nohup python3 packages/scraper/src/pipeline_main.py > pipeline_output.log 2>&1 &

# Check if running
ps aux | grep pipeline_main

# View output
tail -f pipeline_output.log
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

1. Upgrade your Hostinger VPS plan (more RAM)
2. Process in smaller batches:
   ```bash
   python3 packages/scraper/src/pipeline_main.py --limit 1000
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
# Reinstall packages (from repo root)
pip install --upgrade -r requirements.txt

# Or recreate virtual environment
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Performance Tips

1. **Use appropriate VPS size**: More RAM = better performance (4+ GB recommended)
2. **Process in batches**: Use `--limit` to process manageable chunks
3. **Monitor resources**: Use `htop` to monitor CPU/memory usage
4. **Save progress frequently**: The script saves every 10 artists
5. **Resume capability**: Use `--start-index` to resume from where you left off

## Estimated Processing Time

- **Per artist**: ~10-30 seconds (depending on number of images)
- **~19,000 artists**: ~50-150 hours (2-6 days)
- **With 4 vCPU VPS**: Can process ~100-200 artists/hour

## Cost Estimation (Hostinger VPS)

- **Hostinger VPS**: Plans typically $5–20/month depending on resources
- **Storage**: Budget 50-100 GB for all images (included in most plans)
- **Total**: Fixed monthly cost; no per-hour charges like cloud providers

## Backup Strategy

1. **Regular progress saves**: `batch_progress.json` is saved every 10 artists at repo root
2. **Downloaded images**: Use `rsync` or `scp` to sync to your local machine periodically
3. **Progress file**: Backup `batch_progress.json` regularly

```bash
# Example: Backup from local machine
rsync -avz user@YOUR_VPS_IP:~/Tattoo_artists/batch_progress.json ./
rsync -avz user@YOUR_VPS_IP:~/Tattoo_artists/Artist\ Name/ ./backups/
```

## Stopping and Resuming

The pipeline saves progress automatically. To stop:

1. Press `Ctrl+C` (if running in foreground)
2. Or kill the process: `pkill -f pipeline_main.py`

To resume the R2 pipeline:

```bash
# Check state (from repo root)
cat packages/scraper/scrape_state.json

# Resume (pipeline uses last_index automatically)
python3 packages/scraper/src/pipeline_main.py
```

For the legacy batch, resume with:
```bash
python3 packages/scraper/src/batch_process_artists.py --start-index LAST_INDEX
```

## Support

If you encounter issues:

1. Check `batch_progress.json` for error details
2. Review debug files in artist folders (if `--no-debug` was not used)
3. Check VPS logs if running as a service

## Next Steps

After processing completes:

1. Verify: count `data/artists/*.json` or check `packages/scraper/scrape_state.json`
2. Download results to local machine via rsync/scp
3. Review failed artists and retry if needed
4. Keep VPS for future processing or scale down
