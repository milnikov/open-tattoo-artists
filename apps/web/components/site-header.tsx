"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { User } from "lucide-react";
import type { User as SupabaseUser } from "@supabase/supabase-js";
import { createClient } from "@/lib/supabase/client";
import { SuggestArtistModal } from "./SuggestArtistModal";

function GlobeIcon({ className }: { className?: string }) {
  return (
    <svg width="13" height="13" viewBox="0 0 13 13" fill="none" className={className} aria-hidden>
      <path
        d="M6.5 12.5C9.81371 12.5 12.5 9.81371 12.5 6.5C12.5 3.18629 9.81371 0.5 6.5 0.5M6.5 12.5C3.18629 12.5 0.5 9.81371 0.5 6.5C0.5 3.18629 3.18629 0.5 6.5 0.5M6.5 12.5C8.34095 12.5 9.12753 9.05798 9.12753 6.5C9.12753 3.94202 8.34095 0.5 6.5 0.5M6.5 12.5C4.65905 12.5 3.87263 9.05795 3.87263 6.5C3.87263 3.94205 4.65905 0.5 6.5 0.5M0.833252 4.49999C5.25919 4.49999 7.74064 4.49999 12.1666 4.49999M0.833252 8.50002C5.25919 8.50002 7.74064 8.50002 12.1666 8.50002"
        stroke="currentColor"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function PlusIcon({ className }: { className?: string }) {
  return (
    <svg width="12" height="11" viewBox="0 0 12 11" fill="none" className={className} aria-hidden>
      <path d="M6 0V11M0 5.5H12" stroke="currentColor" />
    </svg>
  );
}

export function SiteHeader() {
  const pathname = usePathname();
  const isMapPage = pathname === "/map";
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
      <header
        className={
          isMapPage
            ? "relative z-20 bg-transparent text-white [&_a]:text-white [&_a]:border-white/30 [&_a:hover]:bg-white/10 [&_button]:text-white [&_button]:border-white/30 [&_button:hover]:bg-white/10"
            : ""
        }
      >
        <div className="flex items-center justify-between px-4 py-4 md:px-8 md:py-5">
          <Link
            href="/"
            className="inline-block text-sm font-bold tracking-tight text-foreground hover:opacity-80 origin-left scale-[1.2]"
          >
            <span className="font-spectral-italic-logo italic font-normal text-base pr-[0.5px]">the</span>tattoo
            <span className="font-spectral-italic-logo italic font-normal text-base">.world</span>
          </Link>
          <div className="flex items-center gap-2">
            {!isMapPage && (
              <Link
                href="/map"
                className="flex items-center gap-1.5 h-[26px] text-xs rounded bg-black text-white border border-transparent px-3 hover:bg-black/80 transition-colors whitespace-nowrap"
              >
                <GlobeIcon className="w-3.5 h-3.5 shrink-0" />
                On Map
              </Link>
            )}
            <button
              type="button"
              onClick={() => setSuggestOpen(true)}
              className="flex items-center gap-1.5 h-[26px] text-xs rounded border border-border px-3 text-foreground hover:bg-secondary transition-colors whitespace-nowrap"
            >
              <PlusIcon className="w-3 h-3 shrink-0" />
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
                className="flex items-center justify-center h-[26px] text-xs rounded border border-border px-3 text-foreground hover:bg-secondary transition-colors whitespace-nowrap"
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
