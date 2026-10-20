import { NextResponse } from "next/server";
import { isAdminEmail } from "@/lib/admin";
import { artistFollowerCount } from "@/lib/artist-follower-count";
import { getCompactArtists } from "@/lib/data";
import type { JustinkArtist } from "@/lib/justink";
import { createClient } from "@/lib/supabase/server";

export const dynamic = "force-dynamic";

export async function GET() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user || !isAdminEmail(user.email)) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const artists: JustinkArtist[] = getCompactArtists().map((a) => ({
    id: a.id,
    name: a.name,
    location: a.location,
    styles: a.styles,
    instagram: a.links?.instagram ?? "",
    follower_count: artistFollowerCount(a),
    source_domain: a.source_domain,
    instagram_enriched: Boolean(a.instagram_enriched),
  }));

  return NextResponse.json(artists, {
    headers: { "Cache-Control": "private, max-age=60" },
  });
}
