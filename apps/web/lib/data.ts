import fs from "fs";
import path from "path";
import { headers } from "next/headers";

import { getRepoRoot } from "@/lib/repo-root";

const REPO_ROOT = getRepoRoot();

/** Must match artist id in schema / filenames (prevents path traversal in fetch URL). */
const ARTIST_ID_RE = /^[a-z0-9._]{1,30}$/;

function normalizeOrigin(raw: string | undefined): string | undefined {
  const t = raw?.trim();
  if (!t) return undefined;
  return t.replace(/\/$/, "");
}

/**
 * Origins to try for GET /data/artists/<id>.json (after sync-artist-json).
 * Order: explicit CDN → current request host → Vercel deployment host → public site URL → localhost.
 * Set VERCEL_AUTOMATION_BYPASS_SECRET if Deployment Protection blocks server-side fetches.
 */
async function artistJsonFetchOrigins(): Promise<string[]> {
  const origins: string[] = [];
  const add = (o?: string) => {
    const n = normalizeOrigin(o);
    if (n && !origins.includes(n)) origins.push(n);
  };

  add(process.env.ARTIST_DATA_ORIGIN);

  try {
    const h = await headers();
    const host = (h.get("x-forwarded-host")?.split(",")[0] || h.get("host"))?.trim();
    if (host) {
      const local = /^127\.|^\[::1\]|^localhost(?::|$)/i.test(host);
      const proto = local
        ? "http"
        : (h.get("x-forwarded-proto")?.split(",")[0]?.trim() ?? "https");
      add(`${proto}://${host}`);
    }
  } catch {
    /* outside a request */
  }

  if (process.env.VERCEL_URL) {
    const host = process.env.VERCEL_URL.replace(/^https?:\/\//, "").split("/")[0]?.trim();
    if (host) add(`https://${host}`);
  }

  const site = process.env.NEXT_PUBLIC_SITE_URL;
  if (site && !/localhost|127(\.|$)|^\[::1\]/i.test(site)) {
    add(site);
  }

  add("http://127.0.0.1:3000");

  return origins;
}

function mergeArtistFetchHeaders(base?: HeadersInit): Headers {
  const h = new Headers(base ?? undefined);
  const secret = process.env.VERCEL_AUTOMATION_BYPASS_SECRET?.trim();
  if (secret) {
    h.set("x-vercel-protection-bypass", secret);
    h.set("x-vercel-set-bypass-cookie", "true");
  }
  // Some CDNs/WAFs block or challenge requests with no User-Agent (default Node fetch).
  if (!h.has("user-agent")) {
    h.set("user-agent", "Mozilla/5.0 (compatible; OpenTattooArtists/1.0)");
  }
  if (!h.has("accept")) {
    h.set("accept", "application/json,*/*;q=0.1");
  }
  return h;
}

/** Allowed country names (from data/indexes/countries.json). Only these are shown; rest hide artist. */
let allowedCountriesCache: { mtimeMs: number; set: Set<string> } | null = null;

function getAllowedCountries(): Set<string> {
  const p = path.join(REPO_ROOT, "data", "indexes", "countries.json");
  const mtimeMs = fs.existsSync(p) ? fs.statSync(p).mtimeMs : -1;
  if (allowedCountriesCache && allowedCountriesCache.mtimeMs === mtimeMs) {
    return allowedCountriesCache.set;
  }
  // Visibility filter uses countries; invalidate compact list if country list changed.
  compactArtistsCache = null;
  if (!fs.existsSync(p)) {
    allowedCountriesCache = { mtimeMs, set: new Set(["Unknown"]) };
    return allowedCountriesCache.set;
  }
  const list = JSON.parse(fs.readFileSync(p, "utf-8")) as string[];
  const set = new Set(list.map((c) => c.trim().toLowerCase()));
  allowedCountriesCache = { mtimeMs, set };
  return set;
}

function isStrangeCountry(country: string | undefined): boolean {
  if (country == null || String(country).trim() === "") return true;
  const allowed = getAllowedCountries();
  const normalized = String(country).trim().toLowerCase();
  return !allowed.has(normalized);
}

function isEmptyAbout(bio: string | null | undefined): boolean {
  if (bio == null) return true;
  return typeof bio !== "string" || bio.trim() === "";
}

/**
 * Match build_indexes.py: compact rows use top-level follower_count from instagram_enriched,
 * but raw artist JSON often only has instagram_enriched.follower_count.
 */
function artistFollowerCount(artist: {
  follower_count?: number;
  instagram_enriched?: { follower_count?: number };
}): number {
  if (typeof artist.follower_count === "number" && !Number.isNaN(artist.follower_count)) {
    return artist.follower_count;
  }
  const fc = artist.instagram_enriched?.follower_count;
  if (typeof fc === "number" && !Number.isNaN(fc)) return fc;
  return 0;
}

/** True if the artist should be hidden: only 1 image, strange country, or empty about (unless >5 images and >1000 followers). */
function isArtistHidden(artist: {
  tattoo_count?: number;
  tattoos?: unknown[];
  location: { country: string };
  bio?: string | null;
  follower_count?: number;
  instagram_enriched?: { follower_count?: number };
}): boolean {
  const count =
    artist.tattoo_count ?? (Array.isArray(artist.tattoos) ? artist.tattoos.length : 0);
  if (count <= 1) return true;
  if (isStrangeCountry(artist.location?.country)) return true;
  if (isEmptyAbout(artist.bio)) {
    const fc = artistFollowerCount(artist);
    if (!(count > 5 && fc > 1000)) return true;
  }
  return false;
}

export interface CompactArtist {
  id: string;
  name: string;
  location: { city: string; country: string };
  styles: string[];
  links: { instagram: string };
  tattoo_count: number;
  thumb?: string;
  /** Up to 4 thumb URLs for list view. Falls back to [thumb] when absent. */
  thumbs?: string[];
  /** Optional bio for list excerpt. */
  bio?: string | null;
  /** When artist info was last updated (e.g. "2026-03-06"). */
  updated_at?: string;
  /** Instagram follower count (from instagram_enriched); used to show artists with no bio when >1000. */
  follower_count?: number;
  /** Optional moderation flag: "artist" | "studio". Missing = not verified yet. */
  verified?: "artist" | "studio";
  /** Domain of links.source (e.g. "tattooswizard.com"). */
  source_domain?: string;
  /** Whether the artist JSON has instagram_enriched data. */
  instagram_enriched?: boolean;
}

export interface SearchIndexEntry {
  id: string;
  name: string;
  normalized: string;
}

export interface Artist {
  id: string;
  name: string;
  location: { city: string; country: string };
  styles: string[];
  links: {
    instagram: string;
    website?: string;
    source?: string;
  };
  bio?: string | null;
  tattoos: Array<{
    image_id: string;
    image_full: string;
    image_thumb: string;
  }>;
  updated_at: string;
  /** Optional moderation flag: "artist" | "studio". Missing = not verified yet. */
  verified?: "artist" | "studio";
  instagram_enriched?: { follower_count?: number };
}

let compactArtistsCache: { mtimeMs: number; artists: CompactArtist[] } | null = null;

export function getCompactArtists(): CompactArtist[] {
  const p = path.join(REPO_ROOT, "data", "indexes", "artists.compact.json");
  if (!fs.existsSync(p)) return [];
  const st = fs.statSync(p);
  if (compactArtistsCache && compactArtistsCache.mtimeMs === st.mtimeMs) {
    return compactArtistsCache.artists;
  }
  const all = JSON.parse(fs.readFileSync(p, "utf-8")) as CompactArtist[];
  // verified, source_domain, instagram_enriched come from scripts/build_indexes.py (no per-artist fs reads).
  const artists = all.filter((a) => !isArtistHidden(a));
  compactArtistsCache = { mtimeMs: st.mtimeMs, artists };
  return artists;
}

export function getSearchIndex(): SearchIndexEntry[] {
  const p = path.join(REPO_ROOT, "data", "indexes", "search-index.json");
  if (!fs.existsSync(p)) return [];
  return JSON.parse(fs.readFileSync(p, "utf-8"));
}

/**
 * Load full artist JSON via fetch from /data/artists/<id>.json (public/ after sync-artist-json).
 * Tries several origins; do not use fs.readFile paths here — that pulls ~15k files into every route importing this module.
 * Set VERCEL_AUTOMATION_BYPASS_SECRET if Deployment Protection blocks server fetches.
 */
export async function getArtist(
  id: string,
  fetchInit?: RequestInit
): Promise<Artist | null> {
  if (!ARTIST_ID_RE.test(id)) return null;

  const origins = await artistJsonFetchOrigins();
  const init: RequestInit = {
    ...fetchInit,
    headers: mergeArtistFetchHeaders(fetchInit?.headers),
    cache: fetchInit?.cache ?? "no-store",
  };

  for (const origin of origins) {
    const url = `${origin}/data/artists/${encodeURIComponent(id)}.json`;
    try {
      const res = await fetch(url, init);
      if (!res.ok) continue;
      const artist = (await res.json()) as Artist;
      if (isArtistHidden(artist)) return null;
      return artist;
    } catch {
      continue;
    }
  }
  return null;
}

export function getStyles(): string[] {
  const p = path.join(REPO_ROOT, "data", "styles", "styles.json");
  if (!fs.existsSync(p)) return [];
  const data = JSON.parse(fs.readFileSync(p, "utf-8"));
  return Array.isArray(data) ? data : [];
}

/** Allowed country names for filter UI (only these may appear in the country dropdown). */
export function getAllowedCountryNames(): string[] {
  const p = path.join(REPO_ROOT, "data", "indexes", "countries.json");
  if (!fs.existsSync(p)) return ["Unknown"];
  const list = JSON.parse(fs.readFileSync(p, "utf-8")) as string[];
  return list.map((c) => c.trim()).filter(Boolean);
}
