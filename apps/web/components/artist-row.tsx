"use client";

import Link from "next/link";
import type { CompactArtist } from "@/lib/data";
import { imageUrl } from "@/lib/images";

interface ArtistRowProps {
  artist: CompactArtist;
  index: number;
  onTagClick?: (style: string) => void;
  onCountryClick?: (country: string) => void;
  onCityClick?: (city: string, country: string) => void;
  isFirst?: boolean;
}

function generateAboutText(artist: CompactArtist): string {
  const { name, location, styles } = artist;
  const city = location.city;
  const styleList = styles.slice(0, 3);
  const styleText =
    styleList.length > 1
      ? `${styleList.slice(0, -1).join(", ")} and ${styleList[styleList.length - 1]}`
      : styleList[0] || "mixed styles";
  if (city) {
    return `${name} is based in ${city}, ${location.country}, specializing in ${styleText} tattoos.`;
  }
  return `${name} specializes in ${styleText} tattoos.`;
}

export function ArtistRow({
  artist,
  index,
  onTagClick,
  onCountryClick,
  onCityClick,
  isFirst,
}: ArtistRowProps) {
  const aboutText = generateAboutText(artist);
  const hasCity = !!artist.location.city;
  const hasCountry = !!artist.location.country;
  const thumbs =
    (artist.thumbs?.length ?? 0) > 0
      ? artist.thumbs
      : artist.thumb
        ? [artist.thumb]
        : [];
  const thumbsToShow = thumbs.slice(0, 4);

  return (
    <div className={isFirst ? "" : "border-t border-border"}>
      <Link
        href={`/artists/${artist.id}`}
        className="block hover:bg-muted/50 transition-colors"
      >
        <div className="grid grid-cols-1 md:grid-cols-[40px_minmax(0,0.5fr)_minmax(0,1.2fr)_120px_346px] gap-4 md:gap-6 px-4 py-6 md:px-8 md:py-8 items-start">
          <span className="hidden md:block text-xs text-muted-foreground tabular-nums pt-0.5">
            {String(index + 1).padStart(3, "0")}
          </span>

          <div className="flex flex-col gap-1 min-w-0">
            <h3 className="text-sm font-bold text-foreground leading-tight">
              <span className="md:hidden text-xs font-normal text-muted-foreground mr-2">
                {String(index + 1).padStart(3, "0")}
              </span>
              {artist.name}
            </h3>
            {artist.tattoo_count > 0 && (
              <span className="text-xs text-muted-foreground">
                {artist.tattoo_count} tattoo{artist.tattoo_count !== 1 ? "s" : ""}
              </span>
            )}
          </div>

          <div className="flex flex-col gap-3 text-xs min-w-0">
            <span className="text-foreground leading-relaxed line-clamp-3">{aboutText}</span>
            <span className="text-muted-foreground">
              {hasCity ? (
                <span
                  role="button"
                  tabIndex={0}
                  onClick={(e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    onCityClick?.(artist.location.city, artist.location.country);
                  }}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" || e.key === " ") {
                      e.preventDefault();
                      e.stopPropagation();
                      onCityClick?.(artist.location.city, artist.location.country);
                    }
                  }}
                  className="hover:text-foreground transition-colors cursor-pointer"
                >
                  {artist.location.city}
                </span>
              ) : null}
              {hasCity && hasCountry ? ", " : ""}
              {hasCountry ? (
                <span
                  role="button"
                  tabIndex={0}
                  onClick={(e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    onCountryClick?.(artist.location.country);
                  }}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" || e.key === " ") {
                      e.preventDefault();
                      e.stopPropagation();
                      onCountryClick?.(artist.location.country);
                    }
                  }}
                  className="hover:text-foreground transition-colors cursor-pointer"
                >
                  {artist.location.country}
                </span>
              ) : (
                "—"
              )}
            </span>
          </div>

          <div className="flex flex-wrap gap-x-1.5 gap-y-0.5 text-xs">
            {artist.styles.map((style, i) => (
              <span key={style} className="inline">
                <span
                  role="button"
                  tabIndex={0}
                  onClick={(e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    onTagClick?.(style);
                  }}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" || e.key === " ") {
                      e.preventDefault();
                      e.stopPropagation();
                      onTagClick?.(style);
                    }
                  }}
                  className="text-muted-foreground hover:text-foreground transition-colors cursor-pointer"
                >
                  {style}
                </span>
                {i < artist.styles.length - 1 && (
                  <span className="text-muted-foreground">,</span>
                )}
              </span>
            ))}
          </div>

          <div className="flex flex-col gap-2">
            <div className="flex gap-1.5">
              {thumbsToShow.map((src, i) => (
                <div
                  key={i}
                  className="w-[72px] h-[96px] md:w-[80px] md:h-[108px] bg-muted overflow-hidden shrink-0"
                >
                  <img
                    src={imageUrl(src)}
                    alt={`Work by ${artist.name}`}
                    className="w-full h-full object-cover"
                    loading="lazy"
                  />
                </div>
              ))}
            </div>
            {artist.tattoo_count > thumbsToShow.length && (
              <span className="text-xs text-muted-foreground text-right">
                {artist.tattoo_count - thumbsToShow.length} more in gallery
              </span>
            )}
          </div>
        </div>
      </Link>
    </div>
  );
}
