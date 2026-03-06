"use client";

import { createClient } from "@/lib/supabase/client";
import { useCallback, useEffect, useMemo, useState } from "react";

function FavoriteIcon({ filled }: { filled?: boolean }) {
  return (
    <svg
      width="10"
      height="12"
      viewBox="0 0 10 12"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className="h-3 w-3 shrink-0"
      aria-hidden
    >
      <path
        d="M1 0.5H9C9.27614 0.5 9.5 0.723858 9.5 1V10.2334C9.5 10.622 9.07641 10.862 8.74316 10.6621L5.77148 8.87988C5.29657 8.59505 4.70343 8.59505 4.22852 8.87988L1.25684 10.6621C0.923589 10.862 0.5 10.622 0.5 10.2334V1C0.5 0.723858 0.723857 0.5 1 0.5Z"
        stroke="currentColor"
        strokeLinecap="round"
        strokeLinejoin="round"
        fill={filled ? "currentColor" : "none"}
      />
    </svg>
  );
}

type Props = { artistId: string; variant?: "default" | "muted" };

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

export function FavoriteButton({ artistId, variant = "default" }: Props) {
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

  async function handleLogin() {
    if (!supabase) return;
    await supabase.auth.signInWithOAuth({
      provider: "google",
      options: {
        redirectTo: `${typeof window !== "undefined" ? window.location.origin : ""}/auth/callback`,
      },
    });
  }

  async function toggle() {
    if (!supabase) return;
    setError(null);
    const {
      data: { session },
    } = await supabase.auth.getSession();
    if (!session) {
      handleLogin();
      return;
    }
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

  const isMuted = variant === "muted";
  const buttonClass = isMuted
    ? "text-xs text-muted-foreground hover:text-foreground transition-colors inline-flex items-center gap-1.5 disabled:opacity-50"
    : "text-xs rounded border border-border px-3 py-1 text-foreground hover:bg-secondary transition-colors whitespace-nowrap inline-flex items-center gap-1.5 disabled:opacity-50";

  if (!show) {
    return (
      <button type="button" onClick={handleLogin} className={buttonClass}>
        <FavoriteIcon />
        Save as favorite
      </button>
    );
  }

  return (
    <span className="inline-flex flex-wrap items-center gap-2">
      <button
        type="button"
        onClick={toggle}
        disabled={loading}
        className={buttonClass}
      >
        <FavoriteIcon filled={isFavorite} />
        {isFavorite ? "Saved" : "Save as favorite"}
      </button>
      {error && (
        <span className="text-sm text-red-600" role="alert">
          {error}
        </span>
      )}
    </span>
  );
}
