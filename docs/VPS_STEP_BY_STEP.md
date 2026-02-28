# VPS Setup — Step by Step

You're SSH'd in as `misha@76.13.46.174`. Run these commands in order.

---

## Step 1: Clone the repo

```bash
cd ~
git clone https://github.com/milnikov/open-tattoo-artists.git Tattoo_artists
cd Tattoo_artists
```

---

## Step 2: Run the setup script

```bash
chmod +x scripts/setup_vm.sh
./scripts/setup_vm.sh
```

This installs Python, Chrome, ChromeDriver dependencies, and creates a virtual environment. Takes about 5–10 minutes. If anything fails, paste the error and we can fix it.

---

## Step 3: Configure R2 credentials

Copy your local `config.yaml` to the VPS. **From your Mac** (new terminal, not SSH), run:

```bash
scp packages/scraper/config.yaml misha@76.13.46.174:~/Tattoo_artists/packages/scraper/config.yaml
```

Or create it manually on the VPS. On the VPS:

```bash
cp packages/scraper/config.example.yaml packages/scraper/config.yaml
nano packages/scraper/config.yaml
```

Add your R2 block (uncomment and fill):

```yaml
r2:
  account_id: "YOUR_ACCOUNT_ID"
  access_key_id: "YOUR_ACCESS_KEY"
  secret_access_key: "YOUR_SECRET_KEY"
  bucket: "open-tattoo-artists"
  public_url: "https://pub-4fe1c204aa1d4ce08395d234befdc73f.r2.dev"
```

Save: `Ctrl+O`, Enter, then `Ctrl+X`.

---

## Step 4: Configure Git (for push)

If the pipeline should commit and push to GitHub:

```bash
git config user.name "misha"
git config user.email "your@email.com"
```

For push to work, either:
- Add your SSH key to the VPS: `~/.ssh/id_rsa` (or generate: `ssh-keygen -t ed25519 -C "your@email.com"` and add the public key to GitHub), or
- Use a Personal Access Token (HTTPS) when git prompts for credentials.

---

## Step 5: Test the pipeline

```bash
source venv/bin/activate
python3 packages/scraper/src/pipeline_main.py --limit 2
```

If you see `✅ artist_name (N images)` for 2 artists, the setup works.

---

## Step 6: Run in background (recommended)

Use `screen` so the process keeps running if you disconnect:

```bash
sudo apt-get install -y screen
screen -S tattoo
source venv/bin/activate
cd ~/Tattoo_artists
python3 packages/scraper/src/pipeline_main.py --limit 500
```

When it starts processing:
- Detach: `Ctrl+A`, then `D`
- Reattach later: `screen -r tattoo`

---

## Quick reference

| Task              | Command                                                    |
|-------------------|------------------------------------------------------------|
| Check progress    | `cat packages/scraper/scrape_state.json`                  |
| Count artists     | `ls data/artists/*.json 2>/dev/null | wc -l`                 |
| Reattach screen   | `screen -r tattoo`                                         |
| Stop pipeline     | `pkill -f pipeline_main.py`                                |
| Resume pipeline   | `python3 packages/scraper/src/pipeline_main.py` (no args)  |
