"use client";

import { useState, useMemo, useEffect, useCallback, useRef } from "react";
import { useSearchParams, usePathname, useRouter } from "next/navigation";
import type { CompactArtist } from "@/lib/data";
import { BrowseToolbar } from "./browse-toolbar";
import { ArtistList } from "./artist-list";
import { ListStatusBar } from "./list-status-bar";
import { SiteFooter } from "./site-footer";

const PAGE_SIZE = 20;
type SortKey = "name-asc";

function parseFiltersFromSearchParams(searchParams: URLSearchParams) {
  const q = searchParams.get("q") ?? "";
  const styles = searchParams.get("styles");
  const countries = searchParams.get("countries");
  const cities = searchParams.get("cities");
  const pageParam = searchParams.get("page");
  const page = pageParam
    ? Math.max(0, parseInt(pageParam, 10) - 1)
    : 0;
  return {
    search: q,
    selectedStyles: styles ? styles.split(",").map((s) => decodeURIComponent(s.trim())).filter(Boolean) : [],
    selectedCountries: countries ? countries.split(",").map((c) => decodeURIComponent(c.trim())).filter(Boolean) : [],
    selectedCities: cities ? cities.split(",").map((c) => decodeURIComponent(c.trim())).filter(Boolean) : [],
    page,
  };
}

function buildSearchString(parsed: {
  search: string;
  selectedStyles: string[];
  selectedCountries: string[];
  selectedCities: string[];
  page: number;
}) {
  const params = new URLSearchParams();
  if (parsed.search.trim()) params.set("q", parsed.search.trim());
  if (parsed.selectedStyles.length) params.set("styles", parsed.selectedStyles.map(encodeURIComponent).join(","));
  if (parsed.selectedCountries.length) params.set("countries", parsed.selectedCountries.map(encodeURIComponent).join(","));
  if (parsed.selectedCities.length) params.set("cities", parsed.selectedCities.map(encodeURIComponent).join(","));
  if (parsed.page > 0) params.set("page", String(parsed.page + 1));
  const qs = params.toString();
  return qs ? `?${qs}` : "";
}

interface ArtistListPageProps {
  /** Only these countries may appear in the filter dropdown (from countries.json). */
  allowedCountryNames?: string[];
}

