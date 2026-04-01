/**
 * Copy data/artists/*.json → public/data/artists/ so full artist records are served
 * as static files. lib/data.ts loads them via fetch (avoids Next file-tracing 15k+ JSON
 * into each serverless function on Vercel).
 *
 * Public copies omit links.source so upstream directory URLs are not world-readable.
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
  const srcPath = path.join(src, f);
  const destPath = path.join(dest, f);
  let obj;
  try {
    obj = JSON.parse(fs.readFileSync(srcPath, "utf-8"));
  } catch (e) {
    console.error("sync-artist-json-to-public: invalid JSON:", srcPath, e.message);
    process.exit(1);
  }
  if (obj && typeof obj.links === "object" && obj.links !== null) {
    const { source: _drop, ...rest } = obj.links;
    obj.links = rest;
  }
  fs.writeFileSync(destPath, `${JSON.stringify(obj, null, 2)}\n`, "utf-8");
  n += 1;
}
console.log(`sync-artist-json-to-public: wrote ${n} sanitized JSON files → ${dest}`);
