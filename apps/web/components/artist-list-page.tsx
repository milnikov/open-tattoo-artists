"use client";

import { useState, useMemo, useEffect } from "react";
import type { CompactArtist } from "@/lib/data";
import { BrowseToolbar } from "./browse-toolbar";
import { ArtistList } from "./artist-list";
import { ListStatusBar } from "./list-status-bar";
import { SiteFooter } from "./site-footer";

const PAGE_SIZE = 20;

interface ArtistListPageProps {
  artists: CompactArtist[];
}

export function ArtistListPage({ artists }: ArtistListPageProps) {
  const [activeFilter, setActiveFilter] = useState("All");
  const [isFilterPanelExpanded, setIsFilterPanelExpanded] = useState(false);
  const [selectedStyles, setSelectedStyles] = useState<string[]>([]);
  const [selectedCountries, setSelectedCountries] = useState<string[]>([]);
  const [selectedCities, setSelectedCities] = useState<string[]>([]);
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(0);

  const { allStyles, allCountries, citiesForSelectedCountries } = useMemo(() => {
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
    const cities =
      selectedCountries.length > 0
        ? Array.from(
            new Set(
              selectedCountries.flatMap((c) =>
                Array.from(cityByCountry.get(c) ?? [])
              )
            )
          ).sort()
        : [];
    return {
      allStyles: Array.from(styleSet).sort(),
      allCountries: Array.from(countrySet).sort(),
      citiesForSelectedCountries: cities,
    };
  }, [artists, selectedCountries]);

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

    return result;
  }, [artists, selectedStyles, selectedCountries, selectedCities, search]);

  useEffect(() => {
    setPage(0);
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

  return (
    <div className="min-h-screen flex flex-col bg-background text-foreground">
      <div className="h-8 md:h-16" />

      <BrowseToolbar
        activeFilter={activeFilter}
        isFilterPanelExpanded={isFilterPanelExpanded}
        onFilterChange={handleFilterChange}
        onCollapseFilterPanel={handleCollapseFilterPanel}
        search={search}
        onSearchChange={setSearch}
        totalCount={filteredArtists.length}
        page={page}
        totalPages={totalPages}
        onPageChange={setPage}
        styles={allStyles}
        countries={allCountries}
        selectedStyles={selectedStyles}
        onToggleStyle={handleToggleStyle}
        onClearStyles={() => setSelectedStyles([])}
        selectedCountries={selectedCountries}
        onToggleCountry={handleToggleCountry}
        onClearCountries={handleClearCountries}
        citiesForSelectedCountries={citiesForSelectedCountries}
        selectedCities={selectedCities}
        onToggleCity={handleToggleCity}
        onClearCities={handleClearCities}
      />

      <main className="flex-1">
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
          onPageChange={setPage}
          variant="bottom"
        />
      </main>

      <SiteFooter />
    </div>
  );
}
