/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Per-artist JSON is served from /public (copied at build); do not pack into serverless bundles.
  outputFileTracingExcludes: {
    "*": ["./public/data/artists/**/*"],
  },
};

module.exports = nextConfig;
