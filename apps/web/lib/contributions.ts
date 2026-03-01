import { createClient } from "@/lib/supabase/server";

export async function getContributorEmailForArtist(artistId: string): Promise<string | null> {
  try {
    const supabase = await createClient();
    const { data } = await supabase
      .from("contributions")
      .select("contributor_email")
      .eq("artist_id", artistId)
      .eq("status", "merged")
      .limit(1)
      .maybeSingle();
    return data?.contributor_email ?? null;
  } catch {
    return null;
  }
}

/** Map artist_id -> contributor_email for all merged contributions (for directory cards). */
export async function getContributorMap(): Promise<Record<string, string>> {
  try {
    const supabase = await createClient();
    const { data } = await supabase
      .from("contributions")
      .select("artist_id, contributor_email")
      .not("artist_id", "is", null)
      .eq("status", "merged");
    const map: Record<string, string> = {};
    for (const row of data ?? []) {
      if (row.artist_id && row.contributor_email) map[row.artist_id] = row.contributor_email;
    }
    return map;
  } catch {
    return {};
  }
}
