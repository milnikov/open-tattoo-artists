# GitHub integration (Suggest artist)

The "Suggest an artist" feature creates a GitHub issue and records the submission in your Contributions. It requires a **GitHub Personal Access Token** with permission to create issues in the repo.

## Setup

1. **Create a token**
   - GitHub → Settings → Developer settings → [Personal access tokens](https://github.com/settings/tokens)
   - "Generate new token (classic)" or use a fine-grained token for this repo
   - Required scope: **`repo`** (classic) or **Issues: Read and write** (fine-grained)
   - Copy the token (you won’t see it again)

2. **Configure the app**
   - In `apps/web`, copy `.env.example` to `.env.local` if you don’t have it yet
   - Set:
     - `GITHUB_TOKEN=<your-token>` (required for Suggest artist)
     - `GITHUB_REPO=owner/repo` (optional; default: `milnikov/open-tattoo-artists`)

3. **Restart the dev server** so Next.js picks up the new env vars.

After this, "Suggest an artist" will create issues in the configured repo and link them to the user’s Contributions.

**Security:** Never commit `.env.local` or expose `GITHUB_TOKEN` to the client. It is only used in server actions.
