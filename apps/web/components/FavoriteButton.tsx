"use client";

import { createClient } from "@/lib/supabase/client";
import { useCallback, useEffect, useMemo, useState } from "react";

type Props = { artistId: string };

function fetchFavoriteState(
  supabase: NonNullable<ReturnType<typeof createClient>>,
  artistId: string,
  onResult: (show: boolean, isFavorite: boolean) => void
) {
  supabase.auth.getSession().then(({ data: { session } }) => {
    if (!session) {
      onResult(false, false);
      return;
    }
    supabase
      .from("favourites")
      .select("artist_id")
      .eq("user_id", session.user.id)
      .eq("artist_id", artistId)
      .maybeSingle()
      .then(({ data }) => onResult(true, !!data));
  });
}

export function FavoriteButton({ artistId }: Props) {
  const [isFavorite, setIsFavorite] = useState(false);
  const [loading, setLoading] = useState(false);
  const [show, setShow] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const supabase = useMemo(() => createClient(), []);

  const refetch = useCallback(() => {
    if (!supabase) return;
    fetchFavoriteState(supabase, artistId, (showState, favoriteState) => {
      setShow(showState);
      setIsFavorite(favoriteState);
    });
  }, [supabase, artistId]);

  useEffect(() => {
    if (!supabase) {
      setShow(false);
      return;
    }
    fetchFavoriteState(supabase, artistId, (showState, favoriteState) => {
      setShow(showState);
      setIsFavorite(favoriteState);
    });
    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange(() => refetch());
    return () => subscription.unsubscribe();
  }, [supabase, artistId, refetch]);

  async function toggle() {
    if (!supabase) return;
    setError(null);
    const {
      data: { session },
    } = await supabase.auth.getSession();
    if (!session) return;
    setLoading(true);
    if (isFavorite) {
      const { error: err } = await supabase
        .from("favourites")
        .delete()
        .eq("user_id", session.user.id)
        .eq("artist_id", artistId);
      if (err) {
        setError("Couldn’t remove from favorites");
      } else {
        setIsFavorite(false);
      }
    } else {
      const { error: err } = await supabase
        .from("favourites")
        .insert({ user_id: session.user.id, artist_id: artistId });
      if (err) {
        setError("Couldn’t save to favorites");
      } else {
        setIsFavorite(true);
      }
    }
    setLoading(false);
  }

  if (!show) return null;

  return (
    <span className="inline-flex flex-wrap items-center gap-2">
      <button
        type="button"
        onClick={toggle}
        disabled={loading}
        className="text-sm px-3 py-1.5 border rounded hover:bg-gray-50 disabled:opacity-50 inline-flex items-center gap-1"
      >
        {isFavorite ? "★ Favorited" : "☆ Add to favorites"}
      </button>
      {error && (
        <span className="text-sm text-red-600" role="alert">
          {error}
        </span>
      )}
    </span>
  );
}
