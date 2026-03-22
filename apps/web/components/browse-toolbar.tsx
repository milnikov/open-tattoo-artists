"use client";

import { Search, X, ArrowRight } from "lucide-react";
import { ListStatusBar } from "./list-status-bar";

interface BrowseToolbarProps {
  activeFilter: string;
  isFilterPanelExpanded: boolean;
  onFilterChange: (filter: string, keepSelections?: boolean) => void;
  onCollapseFilterPanel: () => void;
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
  selectedCountries: string[];
  onToggleCountry: (country: string) => void;
  onClearCountries: () => void;
  citiesForSelectedCountries: string[];
  citiesByCountry: { country: string; cities: string[] }[];
  selectedCities: string[];
  onToggleCity: (city: string) => void;
  onClearCities: () => void;
}

export function BrowseToolbar({
  activeFilter,
  isFilterPanelExpanded,
  onFilterChange,
  onCollapseFilterPanel,
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
  selectedCountries,
  onToggleCountry,
  onClearCountries,
  citiesForSelectedCountries,
  citiesByCountry,
  selectedCities,
  onToggleCity,
  onClearCities,
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
            className="w-full bg-transparent py-0 pl-5 pr-5 text-xs text-foreground placeholder:text-muted-foreground focus:outline-none rounded"
          />
          {search && (
            <button
              type="button"
              onClick={() => onSearchChange("")}
              className="absolute right-0 rounded text-muted-foreground hover:text-foreground transition-colors"
            >
              <X className="h-3.5 w-3.5" />
            </button>
          )}
        </div>
      </div>

      <div className="flex items-center gap-2 px-4 md:px-8 h-9 border-b border-border">
        <div className="flex items-center gap-1">
          <span className="text-xs text-muted-foreground">Browse</span>
          <ArrowRight className="h-3 w-3 text-muted-foreground" />
        </div>
        <button
          type="button"
          onClick={() => onFilterChange("All")}
          className={`text-xs px-2 py-1 rounded transition-colors ${
            activeFilter === "All"
              ? "bg-foreground text-background"
              : "text-foreground hover:text-muted-foreground"
          }`}
        >
          All
        </button>
        <button
          type="button"
          onClick={() => onFilterChange("Styles")}
          className={`text-xs px-2 py-1 rounded transition-colors ${
            activeFilter === "Styles"
              ? "bg-foreground text-background"
              : "text-foreground hover:text-muted-foreground"
          }`}
        >
          Styles{selectedStyles.length > 0 && (
            <sup className="ml-0.5">{selectedStyles.length}</sup>
          )}
        </button>
        <button
          type="button"
          onClick={() => onFilterChange("Countries")}
          className={`text-xs px-2 py-1 rounded transition-colors ${
            activeFilter === "Countries"
              ? "bg-foreground text-background"
              : "text-foreground hover:text-muted-foreground"
          }`}
        >
          Countries{selectedCountries.length > 0 && (
            <sup className="ml-0.5">{selectedCountries.length}</sup>
          )}
        </button>
        <button
          type="button"
          disabled={selectedCountries.length === 0}
          onClick={() => onFilterChange("Cities")}
          className={`text-xs px-2 py-1 rounded transition-colors ${
            selectedCountries.length === 0
              ? "text-muted-foreground cursor-not-allowed opacity-70 rounded"
              : activeFilter === "Cities"
                ? "bg-foreground text-background rounded"
                : "text-foreground hover:text-muted-foreground rounded"
          }`}
        >
          Cities{selectedCities.length > 0 && (
            <sup className="ml-0.5">{selectedCities.length}</sup>
          )}
        </button>
      </div>

      {activeFilter === "Styles" && isFilterPanelExpanded && (
        <div className="border-b border-border px-4 md:px-8 py-2.5">
          <div className="h-[50vh] md:h-auto md:max-h-[60vh] overflow-y-auto overscroll-contain">
            <div className="flex flex-wrap gap-1 content-start">
            <button
              type="button"
              onClick={onClearStyles}
              className={`text-xs px-2 py-1 rounded transition-colors ${
                selectedStyles.length === 0
                  ? "bg-foreground text-background"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              All styles
            </button>
            {styles.map((style) => (
              <button
                key={style}
                type="button"
                onClick={() => onToggleStyle(style)}
                className={`text-xs px-2 py-1 rounded transition-colors ${
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
          <div className="flex justify-end mt-2">
            <button
              type="button"
              onClick={onCollapseFilterPanel}
              className="text-xs px-3 py-1 rounded bg-foreground text-background hover:opacity-90 transition-opacity"
            >
              Save
            </button>
          </div>
        </div>
      )}

      {activeFilter === "Countries" && isFilterPanelExpanded && (
        <div className="border-b border-border px-4 md:px-8 py-2.5">
          <div className="h-[50vh] md:h-auto md:max-h-[60vh] overflow-y-auto overscroll-contain">
            <div className="flex flex-wrap gap-1 content-start">
            <button
              type="button"
              onClick={onClearCountries}
              className={`text-xs px-2 py-1 rounded transition-colors ${
                selectedCountries.length === 0
                  ? "bg-foreground text-background"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              All countries
            </button>
            {countries.map((country) => (
              <button
                key={country}
                type="button"
                onClick={() => onToggleCountry(country)}
                className={`text-xs px-2 py-1 rounded transition-colors ${
                  selectedCountries.includes(country)
                    ? "bg-foreground text-background"
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >
                {country}
              </button>
            ))}
            </div>
          </div>
          <div className="flex justify-end mt-2">
            <button
              type="button"
              onClick={onCollapseFilterPanel}
              className="text-xs px-3 py-1 rounded bg-foreground text-background hover:opacity-90 transition-opacity"
            >
              Save
            </button>
          </div>
        </div>
      )}

      {activeFilter === "Cities" &&
        isFilterPanelExpanded &&
        selectedCountries.length > 0 && (
          <div className="border-b border-border px-4 md:px-8 py-2.5">
            <div className="h-[50vh] md:h-auto md:max-h-[60vh] overflow-y-auto overscroll-contain">
              <div className="flex flex-wrap gap-x-2 gap-y-1.5 items-baseline content-start">
              <button
                type="button"
                onClick={onClearCities}
                className={`text-xs px-2 py-1 rounded transition-colors ${
                  selectedCities.length === 0
                    ? "bg-foreground text-background"
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >
                All cities
              </button>
              {selectedCountries.length > 1 ? (
                citiesByCountry.map(({ country, cities }) => (
                  <div
                    key={country}
                    className="flex flex-wrap gap-1 items-center gap-y-0.5"
                  >
                    <span className="text-xs text-muted-foreground px-2 italic">
                      {country}:
                    </span>
                    {cities.map((city) => (
                      <button
                        key={city}
                        type="button"
                        onClick={() => onToggleCity(city)}
                        className={`text-xs px-2 py-1 rounded transition-colors ${
                          selectedCities.includes(city)
                            ? "bg-foreground text-background"
                            : "text-muted-foreground hover:text-foreground"
                        }`}
                      >
                        {city}
                      </button>
                    ))}
                  </div>
                ))
              ) : (
                citiesForSelectedCountries.map((city) => (
                  <button
                    key={city}
                    type="button"
                    onClick={() => onToggleCity(city)}
                    className={`text-xs px-2 py-1 rounded transition-colors ${
                      selectedCities.includes(city)
                        ? "bg-foreground text-background"
                        : "text-muted-foreground hover:text-foreground"
                    }`}
                  >
                    {city}
                  </button>
                ))
              )}
              </div>
            </div>
            <div className="flex justify-end mt-2">
              <button
                type="button"
                onClick={onCollapseFilterPanel}
                className="text-xs px-3 py-1 rounded bg-foreground text-background hover:opacity-90 transition-opacity"
              >
                Save
              </button>
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
