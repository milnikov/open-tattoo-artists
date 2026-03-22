const path = require("path");

const monorepoRoot = path.join(__dirname, "..", "..");

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Indexes live under repo root data/indexes (outside apps/web); trace from monorepo root for Vercel.
  outputFileTracingRoot: monorepoRoot,
  turbopack: {
    root: monorepoRoot,
  },
  outputFileTracingIncludes: {
    "*": [
      "../../data/indexes/**/*",
      "../../data/styles/**/*",
    ],
  },
  // Per-artist JSON is served from /public (copied at build); do not pack into serverless bundles.
  outputFileTracingExcludes: {
    "*": ["./public/data/artists/**/*"],
  },
};

module.exports = nextConfig;
