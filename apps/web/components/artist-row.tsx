"use client";

import Link from "next/link";
import type { CompactArtist } from "@/lib/data";
import { artistFollowerCount } from "@/lib/artist-follower-count";
import { imageUrl } from "@/lib/images";

interface ArtistRowProps {
  artist: CompactArtist;
  index: number;
  onTagClick?: (style: string) => void;
  onCountryClick?: (country: string) => void;
  onCityClick?: (city: string, country: string) => void;
  isFirst?: boolean;
}

const BIO_EXCERPT_LENGTH = 120;

function getDescriptionExcerpt(artist: CompactArtist): string {
  const raw = artist.bio?.trim();
  if (raw && raw.length > 0) {
    if (raw.length <= BIO_EXCERPT_LENGTH) return raw;
    let cut = raw.slice(0, BIO_EXCERPT_LENGTH).trim();
    const lastSpace = cut.lastIndexOf(" ");
    if (lastSpace > BIO_EXCERPT_LENGTH * 0.6) cut = cut.slice(0, lastSpace);
    return `${cut.replace(/\.$/, "")}...`;
  }
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
  const descriptionText = getDescriptionExcerpt(artist);
  const followerCount = artistFollowerCount(artist);
  const hasCity = !!artist.location.city;
  const hasCountry = !!artist.location.country;
  const thumbs: string[] =
    (artist.thumbs?.length ?? 0) > 0
      ? (artist.thumbs ?? [])
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
        <div className="grid grid-cols-1 md:grid-cols-[40px_minmax(0,0.5fr)_minmax(0,1.2fr)_120px_346px] gap-4 md:gap-6 px-4 py-6 md:px-8 md:py-8 items-start min-w-0">
          <span className="hidden md:block text-xs text-muted-foreground tabular-nums pt-0.5">
            {String(index + 1).padStart(3, "0")}
          </span>

          <div className="flex flex-col gap-1 min-w-0">
            <div className="flex items-center justify-between gap-2">
              <h3 className="text-sm font-bold text-foreground leading-tight min-w-0">
                {artist.name}
              </h3>
              <span className="shrink-0 md:hidden text-xs font-normal text-muted-foreground tabular-nums">
                {String(index + 1).padStart(3, "0")}
              </span>
            </div>
            <span className="text-xs text-muted-foreground">
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
                  className="hover:text-foreground transition-colors cursor-pointer rounded"
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
                  className="hover:text-foreground transition-colors cursor-pointer rounded"
                >
                  {artist.location.country}
                </span>
              ) : (
                "—"
              )}
            </span>
          </div>

          <div className="flex flex-col gap-1 text-xs min-w-0">
            <span className="text-foreground leading-relaxed line-clamp-3">{descriptionText}</span>
            {followerCount > 0 ? (
              <span className="text-foreground">
                Followed by {followerCount.toLocaleString()}{" "}
                {followerCount === 1 ? "person" : "people"}
              </span>
            ) : null}
            {artist.updated_at && (
              <span className="text-xs text-muted-foreground">
                {artist.updated_at}
              </span>
            )}
          </div>

          <div className="flex flex-col gap-y-0.5 text-xs">
            {artist.styles.map((style) => (
              <span
                key={style}
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
                className="text-xs text-muted-foreground hover:text-foreground transition-colors cursor-pointer italic rounded"
              >
                {style}
              </span>
            ))}
          </div>

          <div className="flex flex-col gap-2 min-w-0">
            <div className="flex gap-1.5 overflow-x-auto overflow-y-hidden pb-1 -mx-4 px-4 md:mx-0 md:px-0 md:overflow-visible">
              {thumbsToShow.map((src, i) => (
                <div
                  key={i}
                  className="w-[108px] h-[144px] md:w-[120px] md:h-[162px] bg-muted overflow-hidden shrink-0"
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
