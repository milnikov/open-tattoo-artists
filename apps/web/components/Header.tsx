"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import type { User } from "@supabase/supabase-js";
import { createClient } from "@/lib/supabase/client";
import { SuggestArtistModal } from "./SuggestArtistModal";

export function Header() {
  const [suggestOpen, setSuggestOpen] = useState(false);
  const [user, setUser] = useState<User | null>(null);
  const supabase = createClient();

  useEffect(() => {
    if (!supabase) return;
    supabase.auth.getSession().then(({ data: { session } }) => {
      setUser(session?.user ?? null);
    });
    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      setUser(session?.user ?? null);
    });
    return () => subscription.unsubscribe();
  }, []);

  async function signIn() {
    if (!supabase) return;
    await supabase.auth.signInWithOAuth({
      provider: "google",
      options: { redirectTo: `${window.location.origin}/auth/callback` },
    });
  }

  return (
    <>
      <nav className="border-b bg-white">
        <div className="mx-auto max-w-6xl px-4 py-3 flex items-center justify-between">
          <Link href="/" className="text-xl font-bold">
            thetattoo.world
          </Link>
          <div className="flex items-center gap-4">
            <button
              type="button"
              onClick={() => setSuggestOpen(true)}
              className="hover:underline"
            >
              Suggest artist
            </button>
            {user ? (
              <Link
                href="/profile"
                className="flex items-center justify-center w-9 h-9 rounded-full overflow-hidden border border-gray-200 bg-gray-100 hover:ring-2 hover:ring-gray-300 focus:outline-none focus:ring-2 focus:ring-gray-400"
                title={user.user_metadata?.full_name ?? user.email ?? "Profile"}
              >
                {user.user_metadata?.avatar_url ? (
                  <img
                    src={user.user_metadata.avatar_url}
                    alt=""
                    className="w-full h-full object-cover"
                  />
                ) : (
                  <span className="text-sm font-medium text-gray-600">
                    {(user.user_metadata?.full_name ?? user.email ?? "?")[0].toUpperCase()}
                  </span>
                )}
              </Link>
            ) : (
              <button
                type="button"
                onClick={signIn}
                className="px-3 py-1.5 text-sm font-medium text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200"
              >
                Login
              </button>
            )}
          </div>
        </div>
      </nav>
      <SuggestArtistModal open={suggestOpen} onClose={() => setSuggestOpen(false)} />
    </>
  );
}
