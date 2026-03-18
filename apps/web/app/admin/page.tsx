import { redirect } from "next/navigation";
import { getArtist, getCompactArtists } from "@/lib/data";
import { createClient } from "@/lib/supabase/server";
import { AdminPageClient } from "@/components/AdminPageClient";

const ADMIN_EMAIL = "m.milnikov@gmail.com";

export const revalidate = 0;

export default async function AdminPage() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user || user.email !== ADMIN_EMAIL) {
    redirect("/profile");
  }

  const artists = getCompactArtists();

  const verifiedArtistIds = artists
    .filter((a) => a.verified === "artist")
    .map((a) => a.id);

  const tattoos = verifiedArtistIds.flatMap((id) => {
    const full = getArtist(id);
    if (!full) return [];
    let sourceDomain: string | null = null;
    try {
      if (full.links?.source) {
        sourceDomain = new URL(full.links.source).hostname.replace(/^www\./, "");
      }
    } catch {
      sourceDomain = null;
    }
    return full.tattoos.map((t) => ({
      artistId: full.id,
      artistName: full.name,
      imageId: t.image_id,
      imageThumb: t.image_thumb,
      imageFull: t.image_full,
      country: full.location.country,
      city: full.location.city,
      styles: full.styles,
      sourceDomain: sourceDomain ?? "unknown",
      instagramEnriched: Boolean((full as unknown as { instagram_enriched?: unknown }).instagram_enriched),
    }));
  });

  return <AdminPageClient artists={artists} tattoos={tattoos} />;
}

