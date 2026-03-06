import Link from "next/link";
import { getArtist } from "@/lib/data";
import { getContributorEmailForArtist } from "@/lib/contributions";
import { imageUrl } from "@/lib/images";
import { notFound } from "next/navigation";
import { ArrowUpRight } from "lucide-react";
import { FavoriteButton } from "@/components/FavoriteButton";
import { BackToListLink } from "@/components/back-to-list-link";
import { ReportProblemButton } from "@/components/ReportProblemButton";
import { SiteFooter } from "@/components/site-footer";

function listUrl(params: { styles?: string[]; countries?: string[]; cities?: string[] }) {
  const searchParams = new URLSearchParams();
  if (params.styles?.length) searchParams.set("styles", params.styles.map(encodeURIComponent).join(","));
  if (params.countries?.length) searchParams.set("countries", params.countries.map(encodeURIComponent).join(","));
  if (params.cities?.length) searchParams.set("cities", params.cities.map(encodeURIComponent).join(","));
  const qs = searchParams.toString();
  return qs ? `/?${qs}` : "/";
}

const HEADER_BUTTON_CLASS =
  "text-xs rounded border border-border px-3 py-1 text-foreground hover:bg-secondary transition-colors whitespace-nowrap inline-flex items-center gap-1.5";

export default async function ArtistPage({ params }: { params: { id: string } }) {
  const artist = getArtist(params.id);
  if (!artist) notFound();

  const contributorEmail = await getContributorEmailForArtist(params.id);
  const bioText = artist.bio?.replace(/\nPrice:[\s\S]*$/, "").trim() ?? "";

  return (
    <div className="min-h-screen flex flex-col bg-background text-foreground min-w-0">
      <div className="h-8 md:h-16" />
      <div className="sticky top-0 z-10 bg-background flex items-center px-4 md:px-8 h-9 border-b border-border">
        <BackToListLink />
      </div>

      <main className="flex-1 min-w-0 overflow-x-hidden">
      {/* Head block: 4 cols on md = 1fr | 3fr | 1fr gap | 1fr; 2 rows so buttons align */}
      <div className="grid grid-cols-1 md:grid-cols-[1fr_3fr_1fr_1fr] md:grid-rows-[auto_auto] gap-4 md:gap-y-6 md:gap-x-0 px-4 py-6 md:px-8 md:py-8 min-w-0">
        <div className="flex flex-col gap-1 min-w-0 md:row-start-1 md:col-start-1">
          <h1 className="text-sm font-bold text-foreground leading-tight">
            {artist.name}
          </h1>
          <span className="text-xs text-muted-foreground">
            {artist.location.city && artist.location.country ? (
              <>
                <Link
                  href={listUrl({
                    countries: [artist.location.country],
                    cities: [artist.location.city],
                  })}
                  className="text-muted-foreground"
                >
                  {artist.location.city}
                </Link>
                {", "}
                <Link
                  href={listUrl({ countries: [artist.location.country] })}
                  className="text-muted-foreground"
                >
                  {artist.location.country}
                </Link>
              </>
            ) : artist.location.city ? (
              <Link
                href={listUrl({ cities: [artist.location.city] })}
                className="text-muted-foreground"
              >
                {artist.location.city}
              </Link>
            ) : artist.location.country ? (
              <Link
                href={listUrl({ countries: [artist.location.country] })}
                className="text-muted-foreground"
              >
                {artist.location.country}
              </Link>
            ) : null}
          </span>
          {contributorEmail && (
            <span className="text-xs text-muted-foreground mt-1 block">
              Contributed by {contributorEmail}
            </span>
          )}
        </div>

        <div className="flex flex-col gap-1 text-xs min-w-0 md:row-start-1 md:col-start-2">
          {bioText && (
            <span className="text-foreground leading-relaxed whitespace-pre-line block">
              {bioText}
            </span>
          )}
        </div>

        <div className="hidden md:block md:row-start-1 md:col-start-3" aria-hidden />

        <div className="flex flex-col gap-y-0.5 text-xs min-w-0 md:row-start-1 md:col-start-4 md:items-end md:text-right">
          {artist.styles.map((style) => (
            <Link
              key={style}
              href={listUrl({ styles: [style] })}
              className="text-xs text-muted-foreground italic"
            >
              {style}
            </Link>
          ))}
        </div>

        <div className="hidden md:block md:row-start-2 md:col-start-1" aria-hidden />

        <div className="flex flex-wrap items-center gap-2 mt-1 md:mt-0 md:row-start-2 md:col-start-2 min-w-0">
          {artist.links.instagram && (
            <a
              href={artist.links.instagram}
              target="_blank"
              rel="noopener noreferrer"
              className={HEADER_BUTTON_CLASS + " w-fit"}
            >
              Instagram
              <ArrowUpRight className="h-3 w-3 shrink-0" />
            </a>
          )}
          <ReportProblemButton
            artistId={artist.id}
            artistName={artist.name}
            instagramUrl={artist.links.instagram}
          />
          {artist.updated_at && (
            <span className="text-xs text-muted-foreground shrink-0">
              Updated at: {artist.updated_at}
            </span>
          )}
        </div>

        <div className="hidden md:block md:row-start-2 md:col-start-3" aria-hidden />

        <div className="mt-2 md:mt-0 md:row-start-2 md:col-start-4 min-w-0 md:flex md:justify-end">
          <FavoriteButton artistId={artist.id} />
        </div>
      </div>

      <div className="border-t border-border px-2 pt-3 pb-4 md:px-8 md:pt-6 md:pb-8">
        <div className="columns-2 md:columns-3 gap-x-2 md:gap-x-4">
          {artist.tattoos.map((t) => (
            <a
              key={t.image_id}
              href={imageUrl(t.image_full)}
              target="_blank"
              rel="noopener noreferrer"
              className="block break-inside-avoid rounded overflow-hidden bg-muted hover:opacity-95 transition-opacity mb-2 md:mb-4"
            >
              <img
                src={imageUrl(t.image_thumb)}
                alt={`${artist.name} tattoo ${t.image_id}`}
                className="w-full h-auto block"
              />
            </a>
          ))}
        </div>
      </div>
      </main>

      <SiteFooter />
    </div>
  );
}
