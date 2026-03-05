"use client";

import { Search, X, ArrowRight } from "lucide-react";
import { ListStatusBar } from "./list-status-bar";

interface BrowseToolbarProps {
  activeFilter: string;
  onFilterChange: (filter: string) => void;
  search: string;
  onSearchChange: (value: string) => void;
  totalCount: number;
  page: number;
  totalPages: number;
  onPageChange: (page: number) => void;
  styles: string[];
  countries: string[];
  selectedStyles: string[];
  onToggleStyle: (style: string) => void;
  onClearStyles: () => void;
  selectedCountry: string | null;
  onSelectCountry: (country: string | null) => void;
  citiesForCountry: string[];
  selectedCity: string | null;
  onSelectCity: (city: string | null) => void;
}

export function BrowseToolbar({
  activeFilter,
  onFilterChange,
  search,
  onSearchChange,
  totalCount,
  page,
  totalPages,
  onPageChange,
  styles,
  countries,
  selectedStyles,
  onToggleStyle,
  onClearStyles,
  selectedCountry,
  onSelectCountry,
  citiesForCountry,
  selectedCity,
  onSelectCity,
}: BrowseToolbarProps) {
  return (
    <div className="sticky top-0 z-10 bg-background">
      <div className="border-b border-border px-4 md:px-8 h-9 flex items-center">
        <div className="relative flex items-center w-full">
          <Search className="absolute left-0 h-3.5 w-3.5 text-muted-foreground" />
          <input
            type="text"
            placeholder="Search artists, cities..."
            value={search}
            onChange={(e) => onSearchChange(e.target.value)}
            className="w-full bg-transparent py-0 pl-5 pr-5 text-xs text-foreground placeholder:text-muted-foreground focus:outline-none"
          />
          {search && (
            <button
              type="button"
              onClick={() => onSearchChange("")}
              className="absolute right-0 text-muted-foreground hover:text-foreground transition-colors"
            >
              <X className="h-3.5 w-3.5" />
            </button>
          )}
        </div>
      </div>

      <div className="flex items-center gap-2.5 px-4 md:px-8 h-9 border-b border-border">
        <span className="text-xs text-muted-foreground">Browse</span>
        <ArrowRight className="h-3 w-3 text-muted-foreground" />
        {["All", "Styles", "Countries"].map((filter) => (
          <button
            key={filter}
            type="button"
            onClick={() => onFilterChange(filter)}
            className={`text-xs px-2 py-0.5 transition-colors ${
              activeFilter === filter
                ? "bg-foreground text-background"
                : "text-foreground hover:text-muted-foreground"
            }`}
          >
            {filter}
          </button>
        ))}
      </div>

      {activeFilter === "Styles" && (
        <div className="border-b border-border px-4 md:px-8 py-2.5">
          <div className="flex items-start gap-2.5">
            <span className="text-xs text-muted-foreground shrink-0 pt-0.5">
              Styles:
            </span>
            <div className="flex flex-wrap gap-1">
              <button
                type="button"
                onClick={onClearStyles}
                className={`text-xs px-2 py-0.5 transition-colors ${
                  selectedStyles.length === 0
                    ? "bg-foreground text-background"
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >
                All
              </button>
              {styles.map((style) => (
                <button
                  key={style}
                  type="button"
                  onClick={() => onToggleStyle(style)}
                  className={`text-xs px-2 py-0.5 transition-colors ${
                    selectedStyles.includes(style)
                      ? "bg-foreground text-background"
                      : "text-muted-foreground hover:text-foreground"
                  }`}
                >
                  {style}
                </button>
              ))}
            </div>
          </div>
        </div>
      )}

      {activeFilter === "Countries" && (
        <div className="border-b border-border px-4 md:px-8 py-2.5">
          <div className="flex items-start gap-2.5">
            <span className="text-xs text-muted-foreground shrink-0 pt-0.5">
              Countries:
            </span>
            <div className="flex flex-wrap gap-1">
              <button
                type="button"
                onClick={() => onSelectCountry(null)}
                className={`text-xs px-2 py-0.5 transition-colors ${
                  selectedCountry === null
                    ? "bg-foreground text-background"
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >
                All
              </button>
              {countries.map((country) => (
                <button
                  key={country}
                  type="button"
                  onClick={() =>
                    onSelectCountry(country === selectedCountry ? null : country)
                  }
                  className={`text-xs px-2 py-0.5 transition-colors ${
                    selectedCountry === country
                      ? "bg-foreground text-background"
                      : "text-muted-foreground hover:text-foreground"
                  }`}
                >
                  {country}
                </button>
              ))}
            </div>
          </div>
        </div>
      )}

      {selectedCountry && citiesForCountry.length > 0 && (
        <div className="border-b border-border px-4 md:px-8 py-2.5">
          <div className="flex items-start gap-2.5">
            <span className="text-xs text-muted-foreground shrink-0 pt-0.5">
              Cities:
            </span>
            <div className="flex flex-wrap gap-1">
              <button
                type="button"
                onClick={() => onSelectCity(null)}
                className={`text-xs px-2 py-0.5 transition-colors ${
                  selectedCity === null
                    ? "bg-foreground text-background"
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >
                All
              </button>
              {citiesForCountry.map((city) => (
                <button
                  key={city}
                  type="button"
                  onClick={() =>
                    onSelectCity(city === selectedCity ? null : city)
                  }
                  className={`text-xs px-2 py-0.5 transition-colors ${
                    selectedCity === city
                      ? "bg-foreground text-background"
                      : "text-muted-foreground hover:text-foreground"
                  }`}
                >
                  {city}
                </button>
              ))}
            </div>
          </div>
        </div>
      )}

      <ListStatusBar
        totalCount={totalCount}
        page={page}
        totalPages={totalPages}
        onPageChange={onPageChange}
      />
    </div>
  );
}
