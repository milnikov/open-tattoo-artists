"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { AppSelect } from "@/components/app-select";
import { createClient } from "@/lib/supabase/client";
import {
  JUSTINK_COMMENT_MAX,
  JUSTINK_STATUSES,
  errorMessage,
  normalizeOutreachStatus,
  type JustinkArtist,
  type JustinkOutreachRow,
  type JustinkStatus,
} from "@/lib/justink";

type ArtistSortKey = "name-asc" | "followers-desc";
type EnrichedFilter = "" | "enriched" | "not-enriched";

type OutreachMaps = {
  status: Record<string, JustinkStatus>;
  comment: Record<string, string>;
};

const PAGE_SIZE = 50;
const COMMENT_DEBOUNCE_MS = 600;

const FILTER_WRAP = "max-w-[min(100%,12rem)] bg-background text-foreground";
const SEARCH_CLASS =
  "rounded border border-border bg-background px-2 py-1 text-xs min-w-0 max-w-[min(100%,16rem)]";

function instagramProfile(raw: string | undefined): {
  handle: string;
  href: string;
} | null {
  const value = raw?.trim();
  if (!value) return null;
  if (/^https?:\/\//i.test(value)) {
    try {
      const url = new URL(value);
      const handle = url.pathname.replace(/^\/+|\/+$/g, "").split("/")[0] ?? "";
      if (!handle) return { handle: value, href: value };
      return { handle: `@${handle.replace(/^@/, "")}`, href: value };
    } catch {
      return { handle: value, href: value };
    }
  }
  const handle = value
    .replace(/^@/, "")
    .replace(/^instagram\.com\//i, "")
    .replace(/^www\.instagram\.com\//i, "")
    .replace(/\/+$/, "");
  if (!handle) return null;
  return {
    handle: `@${handle}`,
    href: `https://www.instagram.com/${handle}/`,
  };
}

function statusSelectClass(status: JustinkStatus): string {
  switch (status) {
    case "reached":
      return "bg-blue-50 text-blue-950";
    case "no_reply":
      return "bg-slate-100 text-slate-800";
    case "interested":
      return "bg-emerald-50 text-emerald-950";
    case "not_interested":
      return "bg-red-50 text-red-950";
    case "scheduled":
      return "bg-amber-50 text-amber-950";
    case "got_feedback":
      return "bg-violet-50 text-violet-950";
    case "became_a_user":
      return "bg-emerald-600 text-white";
    default:
      return "bg-background text-muted-foreground";
  }
}

function toOutreachMaps(rows: JustinkOutreachRow[]): OutreachMaps {
  const status: Record<string, JustinkStatus> = {};
  const comment: Record<string, string> = {};
  for (const row of rows) {
    const normalized = normalizeOutreachStatus(row.status);
    if (normalized) status[row.artist_id] = normalized;
    if (row.comment) comment[row.artist_id] = row.comment;
  }
  return { status, comment };
}

function getOutreach(
  maps: OutreachMaps,
  artistId: string
): { status: JustinkStatus; comment: string } {
  return {
    status: maps.status[artistId] ?? "",
    comment: maps.comment[artistId] ?? "",
  };
}

export function JustinkPageClient() {
  const [artists, setArtists] = useState<JustinkArtist[]>([]);
  const [artistsLoading, setArtistsLoading] = useState(true);
  const [styleFilter, setStyleFilter] = useState("");
  const [countryFilter, setCountryFilter] = useState("");
  const [cityFilter, setCityFilter] = useState("");
  const [sourceFilter, setSourceFilter] = useState("");
  const [enrichedFilter, setEnrichedFilter] = useState<EnrichedFilter>("");
  const [statusFilter, setStatusFilter] = useState<JustinkStatus | "all">("all");
  const [query, setQuery] = useState("");
  const [artistSortKey, setArtistSortKey] = useState<ArtistSortKey>("followers-desc");
  const [page, setPage] = useState(0);
  const [statusById, setStatusById] = useState<Record<string, JustinkStatus>>({});
  const [commentById, setCommentById] = useState<Record<string, string>>({});
  const [saveError, setSaveError] = useState<string | null>(null);
  const [savingCount, setSavingCount] = useState(0);

  const outreachRef = useRef<OutreachMaps>({
    status: statusById,
    comment: commentById,
  });
  outreachRef.current = { status: statusById, comment: commentById };
  const debounceTimers = useRef<Map<string, number>>(new Map());

  const supabase = useMemo(() => createClient(), []);

  useEffect(() => {
    let cancelled = false;
    setArtistsLoading(true);
    fetch("/api/justink/artists")
      .then((res) => {
        if (!res.ok) throw new Error("Could not load artists.");
        return res.json() as Promise<JustinkArtist[]>;
      })
      .then((data) => {
        if (!cancelled) setArtists(Array.isArray(data) ? data : []);
      })
      .catch((err) => {
        if (!cancelled) {
          setSaveError(errorMessage(err, "Could not load artists."));
        }
      })
      .finally(() => {
        if (!cancelled) setArtistsLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!supabase) return;
    const client = supabase;
    let cancelled = false;
    const pageSize = 1000;
    async function loadOutreach() {
      const rows: JustinkOutreachRow[] = [];
      for (let from = 0; ; from += pageSize) {
        const { data, error } = await client
          .from("justink_outreach")
          .select("artist_id, status, comment")
          .range(from, from + pageSize - 1);
        if (error) throw error;
        const batch = (data ?? []) as JustinkOutreachRow[];
        rows.push(...batch);
        if (batch.length < pageSize) break;
      }
      if (cancelled) return;
      const maps = toOutreachMaps(rows);
      const merged: OutreachMaps = {
        status: { ...maps.status, ...outreachRef.current.status },
        comment: { ...maps.comment, ...outreachRef.current.comment },
      };
      outreachRef.current = merged;
      setStatusById(merged.status);
      setCommentById(merged.comment);
    }
    loadOutreach().catch((err) => {
      if (!cancelled) {
        setSaveError(errorMessage(err, "Could not load outreach rows."));
      }
    });
    return () => {
      cancelled = true;
    };
  }, [supabase]);

  useEffect(() => {
    return () => {
      for (const timer of debounceTimers.current.values()) {
        window.clearTimeout(timer);
      }
    };
  }, []);

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
    return {
      styles: Array.from(styleSet).sort(),
      countries: Array.from(countrySet).sort(),
      citiesInCountry:
        countryFilter && countryFilter !== "Unknown"
          ? Array.from(cityByCountry.get(countryFilter) ?? []).sort()
          : [],
      sources: Array.from(sourceSet).sort(),
    };
  }, [artists, countryFilter]);

  const statusCounts = useMemo(() => {
    const counts = Object.fromEntries(
      JUSTINK_STATUSES.map((s) => [s.value, 0])
    ) as Record<JustinkStatus, number>;
    for (const artist of artists) {
      const status = statusById[artist.id] ?? "";
      counts[status] += 1;
    }
    return counts;
  }, [artists, statusById]);

  const filteredArtists = useMemo(() => {
    const q = query.trim().toLowerCase();
    const filtered = artists.filter((a) => {
      if (styleFilter && !a.styles.includes(styleFilter)) return false;
      if (countryFilter && a.location.country !== countryFilter) return false;
      if (cityFilter && a.location.city !== cityFilter) return false;
      if (sourceFilter && (a.source_domain ?? "unknown") !== sourceFilter) {
        return false;
      }
      if (enrichedFilter === "enriched" && !a.instagram_enriched) return false;
      if (enrichedFilter === "not-enriched" && a.instagram_enriched) return false;
      const status = statusById[a.id] ?? "";
      if (statusFilter !== "all" && status !== statusFilter) return false;
      if (q) {
        const ig = instagramProfile(a.instagram);
        const haystack = `${a.name} ${a.instagram} ${ig?.handle ?? ""}`.toLowerCase();
        if (!haystack.includes(q)) return false;
      }
      return true;
    });

    if (artistSortKey === "followers-desc") {
      return filtered.sort((a, b) => {
        if (b.follower_count !== a.follower_count) {
          return b.follower_count - a.follower_count;
        }
        return a.name.localeCompare(b.name, undefined, { sensitivity: "base" });
      });
    }

    return filtered.sort((a, b) =>
      a.name.localeCompare(b.name, undefined, { sensitivity: "base" })
    );
  }, [
    artists,
    styleFilter,
    countryFilter,
    cityFilter,
    sourceFilter,
    enrichedFilter,
    statusFilter,
    query,
    artistSortKey,
    statusById,
  ]);

  const totalPages = Math.max(1, Math.ceil(filteredArtists.length / PAGE_SIZE));
  const paginatedArtists = useMemo(
    () =>
      filteredArtists.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE),
    [filteredArtists, page]
  );

  useEffect(() => {
    if (countryFilter === "Unknown") setCityFilter("");
  }, [countryFilter]);

  useEffect(() => {
    setPage(0);
  }, [
    styleFilter,
    countryFilter,
    cityFilter,
    sourceFilter,
    enrichedFilter,
    statusFilter,
    query,
    artistSortKey,
  ]);

  useEffect(() => {
    if (page > totalPages - 1) setPage(Math.max(0, totalPages - 1));
  }, [page, totalPages]);

  async function persist(artistId: string) {
    if (!supabase) {
      setSaveError("Supabase is not configured.");
      return;
    }
    const latest = getOutreach(outreachRef.current, artistId);
    const status = latest.status || null;
    const comment = latest.comment.slice(0, JUSTINK_COMMENT_MAX).trim();
    setSavingCount((n) => n + 1);
    setSaveError(null);
    try {
      if (!status && comment === "") {
        const { error } = await supabase
          .from("justink_outreach")
          .delete()
          .eq("artist_id", artistId);
        if (error) throw error;
        return;
      }
      const { error } = await supabase.from("justink_outreach").upsert(
        {
          artist_id: artistId,
          status,
          comment,
          updated_at: new Date().toISOString(),
        },
        { onConflict: "artist_id" }
      );
      if (error) throw error;
    } catch (err) {
      setSaveError(errorMessage(err, "Could not save outreach row."));
    } finally {
      setSavingCount((n) => Math.max(0, n - 1));
    }
  }

  function schedulePersist(artistId: string) {
    const existing = debounceTimers.current.get(artistId);
    if (existing) window.clearTimeout(existing);
    const timer = window.setTimeout(() => {
      debounceTimers.current.delete(artistId);
      void persist(artistId);
    }, COMMENT_DEBOUNCE_MS);
    debounceTimers.current.set(artistId, timer);
  }

  function updateOutreach(
    artistId: string,
    patch: Partial<{ status: JustinkStatus; comment: string }>,
    persistNow: boolean
  ) {
    const current = getOutreach(outreachRef.current, artistId);
    const next = {
      status: patch.status ?? current.status,
      comment: patch.comment ?? current.comment,
    };
    const maps: OutreachMaps = {
      status: { ...outreachRef.current.status },
      comment: { ...outreachRef.current.comment },
    };
    if (next.status) maps.status[artistId] = next.status;
    else delete maps.status[artistId];
    if (next.comment) maps.comment[artistId] = next.comment;
    else delete maps.comment[artistId];
    outreachRef.current = maps;
    if (patch.status !== undefined) setStatusById(maps.status);
    if (patch.comment !== undefined) setCommentById(maps.comment);
    if (persistNow) {
      const existing = debounceTimers.current.get(artistId);
      if (existing) window.clearTimeout(existing);
      debounceTimers.current.delete(artistId);
      void persist(artistId);
    } else {
      schedulePersist(artistId);
    }
  }

  return (
    <div className="min-h-screen flex flex-col bg-background text-foreground min-w-0">
      <div className="h-8 md:h-16" />

      <main className="flex-1 min-w-0 overflow-x-hidden px-4 md:px-8 py-4 flex flex-col gap-4">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <h1 className="text-sm font-semibold">JustInk outreach</h1>
            <p className="text-xs text-muted-foreground mt-1 max-w-xl">
              Track messages to artists about trying JustInk. Status and comments
              save automatically.
            </p>
          </div>
          <div className="text-[11px] text-muted-foreground">
            {savingCount > 0 ? "Saving…" : null}
          </div>
        </div>

        {saveError && (
          <p className="text-xs text-red-600" role="alert">
            {saveError}
          </p>
        )}

        <div className="flex flex-wrap items-center gap-1.5">
          {JUSTINK_STATUSES.map((s) => {
            const active = statusFilter === s.value;
            return (
              <button
                key={s.value || "empty"}
                type="button"
                onClick={() =>
                  setStatusFilter((prev) => (prev === s.value ? "all" : s.value))
                }
                className={`text-[11px] px-2 py-1 rounded border border-border transition-colors ${
                  active
                    ? "bg-foreground text-background"
                    : "bg-background text-foreground hover:bg-secondary"
                }`}
              >
                {s.label} {statusCounts[s.value].toLocaleString()}
              </button>
            );
          })}
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <input
            type="search"
            aria-label="Search name or Instagram"
            placeholder="Search name or Instagram"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className={SEARCH_CLASS}
          />
          <AppSelect
            aria-label="Style filter"
            value={styleFilter}
            onChange={(e) => setStyleFilter(e.target.value)}
            wrapperClassName={FILTER_WRAP}
          >
            <option value="">All Styles</option>
            {styles.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </AppSelect>
          <AppSelect
            aria-label="Country filter"
            value={countryFilter}
            onChange={(e) => {
              setCountryFilter(e.target.value);
              setCityFilter("");
            }}
            wrapperClassName={FILTER_WRAP}
          >
            <option value="">All Countries</option>
            {countries.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </AppSelect>
          <AppSelect
            aria-label="City filter"
            value={cityFilter}
            onChange={(e) => setCityFilter(e.target.value)}
            disabled={!countryFilter || countryFilter === "Unknown"}
            wrapperClassName={FILTER_WRAP}
          >
            <option value="">All Cities</option>
            {citiesInCountry.map((city) => (
              <option key={city} value={city}>
                {city}
              </option>
            ))}
          </AppSelect>
          <AppSelect
            aria-label="Source filter"
            value={sourceFilter}
            onChange={(e) => setSourceFilter(e.target.value)}
            wrapperClassName={FILTER_WRAP}
          >
            <option value="">All Sources</option>
            {sources.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </AppSelect>
          <AppSelect
            aria-label="Instagram-enriched profile filter"
            value={enrichedFilter}
            onChange={(e) => setEnrichedFilter(e.target.value as EnrichedFilter)}
            wrapperClassName={FILTER_WRAP}
          >
            <option value="">All Instagram data</option>
            <option value="enriched">Enriched only</option>
            <option value="not-enriched">Hide enriched</option>
          </AppSelect>
          <AppSelect
            aria-label="Outreach status filter"
            value={statusFilter}
            onChange={(e) =>
              setStatusFilter(e.target.value as JustinkStatus | "all")
            }
            wrapperClassName={FILTER_WRAP}
          >
            <option value="all">All Statuses</option>
            {JUSTINK_STATUSES.map((s) => (
              <option key={s.value || "empty"} value={s.value}>
                {s.label}
              </option>
            ))}
          </AppSelect>
          <AppSelect
            aria-label="Sort artists"
            value={artistSortKey}
            onChange={(e) => setArtistSortKey(e.target.value as ArtistSortKey)}
            wrapperClassName={FILTER_WRAP}
          >
            <option value="name-asc">Sort: Name (A–Z)</option>
            <option value="followers-desc">Sort: Most followed</option>
          </AppSelect>
          <span className="text-xs text-muted-foreground">
            {filteredArtists.length.toLocaleString()} artists
          </span>
        </div>

        <div className="overflow-x-auto border border-border rounded-md bg-card">
          <table className="w-full min-w-[860px] text-xs text-left border-collapse">
            <thead className="sticky top-0 bg-card z-10">
              <tr className="border-b border-border text-muted-foreground">
                <th className="font-medium px-3 py-2 w-[18%]">Name</th>
                <th className="font-medium px-3 py-2 w-[14%]">Instagram</th>
                <th className="font-medium px-3 py-2 w-[10%] text-right">
                  Followers
                </th>
                <th className="font-medium px-3 py-2 w-[12%]">Country</th>
                <th className="font-medium px-3 py-2 w-[12%]">City</th>
                <th className="font-medium px-3 py-2 w-[14%]">Status</th>
                <th className="font-medium px-3 py-2">Comment</th>
              </tr>
            </thead>
            <tbody>
              {artistsLoading ? (
                <tr>
                  <td
                    colSpan={7}
                    className="px-3 py-10 text-center text-muted-foreground"
                  >
                    Loading artists…
                  </td>
                </tr>
              ) : paginatedArtists.length === 0 ? (
                <tr>
                  <td
                    colSpan={7}
                    className="px-3 py-10 text-center text-muted-foreground"
                  >
                    No artists match the selected filters.
                  </td>
                </tr>
              ) : (
                paginatedArtists.map((artist) => {
                  const row = getOutreach(
                    { status: statusById, comment: commentById },
                    artist.id
                  );
                  const ig = instagramProfile(artist.instagram);
                  return (
                    <tr
                      key={artist.id}
                      className="border-b border-border last:border-b-0 hover:bg-muted/40"
                    >
                      <td className="px-3 py-2 align-middle">
                        <Link
                          href={`/artists/${artist.id}`}
                          target="_blank"
                          className="font-medium text-foreground hover:underline underline-offset-2"
                        >
                          {artist.name}
                        </Link>
                      </td>
                      <td className="px-3 py-2 align-middle">
                        {ig ? (
                          <a
                            href={ig.href}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-foreground hover:underline underline-offset-2"
                          >
                            {ig.handle}
                          </a>
                        ) : (
                          <span className="text-muted-foreground">—</span>
                        )}
                      </td>
                      <td className="px-3 py-2 align-middle text-right tabular-nums">
                        {artist.follower_count > 0
                          ? artist.follower_count.toLocaleString()
                          : "—"}
                      </td>
                      <td className="px-3 py-2 align-middle">
                        {artist.location.country || "—"}
                      </td>
                      <td className="px-3 py-2 align-middle">
                        {artist.location.city || "—"}
                      </td>
                      <td className="px-3 py-2 align-middle">
                        <AppSelect
                          aria-label={`Status for ${artist.name}`}
                          value={row.status}
                          onChange={(e) =>
                            updateOutreach(
                              artist.id,
                              { status: e.target.value as JustinkStatus },
                              true
                            )
                          }
                          wrapperClassName={`w-full ${statusSelectClass(row.status)}`}
                        >
                          {JUSTINK_STATUSES.map((s) => (
                            <option key={s.value || "empty"} value={s.value}>
                              {s.label}
                            </option>
                          ))}
                        </AppSelect>
                      </td>
                      <td className="px-3 py-2 align-middle">
                        <input
                          type="text"
                          aria-label={`Comment for ${artist.name}`}
                          placeholder="Add a note"
                          value={row.comment}
                          maxLength={JUSTINK_COMMENT_MAX}
                          onChange={(e) =>
                            updateOutreach(
                              artist.id,
                              { comment: e.target.value },
                              false
                            )
                          }
                          onBlur={() => {
                            const existing = debounceTimers.current.get(
                              artist.id
                            );
                            if (existing) window.clearTimeout(existing);
                            debounceTimers.current.delete(artist.id);
                            void persist(artist.id);
                          }}
                          className="w-full min-w-[12rem] rounded border border-border bg-background px-2 py-1 text-xs"
                        />
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>

        {totalPages > 1 && filteredArtists.length > 0 && (
          <div className="flex items-center justify-center gap-3">
            <button
              type="button"
              onClick={() => setPage((p) => Math.max(0, p - 1))}
              disabled={page <= 0}
              className="text-xs px-2 py-1 rounded border border-border disabled:opacity-50"
            >
              Previous
            </button>
            <span className="text-[11px] text-muted-foreground">
              Page {page + 1} of {totalPages}
            </span>
            <button
              type="button"
              onClick={() =>
                setPage((p) => Math.min(totalPages - 1, p + 1))
              }
              disabled={page >= totalPages - 1}
              className="text-xs px-2 py-1 rounded border border-border disabled:opacity-50"
            >
              Next
            </button>
          </div>
        )}
      </main>
    </div>
  );
}
