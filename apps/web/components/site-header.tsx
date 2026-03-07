"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { User } from "lucide-react";
import type { User as SupabaseUser } from "@supabase/supabase-js";
import { createClient } from "@/lib/supabase/client";
import { SuggestArtistModal } from "./SuggestArtistModal";

export function SiteHeader() {
  const [suggestOpen, setSuggestOpen] = useState(false);
  const [user, setUser] = useState<SupabaseUser | null>(null);
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
      <header>
        <div className="flex items-center justify-between px-4 py-4 md:px-8 md:py-5">
          <Link
            href="/"
            className="inline-block text-sm font-bold tracking-tight text-foreground hover:opacity-80 origin-left scale-[1.2]"
          >
            <span className="font-spectral-italic font-normal text-base pr-[0.5px]">the</span>tattoo
            <span className="font-spectral-italic font-normal text-base">.world</span>
          </Link>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setSuggestOpen(true)}
              className="text-xs rounded border border-border px-3 py-1 text-foreground hover:bg-secondary transition-colors whitespace-nowrap"
            >
              Add Artist
            </button>
            {user ? (
              <Link
                href="/profile"
                className="flex shrink-0 items-center justify-center w-7 h-7 aspect-square rounded-full border border-border text-foreground hover:bg-secondary transition-colors overflow-hidden"
                aria-label="User profile"
                title={user.user_metadata?.full_name ?? user.email ?? "Profile"}
              >
                {user.user_metadata?.avatar_url ? (
                  <img
                    src={user.user_metadata.avatar_url}
                    alt=""
                    className="w-full h-full object-cover"
                  />
                ) : (
                  <User className="h-3.5 w-3.5" />
                )}
              </Link>
            ) : (
              <button
                type="button"
                onClick={signIn}
                className="text-xs rounded border border-border px-3 py-1 text-foreground hover:bg-secondary transition-colors whitespace-nowrap"
              >
                Login
              </button>
            )}
          </div>
        </div>
      </header>
      <SuggestArtistModal open={suggestOpen} onClose={() => setSuggestOpen(false)} />
    </>
  );
}
