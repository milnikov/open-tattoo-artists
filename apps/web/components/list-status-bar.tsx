"use client";

import { ChevronLeft, ChevronRight } from "lucide-react";

interface ListStatusBarProps {
  totalCount: number;
  page: number;
  totalPages: number;
  onPageChange: (page: number) => void;
  /** "top" = bar above list (border-b only). "bottom" = bar below list (border-t only, no border-b to avoid double line with footer). */
  variant?: "top" | "bottom";
}

export function ListStatusBar({
  totalCount,
  page,
  totalPages,
  onPageChange,
  variant = "top",
}: ListStatusBarProps) {
  const borderClass =
    variant === "bottom"
      ? "border-t border-border"
      : "border-b border-border";

  return (
    <div
      className={`flex items-center justify-between px-4 md:px-8 h-9 ${borderClass}`}
    >
      <span className="text-xs text-muted-foreground">
        {totalCount} artists{" "}
        {totalPages > 0 && (
          <>
            {"—"} page {page + 1} of {totalPages}
          </>
        )}
      </span>
      {totalPages > 1 && (
        <div className="flex items-center gap-2.5">
          <button
            type="button"
            onClick={() => {
              onPageChange(Math.max(0, page - 1));
              window.scrollTo({ top: 0, behavior: "smooth" });
            }}
            disabled={page === 0}
            className="rounded text-muted-foreground hover:text-foreground disabled:opacity-25 transition-colors"
            aria-label="Previous page"
          >
            <ChevronLeft className="h-3.5 w-3.5" />
          </button>
          <button
            type="button"
            onClick={() => {
              onPageChange(Math.min(totalPages - 1, page + 1));
              window.scrollTo({ top: 0, behavior: "smooth" });
            }}
            disabled={page === totalPages - 1}
            className="rounded text-muted-foreground hover:text-foreground disabled:opacity-25 transition-colors"
            aria-label="Next page"
          >
            <ChevronRight className="h-3.5 w-3.5" />
          </button>
        </div>
      )}
    </div>
  );
}
