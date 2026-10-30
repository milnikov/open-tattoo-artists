"use client";

import { useState, useMemo, useEffect, useCallback, useRef, startTransition } from "react";
import { useSearchParams, usePathname, useRouter } from "next/navigation";
import type { CompactArtist } from "@/lib/data";
import {
  DIRECTORY_PAGE_SIZE,
  countriesForDirectory,
  sortArtists,
  stylesForDirectory,
  type DirectorySortKey,
} from "@/lib/directory-query";
import { BrowseToolbar } from "./browse-toolbar";
import { ArtistList } from "./artist-list";
import { ListStatusBar } from "./list-status-bar";
import { SiteFooter } from "./site-footer";

const PAGE_SIZE = DIRECTORY_PAGE_SIZE;
type SortKey = DirectorySortKey;

function sortLabelFor(sortKey: SortKey): string {
  if (sortKey === "followers-desc") return "Most followed";
  if (sortKey === "respected-desc") return "Most respected";
  return "Name (A–Z)";
}

function normalizeSortKey(value: string | null | undefined): SortKey {
  if (value === "followers-desc") return "followers-desc";
  if (value === "respected-desc") return "respected-desc";
  return "name-asc";
}
function parseFiltersFromSearchParams(searchParams: URLSearchParams) {
  const q = searchParams.get("q") ?? "";
  const styles = searchParams.get("styles");
  const countries = searchParams.get("countries");
  const cities = searchParams.get("cities");
  const sort = normalizeSortKey(searchParams.get("sort"));
  const pageParam = searchParams.get("page");
  const page = pageParam
    ? Math.max(0, parseInt(pageParam, 10) - 1)
    : 0;
  return {
    search: q,
    selectedStyles: styles ? styles.split(",").map((s) => decodeURIComponent(s.trim())).filter(Boolean) : [],
    selectedCountries: countries ? countries.split(",").map((c) => decodeURIComponent(c.trim())).filter(Boolean) : [],
    selectedCities: cities ? cities.split(",").map((c) => decodeURIComponent(c.trim())).filter(Boolean) : [],
    sort,
    page,
  };
}

function buildSearchString(parsed: {
  search: string;
  selectedStyles: string[];
  selectedCountries: string[];
  selectedCities: string[];
  sort: SortKey;
  page: number;
}) {
  const params = new URLSearchParams();
  if (parsed.search.trim()) params.set("q", parsed.search.trim());
  if (parsed.selectedStyles.length) params.set("styles", parsed.selectedStyles.map(encodeURIComponent).join(","));
  if (parsed.selectedCountries.length) params.set("countries", parsed.selectedCountries.map(encodeURIComponent).join(","));
  if (parsed.selectedCities.length) params.set("cities", parsed.selectedCities.map(encodeURIComponent).join(","));
  if (parsed.sort !== "name-asc") params.set("sort", parsed.sort);
  if (parsed.page > 0) params.set("page", String(parsed.page + 1));
  const qs = params.toString();
  return qs ? `?${qs}` : "";
}

interface ArtistListPageProps {
  /** Only these countries may appear in the filter dropdown (from countries.json). */
  allowedCountryNames?: string[];
  /** Default first page, painted before the full catalog arrives. */
  initialArtists?: CompactArtist[];
  initialTotalCount?: number;
  facetStyles?: string[];
  facetCountries?: string[];
}

