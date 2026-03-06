"use client";

import { useState } from "react";
import { ReportProblemModal } from "./ReportProblemModal";

type Props = {
  artistId: string;
  artistName: string;
  instagramUrl: string;
  variant?: "default" | "muted";
};

export function ReportProblemButton({
  artistId,
  artistName,
  instagramUrl,
  variant = "default",
}: Props) {
  const [open, setOpen] = useState(false);
  const isMuted = variant === "muted";
  const buttonClass = isMuted
    ? "text-xs text-muted-foreground hover:text-foreground transition-colors inline-flex items-center gap-1.5"
    : "text-xs rounded border border-border px-3 py-1 text-foreground hover:bg-secondary transition-colors whitespace-nowrap inline-flex items-center gap-1.5";

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className={buttonClass}
      >
        Request update
      </button>
      <ReportProblemModal
        open={open}
        onClose={() => setOpen(false)}
        artistId={artistId}
        artistName={artistName}
        instagramUrl={instagramUrl}
      />
    </>
  );
}
