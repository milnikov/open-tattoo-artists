import { Suspense } from "react";
import { getCompactArtists, getAllowedCountryNames } from "@/lib/data";
import { ArtistListPage } from "@/components/artist-list-page";

function ArtistListPageFallback() {
  return (
    <div className="flex flex-col items-center justify-center py-32 px-4">
      <p className="text-muted-foreground">Loading…</p>
    </div>
  );
}

export default async function HomePage() {
  const [artists, allowedCountryNames] = await Promise.all([
    getCompactArtists(),
    Promise.resolve(getAllowedCountryNames()),
  ]);

  if (artists.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-32 px-4">
        <p className="text-muted-foreground">No artists yet.</p>
        <p className="text-sm text-muted-foreground mt-2">
          Run the scraper pipeline to populate data.
        </p>
      </div>
    );
  }

  return (
    <Suspense fallback={<ArtistListPageFallback />}>
      <ArtistListPage
        artists={artists}
        allowedCountryNames={allowedCountryNames}
      />
    </Suspense>
  );
}
