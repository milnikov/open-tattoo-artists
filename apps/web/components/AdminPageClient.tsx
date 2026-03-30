"use client";

import { useMemo, useState, useEffect, useRef } from "react";
import type { CompactArtist } from "@/lib/data";
import { artistFollowerCount } from "@/lib/artist-follower-count";
import { imageUrl } from "@/lib/images";

type AdminTab = "artists" | "tattoos";
type ArtistSortKey = "name-asc" | "followers-desc";

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
  instagramEnriched: boolean;
};

/** Full URL to Instagram profile, or null if missing or invalid. */
function instagramProfileUrl(artist: { links?: { instagram?: string } }): string | null {
  const raw = artist.links?.instagram?.trim();
  if (!raw) return null;
  if (/^https?:\/\//i.test(raw)) return raw;
  const handle = raw
    .replace(/^@/, "")
    .replace(/^instagram\.com\//i, "")
    .replace(/^www\.instagram\.com\//i, "")
    .replace(/\/+$/, "");
  if (!handle) return null;
  return `https://www.instagram.com/${handle}/`;
}

interface AdminPageClientProps {
  artists: CompactArtist[];
  tattoos: FlattenedTattoo[];
}

function MobileArtistSwipeCard({
  artist,
  threshold,
  onVerified,
  onNotArtist,
  onStudio,
  onNeedToCheck,
}: {
  artist: CompactArtist;
  threshold: number;
  onVerified: () => void;
  onNotArtist: () => void;
  onStudio: () => void;
  onNeedToCheck: () => void;
}) {
  const startRef = useRef({ x: 0, y: 0 });
  const posRef = useRef({ x: 0, y: 0 });
  const draggingRef = useRef(false);
  const [isDraggingUi, setIsDraggingUi] = useState(false);
  const [offset, setOffset] = useState({ x: 0, y: 0 });
  const touchStartMsRef = useRef(0);

  const igHref = instagramProfileUrl(artist);
  const openArtistPrimary = igHref ?? `/artists/${artist.id}`;

  const thumbs =
    (artist.thumbs && artist.thumbs.length > 0
      ? artist.thumbs
      : artist.thumb
      ? [artist.thumb]
      : []
    ).slice(0, 3);

  const absX = Math.abs(offset.x);
  const absY = Math.abs(offset.y);
  const dominant =
    absX >= absY
      ? offset.x > 12
        ? "verified"
        : offset.x < -12
          ? "not-artist"
          : null
      : offset.y > 12
        ? "studio"
        : offset.y < -12
          ? "need-check"
          : null;

  const hintStrength = Math.min(1, Math.max(absX, absY) / (threshold * 1.2));

  function completeSwipe() {
    const { x: dx, y: dy } = posRef.current;
    const ax = Math.abs(dx);
    const ay = Math.abs(dy);
    if (ax < threshold && ay < threshold) {
      const tapSlop = 14;
      if (
        Math.hypot(dx, dy) < tapSlop &&
        Date.now() - touchStartMsRef.current < 900
      ) {
        window.open(openArtistPrimary, "_blank", "noopener,noreferrer");
      }
      setOffset({ x: 0, y: 0 });
      posRef.current = { x: 0, y: 0 };
      return;
    }
    if (ax >= ay) {
      if (dx > 0) onVerified();
      else onNotArtist();
    } else {
      if (dy > 0) onStudio();
      else onNeedToCheck();
    }
    setOffset({ x: 0, y: 0 });
  }

  return (
    <div className="w-full max-w-md mx-auto flex flex-col gap-3">
      <div
        className="relative touch-none rounded-xl border border-border bg-card shadow-md overflow-hidden select-none"
        style={{
          transform: `translate(${offset.x}px, ${offset.y}px) rotate(${offset.x * 0.04}deg)`,
          transition: isDraggingUi ? "none" : "transform 0.22s ease-out",
        }}
        onTouchStart={(e) => {
          if (e.touches.length !== 1) return;
          draggingRef.current = true;
          touchStartMsRef.current = Date.now();
          setIsDraggingUi(true);
          startRef.current = {
            x: e.touches[0].clientX,
            y: e.touches[0].clientY,
          };
          posRef.current = { x: 0, y: 0 };
          setOffset({ x: 0, y: 0 });
        }}
        onTouchMove={(e) => {
          if (!draggingRef.current || e.touches.length !== 1) return;
          const x = e.touches[0].clientX - startRef.current.x;
          const y = e.touches[0].clientY - startRef.current.y;
          posRef.current = { x, y };
          setOffset({ x, y });
        }}
        onTouchEnd={() => {
          if (!draggingRef.current) return;
          draggingRef.current = false;
          setIsDraggingUi(false);
          completeSwipe();
        }}
        onTouchCancel={() => {
          draggingRef.current = false;
          setIsDraggingUi(false);
          posRef.current = { x: 0, y: 0 };
          setOffset({ x: 0, y: 0 });
        }}
      >
        {dominant && hintStrength > 0.08 && (
          <div
            className="pointer-events-none absolute inset-0 z-10 flex items-center justify-center text-center p-4"
            style={{ opacity: hintStrength * 0.92 }}
          >
            <span
              className={`text-sm font-bold uppercase tracking-wide px-4 py-2 rounded-lg border-2 border-background shadow-lg ${
                dominant === "verified"
                  ? "bg-emerald-600 text-white"
                  : dominant === "not-artist"
                    ? "bg-red-600 text-white"
                    : dominant === "studio"
                      ? "bg-amber-500 text-white"
                      : "bg-blue-600 text-white"
              }`}
            >
              {dominant === "verified"
                ? "Verified"
                : dominant === "not-artist"
                  ? "Not artist"
                  : dominant === "studio"
                    ? "Studio"
                    : "Need to check"}
            </span>
          </div>
        )}
        <div className="aspect-[4/3] bg-muted">
          {thumbs.length > 0 ? (
            <div className="w-full h-full grid grid-cols-3 gap-px bg-background/40">
              {thumbs.map((t, idx) => (
                <div key={idx} className="relative bg-muted overflow-hidden">
                  <img
                    src={imageUrl(t)}
                    alt={artist.name}
                    className="w-full h-full object-cover"
                  />
                </div>
              ))}
            </div>
          ) : (
            <div className="w-full h-full flex items-center justify-center text-[11px] text-muted-foreground">
              {artist.tattoo_count > 0
                ? `${artist.tattoo_count} images`
                : "No image"}
            </div>
          )}
        </div>
        <div className="p-3 border-t border-border">
          <div className="text-sm font-semibold">{artist.name}</div>
          <div className="text-[12px] text-muted-foreground mt-0.5">
            {artist.location.city}, {artist.location.country}
          </div>
          {artist.styles.length > 0 && (
            <div className="text-[12px] text-muted-foreground mt-1">
              {artist.styles.slice(0, 5).join(", ")}
            </div>
          )}
        </div>
      </div>
      <a
        href={openArtistPrimary}
        target="_blank"
        rel="noopener noreferrer"
        className="text-center text-xs text-muted-foreground underline underline-offset-2 hover:text-foreground"
      >
        {igHref ? "Open Instagram" : "Open profile (no Instagram URL)"}
      </a>
    </div>
  );
}

const ARTISTS_PAGE_SIZE = 60;
const TATTOOS_PAGE_SIZE = 60;
const SWIPE_THRESHOLD_PX = 72;

export function AdminPageClient({ artists, tattoos }: AdminPageClientProps) {
  const [tab, setTab] = useState<AdminTab>("artists");

  const [styleFilter, setStyleFilter] = useState("");
  const [countryFilter, setCountryFilter] = useState("");
  const [cityFilter, setCityFilter] = useState("");
  const [sourceFilter, setSourceFilter] = useState("");
  const [instagramEnrichedOnly, setInstagramEnrichedOnly] = useState(false);
  const [artistSortKey, setArtistSortKey] = useState<ArtistSortKey>("name-asc");

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
    const citiesInCountry =
      countryFilter && countryFilter !== "Unknown"
        ? Array.from(cityByCountry.get(countryFilter) ?? []).sort()
        : [];
    const sources = Array.from(sourceSet).sort();
    return { styles, countries, citiesInCountry, sources };
  }, [artists, countryFilter]);

  const filteredArtists = useMemo(() => {
    const filtered = artists.filter((a) => {
      if (a.verified) return false;
      if (hiddenArtistIds.has(a.id)) return false;
      if (styleFilter && !a.styles.includes(styleFilter)) return false;
      if (countryFilter && a.location.country !== countryFilter) return false;
      if (cityFilter && a.location.city !== cityFilter) return false;
      if (sourceFilter && (a.source_domain ?? "unknown") !== sourceFilter) return false;
      const isEnriched = Boolean(a.instagram_enriched);
      if (instagramEnrichedOnly ? !isEnriched : isEnriched) return false;
      return true;
    });

    if (artistSortKey === "followers-desc") {
      return filtered.sort((a, b) => {
        const db = artistFollowerCount(b);
        const da = artistFollowerCount(a);
        if (db !== da) return db - da;
        return a.name.localeCompare(b.name, undefined, { sensitivity: "base" });
      });
    }

    return filtered.sort((a, b) =>
      a.name.localeCompare(b.name, undefined, { sensitivity: "base" })
    );
  }, [
    artists,
    hiddenArtistIds,
    styleFilter,
    countryFilter,
    cityFilter,
    sourceFilter,
    instagramEnrichedOnly,
    artistSortKey,
  ]);

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
      if (instagramEnrichedOnly ? !t.instagramEnriched : t.instagramEnriched) return false;
      return true;
    });
  }, [
    tattoos,
    hiddenTattooKeys,
    styleFilter,
    countryFilter,
    cityFilter,
    sourceFilter,
    instagramEnrichedOnly,
  ]);

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

  useEffect(() => {
    if (countryFilter === "Unknown") setCityFilter("");
  }, [countryFilter]);

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

  function handleVerifiedArtist(artist: CompactArtist) {
    setHiddenArtistIds((prev) => new Set(prev).add(artist.id));
    appendLog(
      `- Artist \`${artist.id}\` (${artist.name}) marked as **Verified artist**.`
    );
  }

  function handleNeedToCheck(artist: CompactArtist) {
    setHiddenArtistIds((prev) => new Set(prev).add(artist.id));
    appendLog(
      `- Artist \`${artist.id}\` (${artist.name}) marked **Need to check** (session note).`
    );
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
            <div className="flex flex-wrap items-center gap-2 mb-4">
              <select
                aria-label="Style filter"
                value={styleFilter}
                onChange={(e) => {
                  setStyleFilter(e.target.value);
                  setArtistPage(0);
                  setTattooPage(0);
                }}
                className="rounded border border-border bg-background px-2 py-1 text-xs min-w-0 max-w-[min(100%,11rem)]"
              >
                <option value="">All Styles</option>
                {styles.map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </select>
              <select
                aria-label="Country filter"
                value={countryFilter}
                onChange={(e) => {
                  setCountryFilter(e.target.value);
                  setCityFilter("");
                  setArtistPage(0);
                  setTattooPage(0);
                }}
                className="rounded border border-border bg-background px-2 py-1 text-xs min-w-0 max-w-[min(100%,11rem)]"
              >
                <option value="">All Countries</option>
                {countries.map((c) => (
                  <option key={c} value={c}>
                    {c}
                  </option>
                ))}
              </select>
              <select
                aria-label="City filter"
                value={cityFilter}
                onChange={(e) => {
                  setCityFilter(e.target.value);
                  setArtistPage(0);
                  setTattooPage(0);
                }}
                disabled={!countryFilter || countryFilter === "Unknown"}
                className="rounded border border-border bg-background px-2 py-1 text-xs min-w-0 max-w-[min(100%,11rem)] disabled:opacity-50"
              >
                <option value="">All Cities</option>
                {citiesInCountry.map((city) => (
                  <option key={city} value={city}>
                    {city}
                  </option>
                ))}
              </select>
              <select
                aria-label="Source filter"
                value={sourceFilter}
                onChange={(e) => {
                  setSourceFilter(e.target.value);
                  setArtistPage(0);
                  setTattooPage(0);
                }}
                className="rounded border border-border bg-background px-2 py-1 text-xs min-w-0 max-w-[min(100%,12rem)]"
              >
                <option value="">All Sources</option>
                {sources.map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </select>
              <button
                type="button"
                aria-label="Instagram-enriched profile filter"
                title={
                  instagramEnrichedOnly
                    ? "Showing only Instagram-enriched profiles"
                    : "Hiding Instagram-enriched profiles"
                }
                onClick={() => {
                  setInstagramEnrichedOnly((v) => !v);
                  setArtistPage(0);
                  setTattooPage(0);
                }}
                className={`text-[11px] px-2 py-1 rounded border border-border transition-colors whitespace-nowrap ${
                  instagramEnrichedOnly
                    ? "bg-foreground text-background"
                    : "bg-background text-foreground hover:bg-secondary"
                }`}
              >
                {instagramEnrichedOnly
                  ? "Enriched only"
                  : "Hide enriched"}
              </button>
              {tab === "artists" && (
                <select
                  aria-label="Sort artists"
                  value={artistSortKey}
                  onChange={(e) => {
                    setArtistSortKey(e.target.value as ArtistSortKey);
                    setArtistPage(0);
                  }}
                  className="rounded border border-border bg-background px-2 py-1 text-xs min-w-0 max-w-[min(100%,12rem)]"
                >
                  <option value="name-asc">Sort: Name (A–Z)</option>
                  <option value="followers-desc">Sort: Most followed</option>
                </select>
              )}
              <span className="text-xs text-muted-foreground">
                {tab === "artists"
                  ? `${filteredArtists.length} artists to check`
                  : `${allTattoos.length} tattoos`}
              </span>
            </div>

            {tab === "artists" && (
              <div className="flex flex-col gap-3">
                {/* Mobile: one card, swipe gestures */}
                <div className="md:hidden flex flex-col gap-2">
                  {filteredArtists.length === 0 ? (
                    <p className="text-xs text-muted-foreground py-12 text-center">
                      No artists match the selected filters.
                    </p>
                  ) : (
                    <MobileArtistSwipeCard
                      key={filteredArtists[0]!.id}
                      artist={filteredArtists[0]!}
                      threshold={SWIPE_THRESHOLD_PX}
                      onVerified={() => handleVerifiedArtist(filteredArtists[0]!)}
                      onNotArtist={() =>
                        handleArtistAction(filteredArtists[0]!, "not-artist")
                      }
                      onStudio={() =>
                        handleArtistAction(filteredArtists[0]!, "studio")
                      }
                      onNeedToCheck={() =>
                        handleNeedToCheck(filteredArtists[0]!)
                      }
                    />
                  )}
                </div>

                {/* Desktop: grid + hover actions */}
                <div className="hidden md:flex flex-col gap-3">
                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
                    {paginatedArtists.map((a) => {
                      const thumbs =
                        (a.thumbs && a.thumbs.length > 0
                          ? a.thumbs
                          : a.thumb
                          ? [a.thumb]
                          : []
                        ).slice(0, 3);
                      const cardHref =
                        instagramProfileUrl(a) ?? `/artists/${a.id}`;
                      return (
                        <div
                          key={a.id}
                          className="relative group border border-border rounded-md overflow-hidden bg-card"
                        >
                          <a
                            href={cardHref}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="block relative z-0 cursor-pointer"
                            aria-label={
                              instagramProfileUrl(a)
                                ? `Open Instagram for ${a.name}`
                                : `Open profile for ${a.name}`
                            }
                          >
                            <div className="aspect-[4/3] bg-muted overflow-hidden">
                              {thumbs.length > 0 ? (
                                <div className="w-full h-full grid grid-cols-3 gap-px bg-background/40">
                                  {thumbs.map((t, idx) => (
                                    <div
                                      key={idx}
                                      className="relative bg-muted overflow-hidden"
                                    >
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
                          </a>
                          <div className="pointer-events-none group-hover:pointer-events-auto absolute inset-0 z-10 bg-black/45 opacity-0 group-hover:opacity-100 transition-opacity flex flex-col items-center justify-center gap-2 px-2">
                            <div className="flex flex-wrap items-center justify-center gap-2">
                              <a
                                href={`/artists/${a.id}`}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="text-[11px] px-2 py-1 rounded bg-slate-800 text-white hover:bg-slate-700"
                              >
                                Site profile
                              </a>
                              <button
                                type="button"
                                onClick={() => handleNeedToCheck(a)}
                                className="text-[11px] px-2 py-1 rounded bg-blue-600 text-white hover:bg-blue-700"
                              >
                                Need to check
                              </button>
                            </div>
                            <div className="flex flex-wrap items-center justify-center gap-2">
                              <button
                                type="button"
                                onClick={() => handleVerifiedArtist(a)}
                                className="text-[11px] px-2 py-1 rounded bg-emerald-600 text-white hover:bg-emerald-700"
                              >
                                Verified
                              </button>
                              <button
                                type="button"
                                onClick={() =>
                                  handleArtistAction(a, "not-artist")
                                }
                                className="text-[11px] px-2 py-1 rounded bg-red-600 text-white hover:bg-red-700"
                              >
                                Not artist
                              </button>
                              <button
                                type="button"
                                onClick={() =>
                                  handleArtistAction(a, "studio")
                                }
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