export function ArtistListPage({
  allowedCountryNames = [],
}: ArtistListPageProps) {
  const [artists, setArtists] = useState<CompactArtist[]>([]);
  const [loadStatus, setLoadStatus] = useState<"loading" | "ready" | "error">(
    "loading"
  );
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await fetch("/api/artists/compact");
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = (await res.json()) as CompactArtist[];
        if (!cancelled) {
          setArtists(data);
          setLoadStatus("ready");
        }
      } catch (e) {
        if (!cancelled) {
          setLoadError(e instanceof Error ? e.message : "Failed to load artists");
          setLoadStatus("error");
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const searchParams = useSearchParams();
  const pathname = usePathname();
  const router = useRouter();

  const [activeFilter, setActiveFilter] = useState(() => {
    const p = parseFiltersFromSearchParams(searchParams);
    const hasFacets =
      p.selectedStyles.length > 0 ||
      p.selectedCountries.length > 0 ||
      p.selectedCities.length > 0;
    return hasFacets ? "" : "All";
  });
  const [isFilterPanelExpanded, setIsFilterPanelExpanded] = useState(false);
  const [selectedStyles, setSelectedStyles] = useState<string[]>(() =>
    parseFiltersFromSearchParams(searchParams).selectedStyles
  );
  const [selectedCountries, setSelectedCountries] = useState<string[]>(() =>
    parseFiltersFromSearchParams(searchParams).selectedCountries
  );
  const [selectedCities, setSelectedCities] = useState<string[]>(() =>
    parseFiltersFromSearchParams(searchParams).selectedCities
  );
  const [search, setSearch] = useState(() =>
    parseFiltersFromSearchParams(searchParams).search
  );
  const [page, setPage] = useState(() =>
    parseFiltersFromSearchParams(searchParams).page
  );
  const [sortKey, setSortKey] = useState<SortKey>("name-asc");

  // Restore filters from URL when navigating back/forward (sync state from URL)
  const prevParamsRef = useRef(searchParams.toString());
  useEffect(() => {
    const current = searchParams.toString();
    if (current !== prevParamsRef.current) {
      prevParamsRef.current = current;
      const parsed = parseFiltersFromSearchParams(searchParams);
      setSearch(parsed.search);
      setSelectedStyles(parsed.selectedStyles);
      setSelectedCountries(parsed.selectedCountries);
      setSelectedCities(parsed.selectedCities);
      setPage(parsed.page);
      const hasFacets =
        parsed.selectedStyles.length > 0 ||
        parsed.selectedCountries.length > 0 ||
        parsed.selectedCities.length > 0;
      setActiveFilter((prev) =>
        hasFacets && prev === "All" ? "" : prev
      );
    }
  }, [searchParams]);

  const updateUrl = useCallback(
    (updates: {
      search?: string;
      selectedStyles?: string[];
      selectedCountries?: string[];
      selectedCities?: string[];
      page?: number;
    }) => {
      const parsed = parseFiltersFromSearchParams(searchParams);
      const next = {
        search: updates.search ?? parsed.search,
        selectedStyles: updates.selectedStyles ?? parsed.selectedStyles,
        selectedCountries: updates.selectedCountries ?? parsed.selectedCountries,
        selectedCities: updates.selectedCities ?? parsed.selectedCities,
        page: updates.page ?? parsed.page,
      };
      const qs = buildSearchString(next);
      router.replace(`${pathname}${qs}`, { scroll: false });
    },
    [pathname, router, searchParams]
  );

  const allowedCountrySet = useMemo(
    () => new Set(allowedCountryNames.map((c) => c.trim().toLowerCase())),
    [allowedCountryNames]
  );

  const { allStyles, allCountries, citiesForSelectedCountries, citiesByCountry } =
    useMemo(() => {
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
      const rawCountries = Array.from(countrySet).sort();
      const allCountries =
        allowedCountrySet.size > 0
          ? rawCountries.filter((c) =>
              allowedCountrySet.has(c.trim().toLowerCase())
            )
          : rawCountries;
      // "Unknown" country is not a real geography — listing every city here is useless noise.
      const cities =
        selectedCountries.length > 0
          ? Array.from(
              new Set(
                selectedCountries.flatMap((c) =>
                  c === "Unknown"
                    ? []
                    : Array.from(cityByCountry.get(c) ?? [])
                )
              )
            ).sort()
          : [];
      const byCountry =
        selectedCountries.length > 0
          ? selectedCountries
              .map((country) => ({
                country,
                cities:
                  country === "Unknown"
                    ? []
                    : Array.from(cityByCountry.get(country) ?? []).sort(),
              }))
              .filter((x) => x.cities.length > 0)
          : [];
      return {
        allStyles: Array.from(styleSet).sort(),
        allCountries,
        citiesForSelectedCountries: cities,
        citiesByCountry: byCountry,
      };
    }, [artists, selectedCountries, allowedCountrySet]);

  // Drop city selections that are no longer valid for the chosen countries (e.g. switched to Unknown-only).
  useEffect(() => {
    setSelectedCities((prev) => {
      if (prev.length === 0) return prev;
      const valid = new Set(citiesForSelectedCountries);
      const next = prev.filter((c) => valid.has(c));
      return next.length === prev.length ? prev : next;
    });
  }, [citiesForSelectedCountries]);

  const citiesFilterEnabled = citiesForSelectedCountries.length > 0;

  useEffect(() => {
    if (activeFilter === "Cities" && !citiesFilterEnabled) {
      setActiveFilter("");
      setIsFilterPanelExpanded(false);
    }
  }, [activeFilter, citiesFilterEnabled]);

  const filteredArtists = useMemo(() => {
    let result = artists;

    if (selectedStyles.length > 0) {
      result = result.filter((a) =>
        selectedStyles.some((s) => a.styles.includes(s))
      );
    }

    if (selectedCountries.length > 0) {
      result = result.filter((a) =>
        selectedCountries.includes(a.location.country)
      );
    }

    if (selectedCities.length > 0) {
      result = result.filter((a) =>
        selectedCities.includes(a.location.city)
      );
    }

    if (search.trim()) {
      const q = search.toLowerCase().trim();
      result = result.filter(
        (a) =>
          a.name.toLowerCase().includes(q) ||
          a.location.city.toLowerCase().includes(q) ||
          a.location.country.toLowerCase().includes(q) ||
          a.styles.some((s) => s.toLowerCase().includes(q))
      );
    }

    if (sortKey === "name-asc") {
      return [...result].sort((a, b) =>
        a.name.localeCompare(b.name, undefined, { sensitivity: "base" })
      );
    }

    return result;
  }, [artists, selectedStyles, selectedCountries, selectedCities, search, sortKey]);

  // When filters actually change (not on mount, not when only page changed), reset to page 0 and sync URL.
  // Compare to last synced filter state so we don't overwrite URL after pagination or on Strict Mode double-invoke.
  const lastSyncedFiltersRef = useRef<string | null>(null);
  useEffect(() => {
    const filterKey = JSON.stringify({
      search,
      styles: selectedStyles,
      countries: selectedCountries,
      cities: selectedCities,
    });
    if (lastSyncedFiltersRef.current === null) {
      lastSyncedFiltersRef.current = filterKey;
      return;
    }
    if (lastSyncedFiltersRef.current === filterKey) return;
    lastSyncedFiltersRef.current = filterKey;
    setPage(0);
    updateUrl({
      search,
      selectedStyles,
      selectedCountries,
      selectedCities,
      page: 0,
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps -- only run when filter state changes
  }, [selectedStyles, selectedCountries, selectedCities, search]);

  const totalPages = Math.ceil(filteredArtists.length / PAGE_SIZE) || 1;
  const paginated = filteredArtists.slice(
    page * PAGE_SIZE,
    (page + 1) * PAGE_SIZE
  );
  const globalOffset = page * PAGE_SIZE;

  const handleFilterChange = (filter: string, keepSelections?: boolean) => {
    setActiveFilter(filter);
    if (filter === "Styles" || filter === "Countries" || filter === "Cities") {
      setIsFilterPanelExpanded(true);
    } else if (filter === "All") {
      setIsFilterPanelExpanded(false);
      if (!keepSelections) {
        setSelectedStyles([]);
        setSelectedCountries([]);
        setSelectedCities([]);
      }
    }
  };

  const handleCollapseFilterPanel = () => {
    setIsFilterPanelExpanded(false);
    setActiveFilter("");
  };

  const handleToggleCountry = (country: string) => {
    setSelectedCountries((prev) =>
      prev.includes(country) ? prev.filter((c) => c !== country) : [...prev, country]
    );
  };

  const handleClearCountries = () => {
    setSelectedCountries([]);
    setSelectedCities([]);
  };

  const handleToggleCity = (city: string) => {
    setSelectedCities((prev) =>
      prev.includes(city) ? prev.filter((c) => c !== city) : [...prev, city]
    );
  };

  const handleClearCities = () => {
    setSelectedCities([]);
  };

  const handleCountryClick = (country: string) => {
    setActiveFilter("Countries");
    setSelectedCountries((prev) =>
      prev.includes(country) ? prev.filter((c) => c !== country) : [...prev, country]
    );
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const handleCityClick = (city: string, _country: string) => {
    setActiveFilter("Cities");
    setSelectedCities((prev) =>
      prev.includes(city) ? prev.filter((c) => c !== city) : [...prev, city]
    );
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const handleToggleStyle = (style: string) => {
    setSelectedStyles((prev) =>
      prev.includes(style) ? prev.filter((s) => s !== style) : [...prev, style]
    );
  };

  const handleTagClick = (style: string) => {
    setActiveFilter("Styles");
    setSelectedStyles((prev) =>
      prev.includes(style) ? prev : [...prev, style]
    );
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  if (loadStatus === "loading") {
    return (
      <div className="flex flex-col items-center justify-center py-32 px-4 min-h-screen">
        <p className="text-muted-foreground">Loading…</p>
      </div>
    );
  }

  if (loadStatus === "error") {
    return (
      <div className="flex flex-col items-center justify-center py-32 px-4 min-h-screen">
        <p className="text-destructive">Could not load artists.</p>
        {loadError ? (
          <p className="text-sm text-muted-foreground mt-2">{loadError}</p>
        ) : null}
      </div>
    );
  }

  if (artists.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-32 px-4 min-h-screen">
        <p className="text-muted-foreground">No artists yet.</p>
        <p className="text-sm text-muted-foreground mt-2">
          Run the scraper pipeline to populate data.
        </p>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex flex-col bg-background text-foreground min-w-0">
      <div className="h-8 md:h-16" />

      <BrowseToolbar
        activeFilter={activeFilter}
        isFilterPanelExpanded={isFilterPanelExpanded}
        onFilterChange={handleFilterChange}
        onCollapseFilterPanel={handleCollapseFilterPanel}
        search={search}
        onSearchChange={(value) => {
          setSearch(value);
          setPage(0);
          updateUrl({ search: value, page: 0 });
        }}
        totalCount={filteredArtists.length}
        page={page}
        totalPages={totalPages}
        onPageChange={(p) => {
          setPage(p);
          updateUrl({ page: p });
        }}
        styles={allStyles}
        countries={allCountries}
        selectedStyles={selectedStyles}
        onToggleStyle={handleToggleStyle}
        onClearStyles={() => setSelectedStyles([])}
        selectedCountries={selectedCountries}
        onToggleCountry={handleToggleCountry}
        onClearCountries={handleClearCountries}
        citiesForSelectedCountries={citiesForSelectedCountries}
        citiesFilterEnabled={citiesFilterEnabled}
        citiesByCountry={citiesByCountry}
        selectedCities={selectedCities}
        onToggleCity={handleToggleCity}
        onClearCities={handleClearCities}
        sortLabel="Name (A–Z)"
        onSortChange={setSortKey}
      />

      <div className="flex-1 flex flex-col min-w-0 overflow-x-hidden">
        <main className="flex-1 min-w-0">
          <ArtistList
            artists={paginated}
            globalOffset={globalOffset}
            onTagClick={handleTagClick}
            onCountryClick={handleCountryClick}
            onCityClick={handleCityClick}
          />
          <ListStatusBar
            totalCount={filteredArtists.length}
            page={page}
            totalPages={totalPages}
            onPageChange={(p) => {
              setPage(p);
              updateUrl({ page: p });
            }}
            variant="bottom"
          />
        </main>

        <SiteFooter />
      </div>
    </div>
  );
}
