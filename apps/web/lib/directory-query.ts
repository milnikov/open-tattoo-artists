import { artistFollowerCount } from "@/lib/artist-follower-count";

export const DIRECTORY_PAGE_SIZE = 20;

export type DirectorySortKey = "name-asc" | "followers-desc" | "respected-desc";

type Named = { name: string };

type SortableArtist = Named & {
  follower_count?: number;
  instagram_enriched?: boolean | { follower_count?: number };
  followed_by_artists_count?: number;
};

export function sortArtists<T extends SortableArtist>(
  artists: readonly T[],
  sortKey: DirectorySortKey
): T[] {
  if (sortKey === "followers-desc") {
    return [...artists].sort((a, b) => {
      const db = artistFollowerCount(b);
      const da = artistFollowerCount(a);
      if (db !== da) return db - da;
      return a.name.localeCompare(b.name, undefined, { sensitivity: "base" });
    });
  }
  if (sortKey === "respected-desc") {
    return [...artists].sort((a, b) => {
      const rb = b.followed_by_artists_count ?? 0;
      const ra = a.followed_by_artists_count ?? 0;
      if (rb !== ra) return rb - ra;
      return a.name.localeCompare(b.name, undefined, { sensitivity: "base" });
    });
  }
  return [...artists].sort((a, b) =>
    a.name.localeCompare(b.name, undefined, { sensitivity: "base" })
  );
}

export function stylesForDirectory(
  artists: readonly { styles: readonly string[] }[]
): string[] {
  const styleSet = new Set<string>();
  for (const artist of artists) {
    for (const style of artist.styles) styleSet.add(style);
  }
  return Array.from(styleSet).sort();
}

export function countriesForDirectory(
  artists: readonly { location: { country: string } }[],
  allowedCountryNames: readonly string[]
): string[] {
  const countrySet = new Set<string>();
  for (const artist of artists) countrySet.add(artist.location.country);
  const rawCountries = Array.from(countrySet).sort();
  if (allowedCountryNames.length === 0) return rawCountries;
  const allowed = new Set(
    allowedCountryNames.map((country) => country.trim().toLowerCase())
  );
  return rawCountries.filter((country) =>
    allowed.has(country.trim().toLowerCase())
  );
}
