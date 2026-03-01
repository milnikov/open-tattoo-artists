"use client";

import { useState } from "react";
import Link from "next/link";
import { SuggestArtistModal } from "./SuggestArtistModal";

export function Header() {
  const [suggestOpen, setSuggestOpen] = useState(false);

  return (
    <>
      <nav className="border-b bg-white">
        <div className="mx-auto max-w-6xl px-4 py-3 flex items-center justify-between">
          <Link href="/" className="text-xl font-bold">
            Open Tattoo Artists
          </Link>
          <div className="flex items-center gap-4">
            <Link href="/" className="hover:underline">
              Directory
            </Link>
            <button
              type="button"
              onClick={() => setSuggestOpen(true)}
              className="hover:underline"
            >
              Suggest artist
            </button>
            <Link href="/profile" className="hover:underline">
              Profile
            </Link>
          </div>
        </div>
      </nav>
      <SuggestArtistModal open={suggestOpen} onClose={() => setSuggestOpen(false)} />
    </>
  );
}
