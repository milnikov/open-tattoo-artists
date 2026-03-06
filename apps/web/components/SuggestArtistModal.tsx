"use client";

import { suggestArtist, type SuggestArtistResult } from "@/app/actions/suggest-artist";
import { X } from "lucide-react";
import { useState } from "react";

type Props = { onClose: () => void; open: boolean };

export function SuggestArtistModal({ onClose, open }: Props) {
  const [artistName, setArtistName] = useState("");
  const [profileUrl, setProfileUrl] = useState("");
  const [notes, setNotes] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<SuggestArtistResult | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setResult(null);
    const res = await suggestArtist(artistName, profileUrl, notes);
    setResult(res);
    setLoading(false);
    if (res.ok) {
      setArtistName("");
      setProfileUrl("");
      setNotes("");
    }
  }

  if (!open) return null;

  const cancelButtonClass =
    "text-xs rounded border border-border px-3 py-1 text-foreground hover:bg-secondary transition-colors whitespace-nowrap";
  const submitButtonClass =
    "text-xs rounded border px-3 py-1 whitespace-nowrap transition-colors disabled:cursor-not-allowed " +
    "enabled:bg-foreground enabled:text-background enabled:border-foreground enabled:hover:opacity-90 " +
    "disabled:opacity-50 disabled:bg-transparent disabled:text-foreground disabled:border-border";

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50" onClick={onClose}>
      <div
        className="bg-background text-foreground rounded-lg shadow-xl max-w-md w-full max-h-[90vh] overflow-y-auto px-4 py-3 border border-border text-xs"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-sm font-bold text-foreground">Suggest an artist</h2>
          <button
            type="button"
            onClick={onClose}
            className="rounded text-muted-foreground hover:text-foreground transition-colors"
            aria-label="Close"
          >
            <X className="h-3.5 w-3.5" />
          </button>
        </div>
        <p className="text-muted-foreground mb-4">
          We’ll create a GitHub issue. Once the artist is added to the directory, it will appear in your Contributions.
        </p>
        {result?.ok && (
          <div className="mb-4 p-3 rounded-lg bg-green-50 dark:bg-green-950/30 text-green-800 dark:text-green-200">
            Issue created.{" "}
            <a href={result.issueUrl} target="_blank" rel="noopener noreferrer" className="underline">
              Open issue
            </a>
          </div>
        )}
        {result && !result.ok && (
          <div className="mb-4 p-3 rounded-lg bg-red-50 dark:bg-red-950/30 text-red-700 dark:text-red-300">
            {result.error}
          </div>
        )}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="artist-name" className="block font-medium text-foreground mb-1">
              Artist name *
            </label>
            <input
              id="artist-name"
              type="text"
              value={artistName}
              onChange={(e) => setArtistName(e.target.value)}
              required
              className="w-full border border-border rounded px-3 py-2 bg-background text-foreground"
              placeholder="e.g. Jane Doe"
            />
          </div>
          <div>
            <label htmlFor="profile-url" className="block font-medium text-foreground mb-1">
              Profile URL *
            </label>
            <input
              id="profile-url"
              type="url"
              value={profileUrl}
              onChange={(e) => setProfileUrl(e.target.value)}
              required
              className="w-full border border-border rounded px-3 py-2 bg-background text-foreground"
              placeholder="https://www.tattoodo.com/artists/..."
            />
          </div>
          <div>
            <label htmlFor="notes" className="block font-medium text-foreground mb-1">
              Notes (optional)
            </label>
            <textarea
              id="notes"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              rows={3}
              className="w-full border border-border rounded px-3 py-2 bg-background text-foreground"
              placeholder="Style, location, or anything that helps us add them."
            />
          </div>
          <div className="flex gap-2 justify-end">
            <button type="button" onClick={onClose} className={cancelButtonClass}>
              Cancel
            </button>
            <button type="submit" disabled={loading} className={submitButtonClass}>
              {loading ? "Creating…" : "Create issue"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
