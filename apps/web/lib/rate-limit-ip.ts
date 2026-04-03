/**
 * Best-effort per-edge-isolate sliding window rate limit.
 * For strong cross-region limits, use Cloudflare WAF / Upstash on Vercel.
 */

type RateLimitRule = { windowMs: number; max: number };

const buckets = new Map<string, number[]>();
const MAX_KEYS = 25_000;

function pruneGlobal(now: number, windowMs: number): void {
  if (buckets.size <= MAX_KEYS || Math.random() > 0.02) return;
  for (const [k, times] of buckets) {
    const kept = times.filter((t) => now - t < windowMs);
    if (kept.length === 0) buckets.delete(k);
    else buckets.set(k, kept);
  }
}

export function rateLimitAllow(key: string, rule: RateLimitRule): boolean {
  const now = Date.now();
  pruneGlobal(now, rule.windowMs);

  let times = buckets.get(key)?.filter((t) => now - t < rule.windowMs) ?? [];
  if (times.length >= rule.max) {
    buckets.set(key, times);
    return false;
  }
  times = [...times, now];
  buckets.set(key, times);
  return true;
}

export function getClientIp(request: Request): string {
  const cf = request.headers.get("cf-connecting-ip")?.trim();
  if (cf) return cf;
  const forwarded = request.headers.get("x-forwarded-for");
  if (forwarded) {
    const first = forwarded.split(",")[0]?.trim();
    if (first) return first;
  }
  const real = request.headers.get("x-real-ip")?.trim();
  if (real) return real;
  return "unknown";
}
