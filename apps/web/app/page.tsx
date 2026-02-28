import { getCompactArtists } from "@/lib/data";
import Link from "next/link";
import { imageUrl } from "@/lib/images";

export default function HomePage() {
  const artists = getCompactArtists();

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Artist Directory</h1>
      <p className="text-gray-600 mb-6">
        {artists.length} artists
      </p>
      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6">
        {artists.map((a) => (
          <Link
            key={a.id}
            href={`/artists/${a.id}`}
            className="block border bg-white rounded-lg overflow-hidden hover:shadow-md transition"
          >
            <div className="aspect-square bg-gray-200 relative overflow-hidden">
              {a.thumb ? (
                <img
                  src={imageUrl(a.thumb)}
                  alt={a.name}
                  className="w-full h-full object-cover"
                />
              ) : (
                <div className="w-full h-full flex items-center justify-center text-gray-400">
                  {a.tattoo_count > 0 ? (
                    <span className="text-sm">{a.tattoo_count} images</span>
                  ) : (
                    <span>No image</span>
                  )}
                </div>
              )}
            </div>
            <div className="p-3">
              <h2 className="font-semibold truncate">{a.name}</h2>
              <p className="text-sm text-gray-600 truncate">
                {a.location.city}, {a.location.country}
              </p>
              {a.styles.length > 0 && (
                <p className="text-xs text-gray-500 mt-1">
                  {a.styles.slice(0, 3).join(", ")}
                </p>
              )}
            </div>
          </Link>
        ))}
      </div>
      {artists.length === 0 && (
        <p className="text-gray-500 py-12 text-center">
          No artists yet. Run the scraper pipeline to populate data.
        </p>
      )}
    </div>
  );
}
