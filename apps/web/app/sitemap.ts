import type { MetadataRoute } from "next";
import { getCompactArtists } from "@/lib/data";
import { buildSitemapEntries } from "@/lib/agent-surface";

export default function sitemap(): MetadataRoute.Sitemap {
  const artists = getCompactArtists().map((artist) => ({
    id: artist.id,
    updated_at: artist.updated_at,
  }));
  return buildSitemapEntries(artists);
}
