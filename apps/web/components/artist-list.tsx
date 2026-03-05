"use client";

import type { CompactArtist } from "@/lib/data";
import { ArtistRow } from "./artist-row";

interface ArtistListProps {
  artists: CompactArtist[];
  globalOffset: number;
  onTagClick?: (style: string) => void;
  onCountryClick?: (country: string) => void;
  onCityClick?: (city: string, country: string) => void;
}

export function ArtistList({
  artists,
  globalOffset,
  onTagClick,
  onCountryClick,
  onCityClick,
}: ArtistListProps) {
  if (artists.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-32 px-4">
        <p className="text-sm text-muted-foreground">No artists found.</p>
        <p className="text-xs text-muted-foreground mt-2">
          Try adjusting your filters or search query.
        </p>
      </div>
    );
  }

  return (
    <div>
      {artists.map((artist, i) => (
        <ArtistRow
          key={artist.id}
          artist={artist}
          index={globalOffset + i}
          onTagClick={onTagClick}
          onCountryClick={onCountryClick}
          onCityClick={onCityClick}
          isFirst={i === 0}
        />
      ))}
    </div>
  );
}
