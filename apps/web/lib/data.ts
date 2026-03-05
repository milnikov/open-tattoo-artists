import fs from "fs";
import path from "path";

const REPO_ROOT = path.join(process.cwd(), "..", "..");

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
}

export function getCompactArtists(): CompactArtist[] {
  const p = path.join(REPO_ROOT, "data", "indexes", "artists.compact.json");
  if (!fs.existsSync(p)) return [];
  return JSON.parse(fs.readFileSync(p, "utf-8"));
}

export function getSearchIndex(): SearchIndexEntry[] {
  const p = path.join(REPO_ROOT, "data", "indexes", "search-index.json");
  if (!fs.existsSync(p)) return [];
  return JSON.parse(fs.readFileSync(p, "utf-8"));
}

export function getArtist(id: string): Artist | null {
  const p = path.join(REPO_ROOT, "data", "artists", `${id}.json`);
  if (!fs.existsSync(p)) return null;
  return JSON.parse(fs.readFileSync(p, "utf-8"));
}

export function getStyles(): string[] {
  const p = path.join(REPO_ROOT, "data", "styles", "styles.json");
  if (!fs.existsSync(p)) return [];
  const data = JSON.parse(fs.readFileSync(p, "utf-8"));
  return Array.isArray(data) ? data : [];
}
