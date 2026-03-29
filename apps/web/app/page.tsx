import { Suspense } from "react";
import { getAllowedCountryNames } from "@/lib/data";
import { ArtistListPage } from "@/components/artist-list-page";

/**
 * Cache the small server shell (country allowlist only). Artist rows load via
 * /api/artists/compact on the client so the ISR payload stays under Vercel’s limit
 * (full compact JSON serialized into RSC was ~19MB).
 */
export const revalidate = 3600;

function ArtistListPageFallback() {
  return (
    <div className="flex flex-col items-center justify-center py-32 px-4">
      <p className="text-muted-foreground">Loading…</p>
    </div>
  );
}

export default function HomePage() {
  const allowedCountryNames = getAllowedCountryNames();
  return (
    <Suspense fallback={<ArtistListPageFallback />}>
      <ArtistListPage allowedCountryNames={allowedCountryNames} />
    </Suspense>
  );
}
