"use server";

import { createClient } from "@/lib/supabase/server";
import { revalidatePath } from "next/cache";

const GITHUB_REPO = process.env.GITHUB_REPO || "milnikov/open-tattoo-artists";
const GITHUB_TOKEN = process.env.GITHUB_TOKEN;

export type SuggestArtistResult =
  | { ok: true; issueUrl: string }
  | { ok: false; error: string };

export async function suggestArtist(
  artistName: string,
  profileUrl: string,
  notes: string
): Promise<SuggestArtistResult> {
  const supabase = await createClient();
  const {
    data: { user },
    error: authError,
  } = await supabase.auth.getUser();

  if (authError || !user) {
    return { ok: false, error: "You must be signed in to suggest an artist." };
  }

  const name = artistName.trim();
  const url = profileUrl.trim();
  if (!name || !url) {
    return { ok: false, error: "Artist name and profile URL are required." };
  }

  if (!GITHUB_TOKEN) {
    return {
      ok: false,
      error: "GitHub integration is not configured. Please contact the site owner.",
    };
  }

  const title = `Add artist: ${name}`;
  const body = [
    "## Suggested artist",
    "",
    `- **Name:** ${name}`,
    `- **Profile URL:** ${url}`,
    "",
    "### Notes",
    notes.trim() || "_None_",
    "",
    "---",
    `_Submitted by ${user.email}_`,
  ].join("\n");

  const [owner, repo] = GITHUB_REPO.split("/");
  if (!owner || !repo) {
    return { ok: false, error: "Invalid GITHUB_REPO configuration." };
  }

  const res = await fetch(
    `https://api.github.com/repos/${owner}/${repo}/issues`,
    {
      method: "POST",
      headers: {
        Accept: "application/vnd.github+json",
        Authorization: `Bearer ${GITHUB_TOKEN}`,
        "X-GitHub-Api-Version": "2022-11-28",
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ title, body }),
    }
  );

  if (!res.ok) {
    const err = await res.text();
    console.error("GitHub API error:", res.status, err);
    return {
      ok: false,
      error: "Failed to create GitHub issue. Please try again later.",
    };
  }

  const issue = (await res.json()) as { html_url: string };
  const issueUrl = issue.html_url;

  const { error: insertError } = await supabase.from("contributions").insert({
    user_id: user.id,
    type: "add",
    artist_id: null,
    github_issue_url: issueUrl,
    status: "open",
    contributor_email: user.email ?? undefined,
  });

  if (insertError) {
    console.error("Supabase insert error:", insertError);
    return {
      ok: false,
      error: "Issue was created but we could not save your contribution. Please contact support.",
    };
  }

  revalidatePath("/profile");
  return { ok: true, issueUrl };
}
