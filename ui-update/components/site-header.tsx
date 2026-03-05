"use client"

import { User } from "lucide-react"

export function SiteHeader() {
  return (
    <header>
      <div className="flex items-center justify-between px-4 py-4 md:px-8 md:py-5">
        <h1 className="text-sm font-bold tracking-tight text-foreground">
          Open Tattoo Artists
        </h1>
        <div className="flex items-center gap-2">
          <button className="text-xs border border-border px-3 py-1 text-foreground hover:bg-secondary transition-colors">
            Add Artist
          </button>
          <button
            className="flex shrink-0 items-center justify-center w-7 h-7 aspect-square rounded-full border border-border text-foreground hover:bg-secondary transition-colors"
            aria-label="User profile"
          >
            <User className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>
    </header>
  )
}
