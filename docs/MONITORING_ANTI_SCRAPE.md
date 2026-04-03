# Monitoring and tuning anti-scrape controls

Use this after Cloudflare rules and app-side rate limits are in place. Goal: catch spikes, tune thresholds, avoid blocking real users.

## What to watch

### Cloudflare (image zone)

- **Security** → **Events** (or **Analytics** → **Security**): rate of **challenges**, **blocks**, **WAF** matches.
- **Traffic** → **Requests** by country / ASN: sudden spikes from one AS (hosting/datacenter) often indicate scraping.
- **Rate limiting rule** analytics: how often the cap fires (adjust if too noisy vs too loose).

### Cloudflare (app zone, if proxied)

- Same security metrics for `/api/*` if you add WAF/rate rules there.
- Correlate **429** responses from origin (Vercel) vs edge challenges.

### Vercel

- **Logs** (or observability): spikes in **429** on `/api/map-data`, `/api/artists/compact`, etc.
- **Function duration / invocation** counts: unusual growth may mean abuse or a hot endpoint.

## Alerts (suggested)

1. **Cloudflare**: alert when **security events** or **rate limit triggers** exceed N/hour vs a 7-day baseline (exact product: Notification rules / third-party).
2. **Vercel**: alert when **429 rate** or **error rate** on `api/*` exceeds threshold.

## Tuning workflow

1. Start with **challenge** before **block** for image paths.
2. If scrapers still pull too much: **lower** the requests/minute per IP or add **bot score** conditions.
3. If users report broken images: loosen **Accept** / **Referer** rules first; then relax rate limits slightly.
4. Document the final numbers (per-path, per-IP) in your runbook so the team can revert after incidents.
