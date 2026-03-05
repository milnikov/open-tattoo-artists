import { getArtist } from "@/lib/data";
import { getContributorEmailForArtist } from "@/lib/contributions";
import { imageUrl } from "@/lib/images";
import Link from "next/link";
import { notFound } from "next/navigation";
import { FavoriteButton } from "@/components/FavoriteButton";
import { ReportProblemButton } from "@/components/ReportProblemButton";

export default async function ArtistPage({ params }: { params: { id: string } }) {
  const artist = getArtist(params.id);
  if (!artist) notFound();

  const contributorEmail = await getContributorEmailForArtist(params.id);

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      <Link href="/" className="text-foreground hover:text-muted-foreground mb-4 inline-block text-sm">
        ← Back to directory
      </Link>
      <div className="border border-border bg-card rounded-lg p-6 mb-6">
        <h1 className="text-2xl font-bold text-foreground">{artist.name}</h1>
        {contributorEmail && (
          <p className="text-sm text-muted-foreground mt-1">
            Contributed by {contributorEmail}
          </p>
        )}
        <p className="text-muted-foreground mt-1">
          {artist.location.city}, {artist.location.country}
        </p>
        {artist.styles.length > 0 && (
          <p className="text-sm text-muted-foreground mt-2">
            Styles: {artist.styles.join(", ")}
          </p>
        )}
        {artist.bio && (
          <div className="mt-3 text-muted-foreground text-sm whitespace-pre-line max-w-2xl">
            {artist.bio.replace(/\nPrice:[\s\S]*$/, "").trim()}
          </div>
        )}
        <div className="flex gap-4 mt-4">
          <a
            href={artist.links.instagram}
            target="_blank"
            rel="noopener noreferrer"
            className="text-foreground hover:text-muted-foreground underline"
          >
            Instagram
          </a>
        </div>
        <div className="mt-4 flex flex-wrap gap-2 items-center">
          <FavoriteButton artistId={artist.id} />
          <ReportProblemButton
            artistId={artist.id}
            artistName={artist.name}
            instagramUrl={artist.links.instagram}
          />
        </div>
      </div>
      <h2 className="text-lg font-semibold text-foreground mb-4">Gallery</h2>
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
        {artist.tattoos.map((t) => (
          <a
            key={t.image_id}
            href={imageUrl(t.image_full)}
            target="_blank"
            rel="noopener noreferrer"
            className="block aspect-square rounded overflow-hidden bg-muted"
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
