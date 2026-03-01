"use client";

import { createClient } from "@/lib/supabase/client";
import { useEffect, useState } from "react";

type Props = { artistId: string };

export function FavoriteButton({ artistId }: Props) {
  const [isFavorite, setIsFavorite] = useState(false);
  const [loading, setLoading] = useState(false);
  const [show, setShow] = useState(false);
  const supabase = createClient();

  useEffect(() => {
    if (!supabase) {
      setShow(false);
      return;
    }
    supabase.auth.getSession().then(({ data: { session } }) => {
      if (!session) {
        setShow(false);
        return;
      }
      setShow(true);
      supabase
        .from("favourites")
        .select("artist_id")
        .eq("user_id", session.user.id)
        .eq("artist_id", artistId)
        .maybeSingle()
        .then(({ data }) => setIsFavorite(!!data));
    });
  }, [supabase, artistId]);

  async function toggle() {
    if (!supabase) return;
    const {
      data: { session },
    } = await supabase.auth.getSession();
    if (!session) return;
    setLoading(true);
    if (isFavorite) {
      await supabase
        .from("favourites")
        .delete()
        .eq("user_id", session.user.id)
        .eq("artist_id", artistId);
      setIsFavorite(false);
    } else {
      await supabase
        .from("favourites")
        .insert({ user_id: session.user.id, artist_id: artistId });
      setIsFavorite(true);
    }
    setLoading(false);
  }

  if (!show) return null;

  return (
    <button
      type="button"
      onClick={toggle}
      disabled={loading}
      className="text-sm px-3 py-1.5 border rounded hover:bg-gray-50 disabled:opacity-50 inline-flex items-center gap-1"
    >
      {isFavorite ? "★ Favorited" : "☆ Add to favorites"}
    </button>
  );
}
