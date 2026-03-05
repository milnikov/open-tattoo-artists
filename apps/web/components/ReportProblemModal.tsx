"use client";

import { reportProblem, type ReportProblemResult } from "@/app/actions/report-problem";
import { REPORT_PROBLEM_OPTIONS } from "@/lib/report-problem-options";
import { useState } from "react";

function getInstagramHandle(url: string): string {
  if (!url) return "";
  const match = url.replace(/^.*instagram\.com\/?/, "").replace(/\/.*$/, "").trim();
  return match ? `@${match}` : "";
}

type Props = {
  open: boolean;
  onClose: () => void;
  artistId: string;
  artistName: string;
  instagramUrl: string;
};

export function ReportProblemModal({
  open,
  onClose,
  artistId,
  artistName,
  instagramUrl,
}: Props) {
  const [whatWrong, setWhatWrong] = useState<string[]>([]);
  const [description, setDescription] = useState("");
  const [suggestedFix, setSuggestedFix] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<ReportProblemResult | null>(null);

  const instagramHandle = getInstagramHandle(instagramUrl);

  function toggleOption(value: string) {
    setWhatWrong((prev) =>
      prev.includes(value) ? prev.filter((v) => v !== value) : [...prev, value]
    );
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setResult(null);
    const artistPageUrl =
      typeof window !== "undefined" ? `${window.location.origin}/artists/${artistId}` : "";
    const res = await reportProblem(
      artistId,
      artistName,
      artistPageUrl,
      instagramHandle,
      whatWrong,
      description,
      suggestedFix || undefined
    );
    setResult(res);
    setLoading(false);
    if (res.ok) {
      setWhatWrong([]);
      setDescription("");
      setSuggestedFix("");
    }
  }

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50"
      onClick={onClose}
    >
      <div
        className="bg-white rounded-lg shadow-xl max-w-md w-full max-h-[90vh] overflow-y-auto p-6"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-xl font-bold">Report a problem</h2>
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
          We’ll create a GitHub issue and add it to your Contributions. This artist: <strong>{artistName}</strong>
        </p>
        {result?.ok && (
          <div className="mb-4 p-3 rounded-lg bg-green-50 text-green-800 text-sm">
            Report submitted.{" "}
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
            <span className="block text-sm font-medium text-gray-700 mb-2">What&apos;s wrong? *</span>
            <div className="space-y-2">
              {REPORT_PROBLEM_OPTIONS.map((opt) => (
                <label key={opt.value} className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={whatWrong.includes(opt.value)}
                    onChange={() => toggleOption(opt.value)}
                    className="rounded border-gray-300"
                  />
                  <span className="text-sm">{opt.label}</span>
                </label>
              ))}
            </div>
          </div>
          <div>
            <label htmlFor="report-description" className="block text-sm font-medium text-gray-700 mb-1">
              Describe the issue *
            </label>
            <textarea
              id="report-description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              required
              rows={3}
              className="w-full border border-gray-300 rounded-lg px-3 py-2"
              placeholder="What should be changed?"
            />
          </div>
          <div>
            <label htmlFor="report-fix" className="block text-sm font-medium text-gray-700 mb-1">
              Suggested fix (optional)
            </label>
            <textarea
              id="report-fix"
              value={suggestedFix}
              onChange={(e) => setSuggestedFix(e.target.value)}
              rows={2}
              className="w-full border border-gray-300 rounded-lg px-3 py-2"
              placeholder="Correct location, links, etc."
            />
          </div>
          <div className="flex gap-2 justify-end">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-gray-700 hover:bg-gray-100 rounded-lg"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading || whatWrong.length === 0}
              className="px-4 py-2 bg-gray-900 text-white rounded-lg hover:bg-gray-800 disabled:opacity-50"
            >
              {loading ? "Submitting…" : "Submit report"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
