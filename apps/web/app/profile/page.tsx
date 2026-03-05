"use client";

import { createClient } from "@/lib/supabase/client";
import { useEffect, useState } from "react";
import type { User } from "@supabase/supabase-js";
import Link from "next/link";
import { imageUrl } from "@/lib/images";

type CompactArtist = {
  id: string;
  name: string;
  location: { city: string; country: string };
  styles: string[];
  links: { instagram: string };
  tattoo_count: number;
  thumb?: string;
};

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
      <div>
        <h1 className="text-2xl font-bold mb-6">Profile</h1>
        <p className="text-gray-500">Loading…</p>
      </div>
    );
  }

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Profile</h1>

      {error && (
        <div className="mb-4 p-3 rounded-lg bg-red-50 text-red-700 text-sm">
          {error}
        </div>
      )}

      <div className="border rounded-lg bg-white overflow-hidden">
        {user ? (
          <>
            <div className="flex items-center gap-3 p-6 border-b">
              {user.user_metadata?.avatar_url && (
                <img
                  src={user.user_metadata.avatar_url}
                  alt=""
                  className="w-12 h-12 rounded-full"
                />
              )}
              <div className="flex-1">
                <p className="font-medium text-gray-900">
                  {user.user_metadata?.full_name ?? user.email}
                </p>
                <p className="text-sm text-gray-500">{user.email}</p>
              </div>
              <button
                type="button"
                onClick={signOut}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200"
              >
                Sign out
              </button>
            </div>

            <div className="flex border-b">
              <button
                type="button"
                onClick={() => setTab("favorites")}
                className={`px-6 py-3 text-sm font-medium ${
                  tab === "favorites"
                    ? "border-b-2 border-gray-900 text-gray-900"
                    : "text-gray-500 hover:text-gray-700"
                }`}
              >
                Favorites
              </button>
              <button
                type="button"
                onClick={() => setTab("contributions")}
                className={`px-6 py-3 text-sm font-medium ${
                  tab === "contributions"
                    ? "border-b-2 border-gray-900 text-gray-900"
                    : "text-gray-500 hover:text-gray-700"
                }`}
              >
                Contributions
              </button>
            </div>

            <div className="p-6">
              {tab === "favorites" && (
                <div className="space-y-4">
                  {favoriteArtists.length === 0 ? (
                    <p className="text-gray-500">
                      No favorites yet. Add artists from their profile page.
                    </p>
                  ) : (
                    <ul className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
                      {favoriteArtists.map((a) => (
                        <li key={a.id}>
                          <Link
                            href={`/artists/${a.id}`}
                            className="block border rounded-lg overflow-hidden hover:shadow-md transition"
                          >
                            <div className="aspect-square bg-gray-200">
                              {a.thumb ? (
                                <img
                                  src={imageUrl(a.thumb)}
                                  alt={a.name}
                                  className="w-full h-full object-cover"
                                />
                              ) : (
                                <div className="w-full h-full flex items-center justify-center text-gray-400 text-sm">
                                  {a.tattoo_count > 0 ? `${a.tattoo_count} images` : "No image"}
                                </div>
                              )}
                            </div>
                            <div className="p-3">
                              <p className="font-semibold truncate">{a.name}</p>
                              <p className="text-sm text-gray-600 truncate">
                                {a.location.city}, {a.location.country}
                              </p>
                            </div>
                          </Link>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              )}

              {tab === "contributions" && (
                <div className="space-y-4">
                  {contributions.length === 0 ? (
                    <p className="text-gray-500">
                      No contributions yet. Use “Suggest artist” in the header to propose an artist, or “Report problem” on an artist page.
                    </p>
                  ) : (
                    <ul className="space-y-4">
                      {contributions.map((c) => {
                        const artist = c.artist_id ? contributionArtists[c.artist_id] : null;
                        const isReport = c.type === "report";
                        return (
                          <li key={c.id} className="border rounded-lg overflow-hidden">
                            {artist ? (
                              <>
                                <Link href={`/artists/${artist.id}`} className="block">
                                  <div className="flex gap-4 p-4">
                                    <div className="w-20 h-20 flex-shrink-0 bg-gray-200 rounded overflow-hidden">
                                      {artist.tattoos?.[0]?.image_thumb ? (
                                        <img
                                          src={imageUrl(artist.tattoos[0].image_thumb)}
                                          alt=""
                                          className="w-full h-full object-cover"
                                        />
                                      ) : null}
                                    </div>
                                    <div className="min-w-0 flex-1">
                                      <p className="font-semibold">{artist.name}</p>
                                      <p className="text-sm text-gray-600">
                                        {artist.location.city}, {artist.location.country}
                                      </p>
                                      <p className="text-xs text-gray-500 mt-1">
                                        {isReport
                                          ? "Problem reported"
                                          : `Contributed by ${c.contributor_email ?? "you"}`}
                                      </p>
                                    </div>
                                  </div>
                                </Link>
                                <div className="px-4 pb-3">
                                  <a
                                    href={c.github_issue_url}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="text-sm text-blue-600 hover:underline"
                                  >
                                    {isReport ? "View issue" : "View original issue"}
                                  </a>
                                </div>
                              </>
                            ) : (
                              <div className="p-4">
                                <p className="font-medium text-gray-900">Suggest artist (pending)</p>
                                <a
                                  href={c.github_issue_url}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="text-sm text-blue-600 hover:underline mt-1 inline-block"
                                >
                                  Open GitHub issue
                                </a>
                                <p className="text-xs text-gray-500 mt-2">
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
          <div className="p-6">
            <p className="text-gray-500 mb-4">
              {supabase
                ? "Sign in with Google to save favourites and track contributions."
                : "Configure "}
              {!supabase && (
                <>
                  <code className="bg-gray-100 px-1 rounded">NEXT_PUBLIC_SUPABASE_URL</code> and{" "}
                  <code className="bg-gray-100 px-1 rounded">NEXT_PUBLIC_SUPABASE_ANON_KEY</code> in{" "}
                  <code className="bg-gray-100 px-1 rounded">.env.local</code>, enable Google in
                  Supabase, then refresh.
                </>
              )}
            </p>
            {supabase && (
              <button
                type="button"
                onClick={signInWithGoogle}
                className="inline-flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 shadow-sm"
              >
                <svg className="w-5 h-5" viewBox="0 0 24 24">
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
      </div>
    </div>
  );
}
