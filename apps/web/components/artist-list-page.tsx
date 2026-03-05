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
  const [selectedStyles, setSelectedStyles] = useState<string[]>([]);
  const [selectedCountry, setSelectedCountry] = useState<string | null>(null);
  const [selectedCity, setSelectedCity] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(0);

  const { allStyles, allCountries, citiesForCountry } = useMemo(() => {
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
    return {
      allStyles: Array.from(styleSet).sort(),
      allCountries: Array.from(countrySet).sort(),
      citiesForCountry: selectedCountry
        ? Array.from(cityByCountry.get(selectedCountry) ?? []).sort()
        : [],
    };
  }, [artists, selectedCountry]);

  const filteredArtists = useMemo(() => {
    let result = artists;

    if (selectedStyles.length > 0) {
      result = result.filter((a) =>
        selectedStyles.some((s) => a.styles.includes(s))
      );
    }

    if (selectedCountry) {
      result = result.filter((a) => a.location.country === selectedCountry);
    }

    if (selectedCity) {
      result = result.filter((a) => a.location.city === selectedCity);
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
  }, [artists, selectedStyles, selectedCountry, selectedCity, search]);

  useEffect(() => {
    setPage(0);
  }, [selectedStyles, selectedCountry, selectedCity, search]);

  const totalPages = Math.ceil(filteredArtists.length / PAGE_SIZE) || 1;
  const paginated = filteredArtists.slice(
    page * PAGE_SIZE,
    (page + 1) * PAGE_SIZE
  );
  const globalOffset = page * PAGE_SIZE;

  const handleFilterChange = (filter: string) => {
    setActiveFilter(filter);
    if (filter === "All") {
      setSelectedStyles([]);
      setSelectedCountry(null);
      setSelectedCity(null);
    }
  };

  const handleSelectCountry = (country: string | null) => {
    setSelectedCountry(country);
    setSelectedCity(null);
  };

  const handleCountryClick = (country: string) => {
    setActiveFilter("Countries");
    setSelectedCountry(country);
    setSelectedCity(null);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const handleCityClick = (city: string, country: string) => {
    setActiveFilter("Countries");
    setSelectedCountry(country);
    setSelectedCity(city);
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
    setSelectedCountry(null);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  return (
    <div className="min-h-screen flex flex-col bg-background text-foreground">
      <div className="h-8 md:h-16" />

      <BrowseToolbar
        activeFilter={activeFilter}
        onFilterChange={handleFilterChange}
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
        selectedCountry={selectedCountry}
        onSelectCountry={handleSelectCountry}
        citiesForCountry={citiesForCountry}
        selectedCity={selectedCity}
        onSelectCity={setSelectedCity}
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
