/**
 * Match build_indexes.py: compact rows expose top-level `follower_count` and
 * `instagram_enriched` as a boolean flag. Raw artist JSON may omit top-level
 * follower_count and only set `instagram_enriched.follower_count`.
 */
export function artistFollowerCount(artist: {
  follower_count?: number;
  instagram_enriched?: boolean | { follower_count?: number };
}): number {
  if (
    typeof artist.follower_count === "number" &&
    !Number.isNaN(artist.follower_count)
  ) {
    return artist.follower_count;
  }
  const ie = artist.instagram_enriched;
  if (
    ie &&
    typeof ie === "object" &&
    typeof ie.follower_count === "number" &&
    !Number.isNaN(ie.follower_count)
  ) {
    return ie.follower_count;
  }
  return 0;
}
