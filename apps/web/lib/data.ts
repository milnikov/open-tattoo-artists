import fs from "fs";
import path from "path";

// Directory containing indexes/, artists/, styles/. Prefer in-app data/ (Vercel); else repo data/ (local).
const DATA_DIR = (() => {
  const inApp = path.join(process.cwd(), "data");
  if (fs.existsSync(inApp)) return inApp;
  return path.join(process.cwd(), "..", "..", "data");
})();

export interface CompactArtist {
  id: string;
  name: string;
  location: { city: string; country: string };
  styles: string[];
  links: { instagram: string };
  tattoo_count: number;
  thumb?: string;
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
  tattoos: Array<{
    image_id: string;
    image_full: string;
    image_thumb: string;
  }>;
  updated_at: string;
}

export function getCompactArtists(): CompactArtist[] {
  const p = path.join(DATA_DIR, "indexes", "artists.compact.json");
  if (!fs.existsSync(p)) return [];
  return JSON.parse(fs.readFileSync(p, "utf-8"));
}

export function getSearchIndex(): SearchIndexEntry[] {
  const p = path.join(DATA_DIR, "indexes", "search-index.json");
  if (!fs.existsSync(p)) return [];
  return JSON.parse(fs.readFileSync(p, "utf-8"));
}

export function getArtist(id: string): Artist | null {
  const p = path.join(DATA_DIR, "artists", `${id}.json`);
  if (!fs.existsSync(p)) return null;
  return JSON.parse(fs.readFileSync(p, "utf-8"));
}

export function getStyles(): string[] {
  const p = path.join(DATA_DIR, "styles", "styles.json");
  if (!fs.existsSync(p)) return [];
  const data = JSON.parse(fs.readFileSync(p, "utf-8"));
  return Array.isArray(data) ? data : [];
}
