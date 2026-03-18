"use client";

import { useMemo, useState } from "react";
import type { CompactArtist } from "@/lib/data";
import { imageUrl } from "@/lib/images";

type AdminTab = "artists" | "tattoos";

type AdminArtistAction = "not-artist" | "studio";

type FlattenedTattoo = {
  artistId: string;
  artistName: string;
  imageId: string;
  imageThumb: string;
  imageFull: string;
  country: string;
  city: string;
  styles: string[];
  sourceDomain: string;
};

interface AdminPageClientProps {
  artists: CompactArtist[];
  tattoos: FlattenedTattoo[];
}

const ARTISTS_PAGE_SIZE = 60;
const TATTOOS_PAGE_SIZE = 60;

export function AdminPageClient({ artists, tattoos }: AdminPageClientProps) {
  const [tab, setTab] = useState<AdminTab>("artists");

  const [styleFilter, setStyleFilter] = useState("");
  const [countryFilter, setCountryFilter] = useState("");
  const [cityFilter, setCityFilter] = useState("");
  const [sourceFilter, setSourceFilter] = useState("");

  const [artistPage, setArtistPage] = useState(0);
  const [tattooPage, setTattooPage] = useState(0);

  const [hiddenArtistIds, setHiddenArtistIds] = useState<Set<string>>(
    () => new Set()
  );
  const [hiddenTattooKeys, setHiddenTattooKeys] = useState<Set<string>>(
    () => new Set()
  );

  const [markdownLog, setMarkdownLog] = useState<string>("# Admin session log\n\n");

  const { styles, countries, citiesInCountry, sources } = useMemo(() => {
    const styleSet = new Set<string>();
    const countrySet = new Set<string>();
    const cityByCountry = new Map<string, Set<string>>();
    const sourceSet = new Set<string>();
    for (const a of artists) {
      for (const s of a.styles) styleSet.add(s);
      const c = a.location.country;
      countrySet.add(c);
      if (!cityByCountry.has(c)) cityByCountry.set(c, new Set());
      cityByCountry.get(c)!.add(a.location.city);
      if (a.source_domain) sourceSet.add(a.source_domain);
    }
    const styles = Array.from(styleSet).sort();
    const countries = Array.from(countrySet).sort();
    const citiesInCountry = countryFilter
      ? Array.from(cityByCountry.get(countryFilter) ?? []).sort()
      : [];
    const sources = Array.from(sourceSet).sort();
    return { styles, countries, citiesInCountry, sources };
  }, [artists, countryFilter]);

  const filteredArtists = useMemo(() => {
    return artists.filter((a) => {
      if (a.verified) return false;
      if (hiddenArtistIds.has(a.id)) return false;
      if (styleFilter && !a.styles.includes(styleFilter)) return false;
      if (countryFilter && a.location.country !== countryFilter) return false;
      if (cityFilter && a.location.city !== cityFilter) return false;
      if (sourceFilter && (a.source_domain ?? "unknown") !== sourceFilter) return false;
      return true;
    });
  }, [artists, hiddenArtistIds, styleFilter, countryFilter, cityFilter, sourceFilter]);

  const artistTotalPages = Math.max(
    1,
    Math.ceil(filteredArtists.length / ARTISTS_PAGE_SIZE)
  );
  const paginatedArtists = useMemo(
    () =>
      filteredArtists.slice(
        artistPage * ARTISTS_PAGE_SIZE,
        (artistPage + 1) * ARTISTS_PAGE_SIZE
      ),
    [filteredArtists, artistPage]
  );

  const allTattoos: FlattenedTattoo[] = useMemo(() => {
    return tattoos.filter((t) => {
      if (hiddenTattooKeys.has(`${t.artistId}:${t.imageId}`)) return false;
      if (styleFilter && !t.styles.includes(styleFilter)) return false;
      if (countryFilter && t.country !== countryFilter) return false;
      if (cityFilter && t.city !== cityFilter) return false;
      if (sourceFilter && t.sourceDomain !== sourceFilter) return false;
      return true;
    });
  }, [tattoos, hiddenTattooKeys, styleFilter, countryFilter, cityFilter, sourceFilter]);

  const tattooTotalPages = Math.max(
    1,
    Math.ceil(allTattoos.length / TATTOOS_PAGE_SIZE)
  );
  const paginatedTattoos = useMemo(
    () =>
      allTattoos.slice(
        tattooPage * TATTOOS_PAGE_SIZE,
        (tattooPage + 1) * TATTOOS_PAGE_SIZE
      ),
    [allTattoos, tattooPage]
  );

  function appendLog(line: string) {
    setMarkdownLog((prev) => prev + line + "\n");
  }

  function handleArtistAction(artist: CompactArtist, action: AdminArtistAction) {
    setHiddenArtistIds((prev) => new Set(prev).add(artist.id));
    if (action === "not-artist") {
      appendLog(
        `- Artist \`${artist.id}\` (${artist.name}) marked as **Not artist**.`
      );
    } else if (action === "studio") {
      appendLog(
        `- Artist \`${artist.id}\` (${artist.name}) marked as **Studio** (should be hidden as studio).`
      );
    }
  }

  function handleTattooDelete(t: FlattenedTattoo) {
    const key = `${t.artistId}:${t.imageId}`;
    setHiddenTattooKeys((prev) => new Set(prev).add(key));
    appendLog(
      `- Tattoo image \`${t.imageId}\` of artist \`${t.artistId}\` (${t.artistName}) marked for **deletion**. Full: ${t.imageFull}, Thumb: ${t.imageThumb}`
    );
  }

  function downloadMarkdown() {
    const blob = new Blob([markdownLog], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "admin-session.md";
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="min-h-screen flex flex-col bg-background text-foreground min-w-0">
      <div className="h-8 md:h-16" />

      <main className="flex-1 min-w-0 overflow-x-hidden px-4 md:px-8 py-4 flex flex-col gap-4">
        <div className="flex items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setTab("artists")}
              className={`text-xs px-3 py-1.5 rounded ${
                tab === "artists"
                  ? "bg-foreground text-background"
                  : "border border-border text-foreground hover:bg-secondary"
              }`}
            >
              Artists
            </button>
            <button
              type="button"
              onClick={() => setTab("tattoos")}
              className={`text-xs px-3 py-1.5 rounded ${
                tab === "tattoos"
                  ? "bg-foreground text-background"
                  : "border border-border text-foreground hover:bg-secondary"
              }`}
            >
              Tattoos
            </button>
          </div>
          <button
            type="button"
            onClick={downloadMarkdown}
            className="text-xs rounded border border-border px-3 py-1 text-foreground hover:bg-secondary transition-colors"
          >
            Download session log
          </button>
        </div>

        <div className="flex flex-col md:flex-row gap-4 items-start">
          <div className="flex-1 min-w-0">
            <div className="flex flex-wrap items-center gap-3 mb-4">
              <label className="flex items-center gap-2 text-xs">
                <span className="text-muted-foreground">Style</span>
                <select
                  value={styleFilter}
                  onChange={(e) => {
                    setStyleFilter(e.target.value);
                    setArtistPage(0);
                    setTattooPage(0);
                  }}
                  className="rounded border border-border bg-background px-2 py-1 text-xs"
                >
                  <option value="">All</option>
                  {styles.map((s) => (
                    <option key={s} value={s}>
                      {s}
                    </option>
                  ))}
                </select>
              </label>
              <label className="flex items-center gap-2 text-xs">
                <span className="text-muted-foreground">Country</span>
                <select
                  value={countryFilter}
                  onChange={(e) => {
                    setCountryFilter(e.target.value);
                    setCityFilter("");
                    setArtistPage(0);
                    setTattooPage(0);
                  }}
                  className="rounded border border-border bg-background px-2 py-1 text-xs"
                >
                  <option value="">All</option>
                  {countries.map((c) => (
                    <option key={c} value={c}>
                      {c}
                    </option>
                  ))}
                </select>
              </label>
              <label className="flex items-center gap-2 text-xs">
                <span className="text-muted-foreground">City</span>
                <select
                  value={cityFilter}
                  onChange={(e) => {
                    setCityFilter(e.target.value);
                    setArtistPage(0);
                    setTattooPage(0);
                  }}
                  disabled={!countryFilter}
                  className="rounded border border-border bg-background px-2 py-1 text-xs"
                >
                  <option value="">All</option>
                  {citiesInCountry.map((city) => (
                    <option key={city} value={city}>
                      {city}
                    </option>
                  ))}
                </select>
              </label>
              <label className="flex items-center gap-2 text-xs">
                <span className="text-muted-foreground">Source</span>
                <select
                  value={sourceFilter}
                  onChange={(e) => {
                    setSourceFilter(e.target.value);
                    setArtistPage(0);
                    setTattooPage(0);
                  }}
                  className="rounded border border-border bg-background px-2 py-1 text-xs"
                >
                  <option value="">All</option>
                  {sources.map((s) => (
                    <option key={s} value={s}>
                      {s}
                    </option>
                  ))}
                </select>
              </label>
              <span className="text-xs text-muted-foreground">
                {tab === "artists"
                  ? `${filteredArtists.length} artists to check`
                  : `${allTattoos.length} tattoos`}
              </span>
            </div>

            {tab === "artists" && (
            <div className="flex flex-col gap-3">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {paginatedArtists.map((a) => {
                    const thumbs =
                      (a.thumbs && a.thumbs.length > 0
                        ? a.thumbs
                        : a.thumb
                        ? [a.thumb]
                        : []
                      ).slice(0, 3);
                    return (
                      <div
                        key={a.id}
                        className="relative group border border-border rounded-md overflow-hidden bg-card"
                      >
                        <div className="aspect-[4/3] bg-muted overflow-hidden">
                          {thumbs.length > 0 ? (
                            <div className="w-full h-full grid grid-cols-3 gap-px bg-background/40">
                              {thumbs.map((t, idx) => (
                                <div key={idx} className="relative bg-muted overflow-hidden">
                                  <img
                                    src={imageUrl(t)}
                                    alt={a.name}
                                    className="w-full h-full object-cover"
                                  />
                                </div>
                              ))}
                            </div>
                          ) : (
                            <div className="w-full h-full flex items-center justify-center text-[11px] text-muted-foreground">
                              {a.tattoo_count > 0
                                ? `${a.tattoo_count} images`
                                : "No image"}
                            </div>
                          )}
                        </div>
                      <div className="p-2">
                        <div className="text-xs font-semibold truncate">
                          {a.name}
                        </div>
                        <div className="text-[11px] text-muted-foreground truncate">
                          {a.location.city}, {a.location.country}
                        </div>
                        {a.styles.length > 0 && (
                          <div className="mt-0.5 text-[11px] text-muted-foreground truncate">
                            {a.styles.slice(0, 3).join(", ")}
                          </div>
                        )}
                      </div>
                        <div className="absolute inset-0 bg-black/45 opacity-0 group-hover:opacity-100 transition-opacity flex flex-col items-center justify-center gap-2 px-2">
                          <div className="flex flex-wrap items-center justify-center gap-2">
                            <a
                              href={`/artists/${a.id}`}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-[11px] px-2 py-1 rounded bg-slate-800 text-white hover:bg-slate-700"
                            >
                              Open
                            </a>
                            <button
                              type="button"
                              onClick={() => {
                                setHiddenArtistIds((prev) => new Set(prev).add(a.id));
                                appendLog(
                                  `- Artist \`${a.id}\` (${a.name}) queued for **Instagram enrichment** and hidden from admin view.`
                                );
                              }}
                              className="text-[11px] px-2 py-1 rounded bg-blue-600 text-white hover:bg-blue-700"
                            >
                              Instagram
                            </button>
                          </div>
                          <div className="flex flex-wrap items-center justify-center gap-2">
                            <button
                              type="button"
                              onClick={() => {
                                setHiddenArtistIds((prev) =>
                                  new Set(prev).add(a.id)
                                );
                                appendLog(
                                  `- Artist \`${a.id}\` (${a.name}) marked as **Verified artist**.`
                                );
                              }}
                              className="text-[11px] px-2 py-1 rounded bg-emerald-600 text-white hover:bg-emerald-700"
                            >
                              Verified
                            </button>
                            <button
                              type="button"
                              onClick={() => handleArtistAction(a, "not-artist")}
                              className="text-[11px] px-2 py-1 rounded bg-red-600 text-white hover:bg-red-700"
                            >
                              Not artist
                            </button>
                            <button
                              type="button"
                              onClick={() => handleArtistAction(a, "studio")}
                              className="text-[11px] px-2 py-1 rounded bg-amber-500 text-white hover:bg-amber-600"
                            >
                              Studio
                            </button>
                          </div>
                      </div>
                      </div>
                    );
                  })}
                </div>
                {filteredArtists.length === 0 && (
                  <p className="text-xs text-muted-foreground py-8 text-center">
                    No artists match the selected filters.
                  </p>
                )}
                {artistTotalPages > 1 && filteredArtists.length > 0 && (
                  <div className="flex items-center justify-center gap-3 mt-2">
                    <button
                      type="button"
                      onClick={() =>
                        setArtistPage((p) => Math.max(0, p - 1))
                      }
                      disabled={artistPage <= 0}
                      className="text-xs px-2 py-1 rounded border border-border disabled:opacity-50"
                    >
                      Previous
                    </button>
                    <span className="text-[11px] text-muted-foreground">
                      Page {artistPage + 1} of {artistTotalPages}
                    </span>
                    <button
                      type="button"
                      onClick={() =>
                        setArtistPage((p) =>
                          Math.min(artistTotalPages - 1, p + 1)
                        )
                      }
                      disabled={artistPage >= artistTotalPages - 1}
                      className="text-xs px-2 py-1 rounded border border-border disabled:opacity-50"
                    >
                      Next
                    </button>
                  </div>
                )}
              </div>
            )}

            {tab === "tattoos" && (
              <div className="flex flex-col gap-3">
                {paginatedTattoos.length === 0 ? (
                  <p className="text-xs text-muted-foreground py-8 text-center">
                    Tattoos tab currently requires full artist data (run via
                    scraper-powered tools). For now this view is empty.
                  </p>
                ) : (
                  <>
                    <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3">
                      {paginatedTattoos
                        .filter(
                          (t) =>
                            !hiddenTattooKeys.has(
                              `${t.artistId}:${t.imageId}`
                            )
                        )
                        .map((t) => (
                          <div
                            key={`${t.artistId}:${t.imageId}`}
                            className="relative group rounded-md overflow-hidden bg-muted"
                          >
                            <a
                              href={imageUrl(t.imageFull)}
                              target="_blank"
                              rel="noopener noreferrer"
                            >
                              <img
                                src={imageUrl(t.imageThumb)}
                                alt={`${t.artistName} tattoo ${t.imageId}`}
                                className="w-full h-auto block"
                              />
                            </a>
                            <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                              <button
                                type="button"
                                onClick={() => handleTattooDelete(t)}
                                className="text-[11px] px-2 py-1 rounded bg-red-600 text-white hover:bg-red-700"
                              >
                                Delete image
                              </button>
                            </div>
                          </div>
                        ))}
                    </div>
                    {tattooTotalPages > 1 && (
                      <div className="flex items-center justify-center gap-3 mt-2">
                        <button
                          type="button"
                          onClick={() =>
                            setTattooPage((p) => Math.max(0, p - 1))
                          }
                          disabled={tattooPage <= 0}
                          className="text-xs px-2 py-1 rounded border border-border disabled:opacity-50"
                        >
                          Previous
                        </button>
                        <span className="text-[11px] text-muted-foreground">
                          Page {tattooPage + 1} of {tattooTotalPages}
                        </span>
                        <button
                          type="button"
                          onClick={() =>
                            setTattooPage((p) =>
                              Math.min(tattooTotalPages - 1, p + 1)
                            )
                          }
                          disabled={tattooPage >= tattooTotalPages - 1}
                          className="text-xs px-2 py-1 rounded border border-border disabled:opacity-50"
                        >
                          Next
                        </button>
                      </div>
                    )}
                  </>
                )}
              </div>
            )}
          </div>

          <aside className="w-full md:w-72 md:max-w-xs border border-border rounded-md bg-card px-3 py-2">
            <h2 className="text-xs font-semibold mb-1">Session notes</h2>
            <p className="text-[11px] text-muted-foreground mb-2">
              Actions you take are appended here and included in the downloaded
              markdown file.
            </p>
            <div className="border border-border rounded bg-muted/40 p-2 h-64 overflow-auto">
              <pre className="text-[11px] whitespace-pre-wrap break-words">
                {markdownLog}
              </pre>
            </div>
          </aside>
        </div>
      </main>
    </div>
  );
}

