/**
 * Copy data/artists/*.json → public/data/artists/ so full artist records are served
 * as static files. lib/data.ts loads them via fetch (avoids Next file-tracing 15k+ JSON
 * into each serverless function on Vercel).
 *
 * Run from apps/web: npm run sync-artist-json
 * Repo root must contain data/artists (Vercel checks out full repo; Root Directory = apps/web).
 */
const fs = require("fs");
const path = require("path");

const webRoot = path.join(__dirname, "..");
const repoRoot = path.join(webRoot, "..", "..");
const src = path.join(repoRoot, "data", "artists");
const dest = path.join(webRoot, "public", "data", "artists");

if (!fs.existsSync(src)) {
  console.error("sync-artist-json-to-public: source directory not found:", src);
  process.exit(1);
}

fs.mkdirSync(dest, { recursive: true });
let n = 0;
for (const f of fs.readdirSync(src)) {
  if (!f.endsWith(".json")) continue;
  fs.copyFileSync(path.join(src, f), path.join(dest, f));
  n += 1;
}
console.log(`sync-artist-json-to-public: copied ${n} JSON files → ${dest}`);
