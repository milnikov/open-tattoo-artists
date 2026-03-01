"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { imageUrl } from "@/lib/images";
import type { CompactArtist } from "@/lib/data";

export function ArtistListWithFilters({
  artists,
  contributorMap = {},
}: {
  artists: CompactArtist[];
  contributorMap?: Record<string, string>;
}) {
  const [styleFilter, setStyleFilter] = useState("");
  const [countryFilter, setCountryFilter] = useState("");
  const [cityFilter, setCityFilter] = useState("");

  const { styles, countries, citiesInCountry } = useMemo(() => {
    const styleSet = new Set<string>();
    const countrySet = new Set<string>();
    const cityByCountry = new Map<string, Set<string>>();
    for (const a of artists) {
      for (const s of a.styles) styleSet.add(s);
      const c = a.location.country;
      countrySet.add(c);
      if (!cityByCountry.has(c)) cityByCountry.set(c, new Set());
      cityByCountry.get(c)!.add(a.location.city);
    }
    const styles = Array.from(styleSet).sort();
    const countries = Array.from(countrySet).sort();
    const citiesInCountry = countryFilter
      ? Array.from(cityByCountry.get(countryFilter) ?? []).sort()
      : [];
    return { styles, countries, citiesInCountry };
  }, [artists, countryFilter]);

  const filtered = useMemo(() => {
    return artists.filter((a) => {
      if (styleFilter && !a.styles.includes(styleFilter)) return false;
      if (countryFilter && a.location.country !== countryFilter) return false;
      if (cityFilter && a.location.city !== cityFilter) return false;
      return true;
    });
  }, [artists, styleFilter, countryFilter, cityFilter]);

  return (
    <div>
      <div className="mb-6 flex flex-wrap items-center gap-3">
        <label className="flex items-center gap-2">
          <span className="text-sm font-medium text-gray-700">Style</span>
          <select
            value={styleFilter}
            onChange={(e) => setStyleFilter(e.target.value)}
            className="rounded border border-gray-300 bg-white px-2 py-1.5 text-sm"
          >
            <option value="">All styles</option>
            {styles.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </label>
        <label className="flex items-center gap-2">
          <span className="text-sm font-medium text-gray-700">Country</span>
          <select
            value={countryFilter}
            onChange={(e) => {
              setCountryFilter(e.target.value);
              setCityFilter("");
            }}
            className="rounded border border-gray-300 bg-white px-2 py-1.5 text-sm"
          >
            <option value="">All countries</option>
            {countries.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
        </label>
        <label className="flex items-center gap-2">
          <span className="text-sm font-medium text-gray-700">City</span>
          <select
            value={cityFilter}
            onChange={(e) => setCityFilter(e.target.value)}
            className="rounded border border-gray-300 bg-white px-2 py-1.5 text-sm"
            disabled={!countryFilter}
          >
            <option value="">All cities</option>
            {citiesInCountry.map((city) => (
              <option key={city} value={city}>
                {city}
              </option>
            ))}
          </select>
        </label>
      </div>

      <p className="text-gray-600 mb-6">
        {filtered.length} artist{filtered.length !== 1 ? "s" : ""}
      </p>

      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6">
        {filtered.map((a) => (
          <Link
            key={a.id}
            href={`/artists/${a.id}`}
            className="block border bg-white rounded-lg overflow-hidden hover:shadow-md transition"
          >
            <div className="aspect-square bg-gray-200 relative overflow-hidden">
              {a.thumb ? (
                <img
                  src={imageUrl(a.thumb)}
                  alt={a.name}
                  className="w-full h-full object-cover"
                />
              ) : (
                <div className="w-full h-full flex items-center justify-center text-gray-400">
                  {a.tattoo_count > 0 ? (
                    <span className="text-sm">{a.tattoo_count} images</span>
                  ) : (
                    <span>No image</span>
                  )}
                </div>
              )}
            </div>
            <div className="p-3">
              <h2 className="font-semibold truncate">{a.name}</h2>
              {contributorMap[a.id] && (
                <p className="text-xs text-gray-500 truncate">
                  Contributed by {contributorMap[a.id]}
                </p>
              )}
              <p className="text-sm text-gray-600 truncate">
                {a.location.city}, {a.location.country}
              </p>
              {a.styles.length > 0 && (
                <p className="text-xs text-gray-500 mt-1">
                  {a.styles.slice(0, 3).join(", ")}
                </p>
              )}
            </div>
          </Link>
        ))}
      </div>
      {filtered.length === 0 && (
        <p className="text-gray-500 py-12 text-center">
          No artists match the selected filters.
        </p>
      )}
    </div>
  );
}
