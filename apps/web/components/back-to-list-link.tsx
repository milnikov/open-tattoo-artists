"use client";

import { useRouter } from "next/navigation";
import { ArrowLeft } from "lucide-react";

export function BackToListLink() {
  const router = useRouter();

  return (
    <button
      type="button"
      onClick={() => {
        if (typeof window !== "undefined" && window.history.length > 1) {
          router.back();
        } else {
          router.push("/");
        }
      }}
      className="inline-flex items-center gap-1 text-xs text-foreground hover:text-muted-foreground transition-colors"
    >
      <ArrowLeft className="h-3 w-3 shrink-0" />
      Back to List
    </button>
  );
}
