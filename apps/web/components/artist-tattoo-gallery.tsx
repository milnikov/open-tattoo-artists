"use client";

import { useCallback, useState } from "react";
import { imageUrl } from "@/lib/images";

export type TattooItem = {
  image_id: string;
  image_full: string;
  image_thumb: string;
};

type ApiTattoosResponse = {
  tattoos: TattooItem[];
  total: number;
  offset: number;
  limit: number;
  hasMore: boolean;
};

export const INITIAL_TATTOO_COUNT = 12;
const PAGE_SIZE = INITIAL_TATTOO_COUNT;

type Props = {
  artistId: string;
  artistName: string;
  initialTattoos: TattooItem[];
  total: number;
  /** How many items were rendered from the server (same as first slice length). */
  initialCount: number;
};

export function ArtistTattooGallery({
  artistId,
  artistName,
  initialTattoos,
  total,
  initialCount,
}: Props) {
  const [tattoos, setTattoos] = useState<TattooItem[]>(initialTattoos);
  const [nextOffset, setNextOffset] = useState(initialCount);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const hasMore = nextOffset < total;

  const loadMore = useCallback(async () => {
    if (!hasMore || loading) return;
    setLoading(true);
    setError(null);
    try {
      const qs = new URLSearchParams({
        offset: String(nextOffset),
        limit: String(PAGE_SIZE),
      });
      const res = await fetch(
        `/api/artists/${encodeURIComponent(artistId)}/tattoos?${qs.toString()}`
      );
      if (!res.ok) {
        const text = await res.text();
        throw new Error(text || res.statusText);
      }
      const data = (await res.json()) as ApiTattoosResponse;
      setTattoos((prev) => [...prev, ...data.tattoos]);
      setNextOffset((o) => o + data.tattoos.length);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load more");
    } finally {
      setLoading(false);
    }
  }, [artistId, hasMore, loading, nextOffset]);

  return (
    <div className="border-t border-border px-2 pt-3 pb-4 md:px-8 md:pt-6 md:pb-8">
      <div className="columns-2 md:columns-3 gap-x-2 md:gap-x-4">
        {tattoos.map((t) => (
          <a
            key={t.image_id}
            href={imageUrl(t.image_full)}
            target="_blank"
            rel="noopener noreferrer"
            className="block break-inside-avoid rounded overflow-hidden bg-muted hover:opacity-95 transition-opacity mb-2 md:mb-4"
          >
            <img
              src={imageUrl(t.image_thumb)}
              alt={`${artistName} tattoo ${t.image_id}`}
              className="w-full h-auto block"
              loading="lazy"
            />
          </a>
        ))}
      </div>
      {hasMore && (
        <div className="mt-4 flex flex-col items-center gap-2">
          <button
            type="button"
            onClick={() => void loadMore()}
            disabled={loading}
            className="text-xs rounded border border-border px-4 py-2 text-foreground hover:bg-secondary transition-colors disabled:opacity-50"
          >
            {loading ? "Loading…" : `Load more (${total - nextOffset} left)`}
          </button>
          {error && <p className="text-xs text-destructive">{error}</p>}
        </div>
      )}
    </div>
  );
}
