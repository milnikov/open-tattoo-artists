"use client";

import { createClient } from "@/lib/supabase/client";
import { useEffect, useState } from "react";
import type { User } from "@supabase/supabase-js";
import Link from "next/link";
import { imageUrl } from "@/lib/images";
import type { CompactArtist } from "@/lib/data";
import { ArtistRow } from "@/components/artist-row";
import { SiteFooter } from "@/components/site-footer";

const HEADER_BUTTON_CLASS =
  "text-xs rounded border border-border px-3 py-1 text-foreground hover:bg-secondary transition-colors whitespace-nowrap inline-flex items-center gap-1.5";

type Contribution = {
  id: string;
  type: string;
  artist_id: string | null;
  github_issue_url: string;
  status: string;
  contributor_email: string | null;
  created_at: string;
};

type Artist = {
  id: string;
  name: string;
  location: { city: string; country: string };
  styles: string[];
  links: { instagram: string; website?: string; source?: string };
  tattoos: Array<{ image_id: string; image_thumb: string }>;
};

export default function ProfilePage() {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<"favorites" | "contributions">("favorites");
  const [favoriteIds, setFavoriteIds] = useState<string[]>([]);
  const [compactArtists, setCompactArtists] = useState<CompactArtist[]>([]);
  const [contributions, setContributions] = useState<Contribution[]>([]);
  const [contributionArtists, setContributionArtists] = useState<Record<string, Artist>>({});
  const supabase = createClient();

  useEffect(() => {
    if (!supabase) {
      setLoading(false);
      return;
    }
    supabase.auth.getSession().then(({ data: { session } }) => {
      setUser(session?.user ?? null);
      setLoading(false);
    });

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      setUser(session?.user ?? null);
    });

    return () => subscription.unsubscribe();
  }, []);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const err = params.get("error");
    if (err === "auth_failed") setError("Sign-in failed. Please try again.");
    if (err === "missing_code") setError("Invalid sign-in link.");
  }, []);

  useEffect(() => {
    if (!supabase || !user) return;
    supabase
      .from("favourites")
      .select("artist_id")
      .then(({ data }) => setFavoriteIds((data ?? []).map((r) => r.artist_id)));
  }, [supabase, user]);

  useEffect(() => {
    fetch("/api/artists/compact")
      .then((r) => r.json())
      .then(setCompactArtists)
      .catch(() => setCompactArtists([]));
  }, []);

  useEffect(() => {
    if (!supabase || !user) return;
    supabase
      .from("contributions")
      .select("id, type, artist_id, github_issue_url, status, contributor_email, created_at")
      .order("created_at", { ascending: false })
      .then(({ data }) => setContributions(data ?? []));
  }, [supabase, user]);

  useEffect(() => {
    const ids = Array.from(new Set(contributions.map((c) => c.artist_id).filter((id): id is string => Boolean(id))));
    if (ids.length === 0) {
      setContributionArtists({});
      return;
    }
    const map: Record<string, Artist> = {};
    Promise.all(
      ids.map((id) =>
        fetch(`/api/artists/${id}`)
          .then((r) => (r.ok ? r.json() : null))
          .then((a) => {
            if (a) map[id] = a;
          })
      )
    ).then(() => setContributionArtists(map));
  }, [contributions]);

  async function signInWithGoogle() {
    if (!supabase) return;
    setError(null);
    const { error } = await supabase.auth.signInWithOAuth({
      provider: "google",
      options: {
        redirectTo: `${window.location.origin}/auth/callback`,
      },
    });
    if (error) setError(error.message);
  }

  async function signOut() {
    if (!supabase) return;
    await supabase.auth.signOut();
  }

  const favoriteArtists = compactArtists.filter((a) => favoriteIds.includes(a.id));

  if (loading) {
    return (
      <div className="min-h-screen flex flex-col bg-background text-foreground min-w-0">
        <div className="h-8 md:h-16" />
        <main className="flex-1 min-w-0 overflow-x-hidden px-4 md:px-8 py-6">
          <p className="text-sm text-muted-foreground">Loading…</p>
        </main>
        <SiteFooter />
      </div>
    );
  }

  return (
    <div className="min-h-screen flex flex-col bg-background text-foreground min-w-0">
      <div className="h-8 md:h-16" />

      <main className="flex-1 min-w-0 overflow-x-hidden">
        {error && (
          <div className="px-4 md:px-8 pt-4">
            <p className="text-xs text-red-600">{error}</p>
          </div>
        )}

        {user ? (
          <>
            <div className="flex items-center justify-between gap-4 px-4 md:px-8 py-6 border-b border-border">
              <div className="flex items-center gap-3 min-w-0">
                {user.user_metadata?.avatar_url && (
                  <img src={user.user_metadata.avatar_url} alt="" className="w-10 h-10 rounded-full shrink-0" />
                )}
                <div className="min-w-0">
                  <p className="text-sm font-bold text-foreground truncate">
                    {user.user_metadata?.full_name ?? user.email}
                  </p>
                  <p className="text-xs text-muted-foreground truncate">{user.email}</p>
                </div>
              </div>
              <button type="button" onClick={signOut} className={HEADER_BUTTON_CLASS}>
                Sign out
              </button>
            </div>

            <div className="flex items-center gap-2 px-4 md:px-8 h-9 border-b border-border">
              <button
                type="button"
                onClick={() => setTab("favorites")}
                className={`text-xs px-2 py-1 rounded transition-colors ${
                  tab === "favorites" ? "bg-foreground text-background" : "text-foreground hover:text-muted-foreground"
                }`}
              >
                Favorites
              </button>
              <button
                type="button"
                onClick={() => setTab("contributions")}
                className={`text-xs px-2 py-1 rounded transition-colors ${
                  tab === "contributions" ? "bg-foreground text-background" : "text-foreground hover:text-muted-foreground"
                }`}
              >
                Contributions
              </button>
            </div>

            <div>
              {tab === "favorites" && (
                <>
                  {favoriteArtists.length === 0 ? (
                    <div className="px-4 md:px-8 py-8">
                      <p className="text-xs text-muted-foreground">
                        No favorites yet. Add artists from their profile page.
                      </p>
                    </div>
                  ) : (
                    <div>
                      {favoriteArtists.map((artist, i) => (
                        <ArtistRow key={artist.id} artist={artist} index={i} isFirst={i === 0} />
                      ))}
                    </div>
                  )}
                </>
              )}

              {tab === "contributions" && (
                <div className="px-4 md:px-8 py-6">
                  {contributions.length === 0 ? (
                    <p className="text-xs text-muted-foreground">
                      No contributions yet. Use “Suggest artist” in the header or “Request update” on an artist page.
                    </p>
                  ) : (
                    <ul className="divide-y divide-border">
                      {contributions.map((c) => {
                        const artist = c.artist_id ? contributionArtists[c.artist_id] : null;
                        const isReport = c.type === "report";
                        return (
                          <li key={c.id} className="py-6 first:pt-0">
                            {artist ? (
                              <>
                                <Link href={`/artists/${artist.id}`} className="block hover:opacity-80 transition-opacity">
                                  <div className="flex gap-4">
                                    <div className="w-[72px] h-[96px] md:w-[80px] md:h-[108px] flex-shrink-0 bg-muted overflow-hidden rounded">
                                      {artist.tattoos?.[0]?.image_thumb ? (
                                        <img
                                          src={imageUrl(artist.tattoos[0].image_thumb)}
                                          alt=""
                                          className="w-full h-full object-cover"
                                        />
                                      ) : null}
                                    </div>
                                    <div className="min-w-0 flex-1">
                                      <p className="text-sm font-bold text-foreground">{artist.name}</p>
                                      <p className="text-xs text-muted-foreground">
                                        {artist.location.city}, {artist.location.country}
                                      </p>
                                      <p className="text-xs text-muted-foreground mt-1">
                                        {isReport ? "Problem reported" : `Contributed by ${c.contributor_email ?? "you"}`}
                                      </p>
                                    </div>
                                  </div>
                                </Link>
                                <a
                                  href={c.github_issue_url}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="text-xs text-foreground hover:text-muted-foreground transition-colors underline underline-offset-2 mt-2 inline-block"
                                >
                                  {isReport ? "View issue" : "View original issue"}
                                </a>
                              </>
                            ) : (
                              <div>
                                <p className="text-sm font-bold text-foreground">Suggest artist (pending)</p>
                                <a
                                  href={c.github_issue_url}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="text-xs text-foreground hover:text-muted-foreground transition-colors underline underline-offset-2 mt-1 inline-block"
                                >
                                  Open GitHub issue
                                </a>
                                <p className="text-xs text-muted-foreground mt-2">
                                  Once the artist is added, they’ll appear here as a card.
                                </p>
                              </div>
                            )}
                          </li>
                        );
                      })}
                    </ul>
                  )}
                </div>
              )}
            </div>
          </>
        ) : (
          <div className="px-4 md:px-8 py-8">
            <p className="text-xs text-muted-foreground mb-4">
              {supabase
                ? "Sign in with Google to save favourites and track contributions."
                : "Configure "}
              {!supabase && (
                <>
                  <code className="bg-muted px-1 rounded text-foreground">NEXT_PUBLIC_SUPABASE_URL</code> and{" "}
                  <code className="bg-muted px-1 rounded text-foreground">NEXT_PUBLIC_SUPABASE_ANON_KEY</code> in{" "}
                  <code className="bg-muted px-1 rounded text-foreground">.env.local</code>, enable Google in Supabase, then refresh.
                </>
              )}
            </p>
            {supabase && (
              <button
                type="button"
                onClick={signInWithGoogle}
                className={HEADER_BUTTON_CLASS + " inline-flex items-center gap-2"}
              >
                <svg className="w-4 h-4 shrink-0" viewBox="0 0 24 24">
                  <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" />
                  <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
                  <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" />
                  <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" />
                </svg>
                Sign in with Google
              </button>
            )}
          </div>
        )}
      </main>

      <SiteFooter />
    </div>
  );
}
