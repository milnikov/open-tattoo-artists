import { getCompactArtists } from "@/lib/data";
import { getRepoRoot } from "@/lib/repo-root";
import { NextRequest, NextResponse } from "next/server";
import fs from "fs";
import path from "path";

const REPO_ROOT = getRepoRoot();

type Coords = [number, number];

function loadCountryCentroids(): Record<string, Coords> {
  const p = path.join(REPO_ROOT, "data", "indexes", "country-centroids.json");
  if (!fs.existsSync(p)) return {};
  return JSON.parse(fs.readFileSync(p, "utf-8"));
}

function loadCityCoords(): Record<string, Coords> {
  const p = path.join(REPO_ROOT, "data", "indexes", "city-coords.json");
  if (!fs.existsSync(p)) return {};
  return JSON.parse(fs.readFileSync(p, "utf-8"));
}

const COUNTRY_ALIASES: Record<string, string> = {
  UK: "United Kingdom",
  "United Kingdom of Great Britain and Northern Ireland": "United Kingdom",
  USA: "United States",
  "United States of America": "United States",
  "Korea, Republic of": "South Korea",
  "Republic of Korea": "South Korea",
};

function resolveCoords(
  city: string,
  country: string,
  countryCentroids: Record<string, Coords>,
  cityCoords: Record<string, Coords>
): Coords | null {
  const cityKey = `${city.trim()}|${country.trim()}`;
  if (cityCoords[cityKey]) return cityCoords[cityKey];
  const c = country.trim();
  if (countryCentroids[c]) return countryCentroids[c];
  const alias = COUNTRY_ALIASES[c];
  if (alias && countryCentroids[alias]) return countryCentroids[alias];
  return null;
}

export interface MapPoint {
  lat: number;
  lng: number;
  count: number;
  city: string;
  country: string;
  label: string;
  /** Set when no style filter: each point is one (location, style) for coloring by dominant style. */
  style?: string;
}

export async function GET(request: NextRequest) {
  const styleParam = request.nextUrl.searchParams.get("style")?.trim() || null;
  const artists = getCompactArtists();
  const countryCentroids = loadCountryCentroids();
  const cityCoords = loadCityCoords();

  const allStyles = new Set<string>();

  if (styleParam) {
    // Single style: one point per (city, country) with total count
    const locationCount = new Map<string, { city: string; country: string; count: number }>();
    for (const a of artists) {
      for (const s of a.styles) allStyles.add(s);
      if (!a.styles.includes(styleParam)) continue;
      const city = a.location?.city?.trim() || "";
      const country = a.location?.country?.trim() || "";
      if (!country) continue;
      const key = `${city}|${country}`;
      const prev = locationCount.get(key);
      if (prev) prev.count += 1;
      else locationCount.set(key, { city, country, count: 1 });
    }
    const points: MapPoint[] = [];
    for (const [, { city, country, count }] of locationCount) {
      const coords = resolveCoords(city, country, countryCentroids, cityCoords);
      if (!coords) continue;
      const [lat, lng] = coords;
      points.push({
        lat,
        lng,
        count,
        city,
        country,
        label: city ? `${city}, ${country}: ${count}` : `${country}: ${count}`,
        style: styleParam,
      });
    }
    const totalArtists = artists.filter((a) => a.styles.includes(styleParam)).length;
    return NextResponse.json({
      points,
      styles: Array.from(allStyles).sort(),
      totalArtists,
    });
  }

  // All styles: one point per (city, country, style) so hex bins can be colored by dominant style
  const locationByStyle = new Map<
    string,
    { city: string; country: string; styleCount: Map<string, number> }
  >();
  for (const a of artists) {
    for (const s of a.styles) allStyles.add(s);
    const city = a.location?.city?.trim() || "";
    const country = a.location?.country?.trim() || "";
    if (!country) continue;
    const key = `${city}|${country}`;
    let loc = locationByStyle.get(key);
    if (!loc) {
      loc = { city, country, styleCount: new Map<string, number>() };
      locationByStyle.set(key, loc);
    }
    for (const s of a.styles) {
      loc.styleCount.set(s, (loc.styleCount.get(s) ?? 0) + 1);
    }
  }

  const points: MapPoint[] = [];
  for (const [, { city, country, styleCount }] of locationByStyle) {
    const coords = resolveCoords(city, country, countryCentroids, cityCoords);
    if (!coords) continue;
    const [lat, lng] = coords;
    for (const [style, count] of styleCount) {
      points.push({
        lat,
        lng,
        count,
        city,
        country,
        label: city ? `${city}, ${country}: ${count} (${style})` : `${country}: ${count} (${style})`,
        style,
      });
    }
  }

  return NextResponse.json({
    points,
    styles: Array.from(allStyles).sort(),
    totalArtists: artists.length,
  });
}
