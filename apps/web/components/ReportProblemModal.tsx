"use client";

import { reportProblem, type ReportProblemResult } from "@/app/actions/report-problem";
import { REPORT_PROBLEM_OPTIONS } from "@/lib/report-problem-options";
import { X } from "lucide-react";
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

  const cancelButtonClass =
    "flex items-center justify-center h-[26px] text-xs rounded border border-border px-3 text-foreground hover:bg-secondary transition-colors whitespace-nowrap";
  const submitButtonClass =
    "text-xs rounded border px-3 py-1 whitespace-nowrap transition-colors disabled:cursor-not-allowed " +
    "enabled:bg-foreground enabled:text-background enabled:border-foreground enabled:hover:opacity-90 " +
    "disabled:opacity-50 disabled:bg-transparent disabled:text-foreground disabled:border-border";

  if (result?.ok) {
    return (
      <div
        className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50"
        onClick={onClose}
      >
        <div
          className="bg-background text-foreground rounded-lg shadow-xl max-w-sm w-full px-4 py-4 border border-border text-xs"
          onClick={(e) => e.stopPropagation()}
        >
          <div className="flex justify-between items-center mb-3">
            <h2 className="text-sm font-bold text-foreground">Request submitted</h2>
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
            Your update request was submitted successfully. We will process it soon.
          </p>
          <div className="flex gap-2 justify-end">
            <a
              href="/profile"
              className={cancelButtonClass}
            >
              Show in profile
            </a>
            <button type="button" onClick={onClose} className={cancelButtonClass}>
              Great
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50"
      onClick={onClose}
    >
      <div
        className="bg-background text-foreground rounded-lg shadow-xl max-w-md w-full max-h-[90vh] overflow-y-auto px-4 py-3 border border-border text-xs"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-sm font-bold text-foreground">Request update</h2>
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
          We’ll create an update request and add it to your Contributions for: <strong className="text-foreground">{artistName}</strong>
        </p>
        {result && !result.ok && (
          <div className="mb-4 p-3 rounded-lg bg-red-50 dark:bg-red-950/30 text-red-700 dark:text-red-300">
            {result.error}
          </div>
        )}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <span className="block font-medium text-foreground mb-2">What needs updating? *</span>
            <div className="space-y-2">
              {REPORT_PROBLEM_OPTIONS.map((opt) => (
                <label key={opt.value} className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={whatWrong.includes(opt.value)}
                    onChange={() => toggleOption(opt.value)}
                    className="rounded border-border text-foreground"
                  />
                  <span className="text-foreground">{opt.label}</span>
                </label>
              ))}
            </div>
          </div>
          <div>
            <label htmlFor="report-description" className="block font-medium text-foreground mb-1">
              Describe what should be updated *
            </label>
            <textarea
              id="report-description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              required
              rows={3}
              className="w-full border border-border rounded px-3 py-2 bg-background text-foreground"
              placeholder="What should be changed?"
            />
          </div>
          <div>
            <label htmlFor="report-fix" className="block font-medium text-foreground mb-1">
              Suggested correction (optional)
            </label>
            <textarea
              id="report-fix"
              value={suggestedFix}
              onChange={(e) => setSuggestedFix(e.target.value)}
              rows={2}
              className="w-full border border-border rounded px-3 py-2 bg-background text-foreground"
              placeholder="Correct location, links, etc."
            />
          </div>
          <div className="flex gap-2 justify-end">
            <button type="button" onClick={onClose} className={cancelButtonClass}>
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading || whatWrong.length === 0}
              className={submitButtonClass}
            >
              {loading ? "Submitting…" : "Submit request"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
