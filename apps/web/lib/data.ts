import fs from "fs";
import path from "path";

/** Resolve repo root by finding where data/indexes exists (works from repo root or apps/web). */
function getRepoRoot(): string {
  const candidates = [
    process.cwd(),
    path.join(process.cwd(), ".."),
    path.join(process.cwd(), "..", ".."),
    path.join(process.cwd(), "apps", "web"),
  ];
  for (const root of candidates) {
    const p = path.join(root, "data", "indexes", "countries.json");
    if (fs.existsSync(p)) return root;
  }
  return path.join(process.cwd(), "..", "..");
}

const REPO_ROOT = getRepoRoot();

/** Allowed country names (from data/indexes/countries.json). Only these are shown; rest hide artist. */
function getAllowedCountries(): Set<string> {
  const p = path.join(REPO_ROOT, "data", "indexes", "countries.json");
  if (!fs.existsSync(p)) return new Set(["Unknown"]);
  const list = JSON.parse(fs.readFileSync(p, "utf-8")) as string[];
  return new Set(list.map((c) => c.trim().toLowerCase()));
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

export function getCompactArtists(): CompactArtist[] {
  const p = path.join(REPO_ROOT, "data", "indexes", "artists.compact.json");
  if (!fs.existsSync(p)) return [];
  const all = JSON.parse(fs.readFileSync(p, "utf-8")) as CompactArtist[];

  const visible = all.filter((a) => !isArtistHidden(a));

  function getDomain(url: string | undefined): string | null {
    if (!url) return null;
    try {
      const u = new URL(url);
      return u.hostname.replace(/^www\./, "");
    } catch {
      return null;
    }
  }

  // Enrich with verified/source from full artist JSON when available.
  return visible.map((a) => {
    try {
      const fullPath = path.join(REPO_ROOT, "data", "artists", `${a.id}.json`);
      if (!fs.existsSync(fullPath)) return a;
      const full = JSON.parse(fs.readFileSync(fullPath, "utf-8")) as Artist;
      const sourceDomain = getDomain(full.links?.source);
      return {
        ...a,
        verified: full.verified ?? a.verified,
        source_domain: sourceDomain ?? a.source_domain,
      };
    } catch {
      return a;
    }
  });
}

export function getSearchIndex(): SearchIndexEntry[] {
  const p = path.join(REPO_ROOT, "data", "indexes", "search-index.json");
  if (!fs.existsSync(p)) return [];
  return JSON.parse(fs.readFileSync(p, "utf-8"));
}

export function getArtist(id: string): Artist | null {
  const p = path.join(REPO_ROOT, "data", "artists", `${id}.json`);
  if (!fs.existsSync(p)) return null;
  const artist = JSON.parse(fs.readFileSync(p, "utf-8")) as Artist;
  if (isArtistHidden(artist)) return null;
  return artist;
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
