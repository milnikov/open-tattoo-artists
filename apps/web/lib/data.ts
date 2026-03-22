import fs from "fs";
import path from "path";

import { getRepoRoot } from "@/lib/repo-root";

const REPO_ROOT = getRepoRoot();

/** Must match artist id in schema / filenames (prevents path traversal in fetch URL). */
const ARTIST_ID_RE = /^[a-z0-9._]{1,30}$/;

/**
 * Origin for loading /data/artists/<id>.json (static files under public/, copied at build).
 * Override with ARTIST_DATA_ORIGIN or NEXT_PUBLIC_SITE_URL if self-fetch fails (e.g. custom domain edge cases).
 */
function getArtistDataOrigin(): string {
  const fromEnv =
    process.env.ARTIST_DATA_ORIGIN?.replace(/\/$/, "") ||
    process.env.NEXT_PUBLIC_SITE_URL?.replace(/\/$/, "");
  if (fromEnv) return fromEnv;
  if (process.env.VERCEL_URL) return `https://${process.env.VERCEL_URL}`;
  return "http://127.0.0.1:3000";
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

/** True if the artist should be hidden: only 1 image, strange country, or empty about (unless >5 images and >1000 followers). */
function isArtistHidden(artist: {
  tattoo_count?: number;
  tattoos?: unknown[];
  location: { country: string };
  bio?: string | null;
  follower_count?: number;
}): boolean {
  const count =
    artist.tattoo_count ?? (Array.isArray(artist.tattoos) ? artist.tattoos.length : 0);
  if (count <= 1) return true;
  if (isStrangeCountry(artist.location?.country)) return true;
  if (isEmptyAbout(artist.bio)) {
    const fc = artist.follower_count ?? 0;
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
 * Load full artist JSON via fetch from static /data/artists/<id>.json (see sync-artist-json-to-public.cjs).
 * Avoids fs + dynamic path, which would make Next trace ~15k files into every serverless function on Vercel.
 */
export async function getArtist(
  id: string,
  fetchInit?: RequestInit
): Promise<Artist | null> {
  if (!ARTIST_ID_RE.test(id)) return null;
  const url = `${getArtistDataOrigin()}/data/artists/${encodeURIComponent(id)}.json`;
  try {
    const res = await fetch(url, fetchInit);
    if (!res.ok) return null;
    const artist = (await res.json()) as Artist;
    if (isArtistHidden(artist)) return null;
    return artist;
  } catch {
    return null;
  }
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
