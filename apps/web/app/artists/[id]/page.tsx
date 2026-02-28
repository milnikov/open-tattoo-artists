import { getArtist } from "@/lib/data";
import { imageUrl } from "@/lib/images";
import Link from "next/link";
import { notFound } from "next/navigation";

export default function ArtistPage({ params }: { params: { id: string } }) {
  const artist = getArtist(params.id);
  if (!artist) notFound();

  const reportUrl = `https://github.com/YOUR_ORG/YOUR_REPO/issues/new?template=report-problem.md&title=Report+problem%3A+${encodeURIComponent(artist.name)}&labels=report&artist_id=${artist.id}`;

  return (
    <div>
      <Link href="/" className="text-blue-600 hover:underline mb-4 inline-block">
        ← Back to directory
      </Link>
      <div className="border bg-white rounded-lg p-6 mb-6">
        <h1 className="text-2xl font-bold">{artist.name}</h1>
        <p className="text-gray-600 mt-1">
          {artist.location.city}, {artist.location.country}
        </p>
        {artist.styles.length > 0 && (
          <p className="text-sm text-gray-500 mt-2">
            Styles: {artist.styles.join(", ")}
          </p>
        )}
        <div className="flex gap-4 mt-4">
          <a
            href={artist.links.instagram}
            target="_blank"
            rel="noopener noreferrer"
            className="text-blue-600 hover:underline"
          >
            Instagram
          </a>
          {artist.links.website && (
            <a
              href={artist.links.website}
              target="_blank"
              rel="noopener noreferrer"
              className="text-blue-600 hover:underline"
            >
              Website
            </a>
          )}
          {artist.links.source && (
            <a
              href={artist.links.source}
              target="_blank"
              rel="noopener noreferrer"
              className="text-gray-500 text-sm hover:underline"
            >
              Source
            </a>
          )}
        </div>
        <div className="mt-4 flex gap-2">
          <a
            href={reportUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="text-sm px-3 py-1 border rounded hover:bg-gray-50"
          >
            Report problem
          </a>
        </div>
      </div>
      <h2 className="text-lg font-semibold mb-4">Gallery</h2>
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
        {artist.tattoos.map((t) => (
          <a
            key={t.image_id}
            href={imageUrl(t.image_full)}
            target="_blank"
            rel="noopener noreferrer"
            className="block aspect-square rounded overflow-hidden bg-gray-200"
          >
            <img
              src={imageUrl(t.image_thumb)}
              alt={`${artist.name} tattoo ${t.image_id}`}
              className="w-full h-full object-cover hover:opacity-90 transition"
            />
          </a>
        ))}
      </div>
    </div>
  );
}
