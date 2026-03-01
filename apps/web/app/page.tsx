import { getCompactArtists } from "@/lib/data";
import { getContributorMap } from "@/lib/contributions";
import { ArtistListWithFilters } from "@/components/ArtistListWithFilters";

export default async function HomePage() {
  const [artists, contributorMap] = await Promise.all([
    getCompactArtists(),
    getContributorMap(),
  ]);

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Artist Directory</h1>
      {artists.length === 0 ? (
        <p className="text-gray-500 py-12 text-center">
          No artists yet. Run the scraper pipeline to populate data.
        </p>
      ) : (
        <ArtistListWithFilters artists={artists} contributorMap={contributorMap} />
      )}
    </div>
  );
}
