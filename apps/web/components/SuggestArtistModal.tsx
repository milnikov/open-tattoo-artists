"use client";

import { suggestArtist, type SuggestArtistResult } from "@/app/actions/suggest-artist";
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

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50" onClick={onClose}>
      <div
        className="bg-white rounded-lg shadow-xl max-w-md w-full p-6"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-xl font-bold">Suggest an artist</h2>
          <button
            type="button"
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 text-2xl leading-none"
            aria-label="Close"
          >
            ×
          </button>
        </div>
        <p className="text-gray-600 text-sm mb-4">
          We’ll create a GitHub issue. Once the artist is added to the directory, it will appear in your Contributions.
        </p>
        {result?.ok && (
          <div className="mb-4 p-3 rounded-lg bg-green-50 text-green-800 text-sm">
            Issue created.{" "}
            <a href={result.issueUrl} target="_blank" rel="noopener noreferrer" className="underline">
              Open issue
            </a>
          </div>
        )}
        {result && !result.ok && (
          <div className="mb-4 p-3 rounded-lg bg-red-50 text-red-700 text-sm">
            {result.error}
          </div>
        )}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="artist-name" className="block text-sm font-medium text-gray-700 mb-1">
              Artist name *
            </label>
            <input
              id="artist-name"
              type="text"
              value={artistName}
              onChange={(e) => setArtistName(e.target.value)}
              required
              className="w-full border border-gray-300 rounded-lg px-3 py-2"
              placeholder="e.g. Jane Doe"
            />
          </div>
          <div>
            <label htmlFor="profile-url" className="block text-sm font-medium text-gray-700 mb-1">
              Profile URL *
            </label>
            <input
              id="profile-url"
              type="url"
              value={profileUrl}
              onChange={(e) => setProfileUrl(e.target.value)}
              required
              className="w-full border border-gray-300 rounded-lg px-3 py-2"
              placeholder="https://www.tattoodo.com/artists/..."
            />
          </div>
          <div>
            <label htmlFor="notes" className="block text-sm font-medium text-gray-700 mb-1">
              Notes (optional)
            </label>
            <textarea
              id="notes"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              rows={3}
              className="w-full border border-gray-300 rounded-lg px-3 py-2"
              placeholder="Style, location, or anything that helps us add them."
            />
          </div>
          <div className="flex gap-2 justify-end">
            <button type="button" onClick={onClose} className="px-4 py-2 text-gray-700 hover:bg-gray-100 rounded-lg">
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="px-4 py-2 bg-gray-900 text-white rounded-lg hover:bg-gray-800 disabled:opacity-50"
            >
              {loading ? "Creating…" : "Create issue"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