export function ArtistListPage({
  allowedCountryNames = [],
  initialArtists = [],
  initialTotalCount = 0,
  facetStyles = [],
  facetCountries = [],
}: ArtistListPageProps) {
  const [catalog, setCatalog] = useState<CompactArtist[] | null>(null);
  const [loadStatus, setLoadStatus] = useState<"loading" | "ready" | "error">(
    "loading"
  );
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        // Low priority so the first-page photos can use the connection first.
        const res = await fetch("/api/artists/compact", { priority: "low" });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = (await res.json()) as CompactArtist[];
        if (!cancelled) {
          startTransition(() => {
            setCatalog(data);
            setLoadStatus("ready");
          });
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
  const [sortKey, setSortKey] = useState<SortKey>(() =>
    parseFiltersFromSearchParams(searchParams).sort
  );

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
      setSortKey(parsed.sort);
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
      sort?: SortKey;
      page?: number;
    }) => {
      const parsed = parseFiltersFromSearchParams(searchParams);
      const next = {
        search: updates.search ?? parsed.search,
        selectedStyles: updates.selectedStyles ?? parsed.selectedStyles,
        selectedCountries: updates.selectedCountries ?? parsed.selectedCountries,
        selectedCities: updates.selectedCities ?? parsed.selectedCities,
        sort: updates.sort ?? parsed.sort,
        page: updates.page ?? parsed.page,
      };
      const qs = buildSearchString(next);
      router.replace(`${pathname}${qs}`, { scroll: false });
    },
    [pathname, router, searchParams]
  );

  const { allStyles, allCountries, citiesForSelectedCountries, citiesByCountry } =
    useMemo(() => {
      const source = catalog ?? [];
      const cityByCountry = new Map<string, Set<string>>();
      for (const a of source) {
        const c = a.location.country;
        if (!cityByCountry.has(c)) cityByCountry.set(c, new Set());
        cityByCountry.get(c)!.add(a.location.city);
      }
      const allCountries = countriesForDirectory(source, allowedCountryNames);
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
        allStyles: stylesForDirectory(source),
        allCountries,
        citiesForSelectedCountries: cities,
        citiesByCountry: byCountry,
      };
    }, [catalog, selectedCountries, allowedCountryNames]);

  // Drop city selections that are no longer valid for the chosen countries (e.g. switched to Unknown-only).
  // Wait until the full catalog is in memory — an empty city list while it downloads would wipe the URL selection.
  useEffect(() => {
    if (!catalog) return;
    setSelectedCities((prev) => {
      if (prev.length === 0) return prev;
      const valid = new Set(citiesForSelectedCountries);
      const next = prev.filter((c) => valid.has(c));
      return next.length === prev.length ? prev : next;
    });
  }, [catalog, citiesForSelectedCountries]);

  const citiesFilterEnabled = citiesForSelectedCountries.length > 0;

  useEffect(() => {
    if (activeFilter === "Cities" && !citiesFilterEnabled) {
      setActiveFilter("");
      setIsFilterPanelExpanded(false);
    }
  }, [activeFilter, citiesFilterEnabled]);

  const filteredArtists = useMemo(() => {
    let result = catalog ?? [];

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

    return sortArtists(result, sortKey);
  }, [catalog, selectedStyles, selectedCountries, selectedCities, search, sortKey]);

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

  const catalogReady = catalog !== null;
  const queryAffectsResults =
    selectedStyles.length > 0 ||
    selectedCountries.length > 0 ||
    selectedCities.length > 0 ||
    search.trim() !== "" ||
    sortKey !== "name-asc";
  const countPending = !catalogReady && queryAffectsResults;
  const totalCount = catalogReady
    ? filteredArtists.length
    : queryAffectsResults
      ? 0
      : initialTotalCount;
  const totalPages = catalogReady
    ? Math.ceil(filteredArtists.length / PAGE_SIZE) || 1
    : queryAffectsResults
      ? 1
      : Math.ceil(initialTotalCount / PAGE_SIZE) || 1;
  const showingPreview =
    !catalogReady &&
    !queryAffectsResults &&
    page === 0 &&
    initialArtists.length > 0;
  const pageArtists = catalogReady
    ? filteredArtists.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE)
    : initialArtists;
  const globalOffset = catalogReady ? page * PAGE_SIZE : 0;
  const listMode: "artists" | "loading" | "error" =
    showingPreview || catalogReady
      ? "artists"
      : loadStatus === "error"
        ? "error"
        : "loading";
  const toolbarStyles = catalogReady ? allStyles : facetStyles;
  const toolbarCountries = catalogReady ? allCountries : facetCountries;

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

  if (loadStatus === "error" && initialArtists.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-32 px-4 min-h-screen">
        <p className="text-destructive">Could not load artists.</p>
        {loadError ? (
          <p className="text-sm text-muted-foreground mt-2">{loadError}</p>
        ) : null}
      </div>
    );
  }

  if (catalog && catalog.length === 0) {
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
    <DirectoryScreen
      artists={pageArtists}
      globalOffset={globalOffset}
      listMode={listMode}
      loadError={loadError}
      totalCount={totalCount}
      page={page}
      totalPages={totalPages}
      countPending={countPending}
      onPageChange={(p) => {
        setPage(p);
        updateUrl({ page: p });
      }}
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
      styles={toolbarStyles}
      countries={toolbarCountries}
      selectedStyles={selectedStyles}
      onToggleStyle={handleToggleStyle}
      onClearStyles={() => setSelectedStyles([])}
      selectedCountries={selectedCountries}
      onToggleCountry={handleToggleCountry}
      onClearCountries={handleClearCountries}
      citiesForSelectedCountries={catalogReady ? citiesForSelectedCountries : []}
      citiesFilterEnabled={catalogReady && citiesFilterEnabled}
      citiesByCountry={catalogReady ? citiesByCountry : []}
      selectedCities={selectedCities}
      onToggleCity={handleToggleCity}
      onClearCities={handleClearCities}
      sortLabel={sortLabelFor(sortKey)}
      onSortChange={(key) => {
        setSortKey(key);
        setPage(0);
        updateUrl({ sort: key, page: 0 });
      }}
      onTagClick={handleTagClick}
      onCountryClick={handleCountryClick}
      onCityClick={handleCityClick}
    />
  );
}

