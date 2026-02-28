#!/usr/bin/env node
/**
 * Copy repo data/ into apps/web/data for Vercel (and any deploy where only apps/web is deployed).
 * Run from apps/web. No-op if ../../data does not exist.
 */
const fs = require("fs");
const path = require("path");

const from = path.join(__dirname, "..", "..", "data");
const to = path.join(__dirname, "..", "data");

if (!fs.existsSync(from)) {
  console.log("copy-data: no ../../data, skipping");
  process.exit(0);
}

function copyRecursive(src, dest) {
  const stat = fs.statSync(src);
  if (stat.isDirectory()) {
    if (!fs.existsSync(dest)) fs.mkdirSync(dest, { recursive: true });
    for (const name of fs.readdirSync(src)) {
      copyRecursive(path.join(src, name), path.join(dest, name));
    }
  } else {
    fs.mkdirSync(path.dirname(dest), { recursive: true });
    fs.copyFileSync(src, dest);
  }
}

copyRecursive(from, to);
console.log("copy-data: copied data/ into apps/web/data");
