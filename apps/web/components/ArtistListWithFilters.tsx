"use client";

import { useMemo, useState, useEffect } from "react";
import Link from "next/link";
import { imageUrl } from "@/lib/images";
import type { CompactArtist } from "@/lib/data";

const PAGE_SIZE = 50;

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
  const [page, setPage] = useState(1);

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
    const citiesInCountry =
      countryFilter && countryFilter !== "Unknown"
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

  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const paginated = useMemo(
    () => filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE),
    [filtered, page]
  );

  useEffect(() => {
    setPage(1);
  }, [styleFilter, countryFilter, cityFilter]);

  useEffect(() => {
    if (countryFilter === "Unknown") setCityFilter("");
  }, [countryFilter]);

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
            disabled={!countryFilter || countryFilter === "Unknown"}
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
        {totalPages > 1 && (
          <span className="text-gray-500 ml-2">
            (page {page} of {totalPages})
          </span>
        )}
      </p>

      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6">
        {paginated.map((a) => (
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

      {totalPages > 1 && filtered.length > 0 && (
        <div className="mt-8 flex items-center justify-center gap-4">
          <button
            type="button"
            onClick={() => {
              setPage((p) => Math.max(1, p - 1));
              window.scrollTo({ top: 0, behavior: "smooth" });
            }}
            disabled={page <= 1}
            className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Previous
          </button>
          <span className="text-sm text-gray-600">
            Page {page} of {totalPages}
          </span>
          <button
            type="button"
            onClick={() => {
              setPage((p) => Math.min(totalPages, p + 1));
              window.scrollTo({ top: 0, behavior: "smooth" });
            }}
            disabled={page >= totalPages}
            className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Next
          </button>
        </div>
      )}
    </div>
  );
}
