"use client";

import { useState } from "react";
import { ReportProblemModal } from "./ReportProblemModal";

type Props = {
  artistId: string;
  artistName: string;
  instagramUrl: string;
};

export function ReportProblemButton({ artistId, artistName, instagramUrl }: Props) {
  const [open, setOpen] = useState(false);

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="text-sm px-3 py-1.5 border rounded hover:bg-gray-50"
      >
        Report problem
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