function noop() {}
function noopString(_value: string) {}
function noopPage(_page: number) {}
function noopSort(_sortKey: SortKey) {}
function noopFilter(_filter: string, _keepSelections?: boolean) {}

/** Static first paint: toolbar, names, and image slots before the catalog request finishes. */
export function ArtistDirectoryFallback({
  artists,
  totalCount,
  styles,
  countries,
}: {
  artists: CompactArtist[];
  totalCount: number;
  styles: string[];
  countries: string[];
}) {
  const totalPages = Math.max(1, Math.ceil(totalCount / PAGE_SIZE));
  return (
    <DirectoryScreen
      artists={artists}
      globalOffset={0}
      listMode="artists"
      loadError={null}
      totalCount={totalCount}
      page={0}
      totalPages={totalPages}
      onPageChange={noopPage}
      activeFilter="All"
      isFilterPanelExpanded={false}
      onFilterChange={noopFilter}
      onCollapseFilterPanel={noop}
      search=""
      onSearchChange={noopString}
      styles={styles}
      countries={countries}
      selectedStyles={[]}
      onToggleStyle={noopString}
      onClearStyles={noop}
      selectedCountries={[]}
      onToggleCountry={noopString}
      onClearCountries={noop}
      citiesForSelectedCountries={[]}
      citiesFilterEnabled={false}
      citiesByCountry={[]}
      selectedCities={[]}
      onToggleCity={noopString}
      onClearCities={noop}
      sortLabel="Name (A–Z)"
      onSortChange={noopSort}
    />
  );
}

