# Cloudflare hardening for public images (R2 / custom domain)

Images are served from a public base URL (`NEXT_PUBLIC_IMAGES_BASE_URL`, e.g. `https://pub-xxxx.r2.dev` or a custom domain in front of R2). Use Cloudflare on **that hostname** to slow scrapers and reduce cost without changing image URLs in the app.

## Prerequisites

- The image hostname is **proxied through Cloudflare** (orange cloud), or you use **R2 custom domain** + Cloudflare DNS.
- You can open: **Security** → **WAF**, **Security** → **Bots**, **Security** → **Rate limiting rules** (names vary slightly by plan).

### Free / lower plans: no regex “matches”

If Cloudflare says **“operator Matches is not allowed”** (Business / WAF Advanced required), **do not use** the **matches (regex)** operator. Use **starts with**, **ends with**, and **equals** instead, for example:

- **Rate limiting:** `URI Path` **starts with** `/artists/` (covers `.../thumb/...` and `.../full/...` on your image host). Optionally add **AND** `Hostname` **equals** `img.thetattoo.world`.
- **Custom rules:** same idea—combine **Hostname equals** your image subdomain with **URI Path starts with** `/artists/` (and **ends with** `.webp` if the rule builder offers it).

This is slightly broader than a single regex but works on free/Pro-style plans.

## 1) Bot protection

1. **Security** → **Bots**
2. Turn on **Bot Fight Mode** (free) or **Super Bot Fight Mode** / **Bot Management** (paid), depending on plan.
3. Prefer **challenge** or **block** for **definitely automated** traffic on the image zone; start with challenge to limit false positives.

## 2) Rate limiting on image paths

Object keys look like:

- `artists/<handle>/thumb/<id>.webp`
- `artists/<handle>/full/<id>.webp`

Create a **Rate limiting rule** (or WAF rate limit, by product):

| Setting | Suggested start |
|--------|------------------|
| **If incoming requests match** | **Paid (regex):** URI Path **matches** `^/artists/.+/(thumb|full)/.+\.webp$`. **Free/Pro:** URI Path **starts with** `/artists/` (optional **AND** Hostname **equals** `img.thetattoo.world`). |
| **Then** | Block or Managed challenge (prefer challenge first) |
| **When rate exceeds** | e.g. **600 requests / 1 minute** per **IP** (tune up/down from traffic) |
| **Duration** | 1 minute or per your plan’s options |

Add a **separate**, **stricter** rule for obvious automation (optional): e.g. **same path pattern** AND **Bot score** low / **Verified Bot** is false.

## 3) Hotlink / header checks (optional, tune carefully)

Aggressive Referer-only rules can break RSS, email clients, or embeds. Safer options:

- **WAF custom rule:** if `Accept` **does not contain** `image` **AND** URI Path **starts with** `/artists/` (free/Pro), then **Managed challenge**. On plans that allow regex, you can narrow with **matches** instead of **starts with**. Browsers loading `<img>` usually send an `Accept` header that includes `image`.

## 4) Caching on the edge

If responses are cacheable at the CDN:

- Set **Cache Level** / **Cache Rules** so `.webp` under `/artists/` is **eligible for cache** with long TTL (objects already use `Cache-Control: public, max-age=31536000, immutable` from the uploader).

This cuts **origin (R2) egress** when the same URL is hit often (good for legitimate users; scrapers still consume bandwidth but hit the edge more).

## 5) Image host `robots.txt` (optional)

A raw R2 public URL often **cannot** serve `robots.txt` at bucket root. Options:

- Put a **Cloudflare Worker** on the image hostname that returns `404` or a minimal `robots.txt` (e.g. `Disallow: /`) for **only** `/robots.txt`, and otherwise proxies to R2.
- Or use a **custom domain** where Workers / Rules can serve static `robots.txt`.

Discouraging crawlers does **not** stop scrapers; it helps with polite bots and signals policy.

## 6) Main site (Vercel) behind Cloudflare (optional)

If you proxy your **app** domain through Cloudflare:

- Add **rate limiting** or **WAF rules** for paths:
  - `/api/map-data`
  - `/api/map-hex-artists`
  - `/api/artists/*`

The repo applies **Next.js middleware** ([`apps/web/middleware.ts`](../apps/web/middleware.ts)) as a baseline (per-edge-isolate sliding window; tune limits there if needed). **Cloudflare WAF / rate limiting** is stronger at scale and consistent across regions.

See also: [MONITORING_ANTI_SCRAPE.md](./MONITORING_ANTI_SCRAPE.md).
