import type { MetadataRoute } from "next";

function siteHost(): string | undefined {
  const raw = process.env.NEXT_PUBLIC_SITE_URL?.trim();
  if (!raw) return undefined;
  try {
    const u = new URL(raw.includes("://") ? raw : `https://${raw}`);
    return u.host;
  } catch {
    return undefined;
  }
}

/**
 * Discourage polite crawlers from hammering JSON APIs. Pages remain indexable.
 * For the separate R2 image hostname, see docs/CLOUDFLARE_ANTI_SCRAPE.md (robots.txt options).
 */
export default function robots(): MetadataRoute.Robots {
  const host = siteHost();

  return {
    rules: [
      {
        userAgent: "*",
        allow: "/",
        disallow: ["/api/"],
      },
    ],
    ...(host ? { host } : {}),
  };
}