function DirectoryScreen({
  artists,
  globalOffset,
  listMode,
  loadError,
  totalCount,
  page,
  totalPages,
  countPending = false,
  onPageChange,
  activeFilter,
  isFilterPanelExpanded,
  onFilterChange,
  onCollapseFilterPanel,
  search,
  onSearchChange,
  styles,
  countries,
  selectedStyles,
  onToggleStyle,
  onClearStyles,
  selectedCountries,
  onToggleCountry,
  onClearCountries,
  citiesForSelectedCountries,
  citiesFilterEnabled,
  citiesByCountry,
  selectedCities,
  onToggleCity,
  onClearCities,
  sortLabel,
  onSortChange,
  onTagClick,
  onCountryClick,
  onCityClick,
}: {
  artists: CompactArtist[];
  globalOffset: number;
  listMode: "artists" | "loading" | "error";
  loadError: string | null;
  totalCount: number;
  page: number;
  totalPages: number;
  countPending?: boolean;
  onPageChange: (page: number) => void;
  activeFilter: string;
  isFilterPanelExpanded: boolean;
  onFilterChange: (filter: string, keepSelections?: boolean) => void;
  onCollapseFilterPanel: () => void;
  search: string;
  onSearchChange: (value: string) => void;
  styles: string[];
  countries: string[];
  selectedStyles: string[];
  onToggleStyle: (style: string) => void;
  onClearStyles: () => void;
  selectedCountries: string[];
  onToggleCountry: (country: string) => void;
  onClearCountries: () => void;
  citiesForSelectedCountries: string[];
  citiesFilterEnabled: boolean;
  citiesByCountry: { country: string; cities: string[] }[];
  selectedCities: string[];
  onToggleCity: (city: string) => void;
  onClearCities: () => void;
  sortLabel: string;
  onSortChange: (sortKey: SortKey) => void;
  onTagClick?: (style: string) => void;
  onCountryClick?: (country: string) => void;
  onCityClick?: (city: string, country: string) => void;
}) {
  return (
    <div className="min-h-screen flex flex-col bg-background text-foreground min-w-0 overflow-x-hidden">
      <div className="h-8 md:h-16" />

      <BrowseToolbar
        activeFilter={activeFilter}
        isFilterPanelExpanded={isFilterPanelExpanded}
        onFilterChange={onFilterChange}
        onCollapseFilterPanel={onCollapseFilterPanel}
        search={search}
        onSearchChange={onSearchChange}
        totalCount={totalCount}
        page={page}
        totalPages={totalPages}
        onPageChange={onPageChange}
        styles={styles}
        countries={countries}
        selectedStyles={selectedStyles}
        onToggleStyle={onToggleStyle}
        onClearStyles={onClearStyles}
        selectedCountries={selectedCountries}
        onToggleCountry={onToggleCountry}
        onClearCountries={onClearCountries}
        citiesForSelectedCountries={citiesForSelectedCountries}
        citiesFilterEnabled={citiesFilterEnabled}
        citiesByCountry={citiesByCountry}
        selectedCities={selectedCities}
        onToggleCity={onToggleCity}
        onClearCities={onClearCities}
        sortLabel={sortLabel}
        onSortChange={onSortChange}
        countPending={countPending}
      />

      <div className="flex-1 flex flex-col min-w-0 overflow-x-hidden">
        <main className="flex-1 min-w-0">
          {listMode === "loading" ? (
            <div className="flex flex-col items-center justify-center py-32 px-4">
              <p className="text-muted-foreground">Loading artists…</p>
            </div>
          ) : listMode === "error" ? (
            <div className="flex flex-col items-center justify-center py-32 px-4">
              <p className="text-destructive">Could not load artists.</p>
              {loadError ? (
                <p className="text-sm text-muted-foreground mt-2">{loadError}</p>
              ) : null}
            </div>
          ) : (
            <ArtistList
              artists={artists}
              globalOffset={globalOffset}
              onTagClick={onTagClick}
              onCountryClick={onCountryClick}
              onCityClick={onCityClick}
            />
          )}
          <ListStatusBar
            totalCount={totalCount}
            page={page}
            totalPages={totalPages}
            onPageChange={onPageChange}
            variant="bottom"
            countPending={countPending}
          />
        </main>

        <SiteFooter />
      </div>
    </div>
  );
}
