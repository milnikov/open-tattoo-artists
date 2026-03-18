"use server";

import { cookies } from "next/headers";
import { createClient } from "@/lib/supabase/server";

const GITHUB_REPO = process.env.GITHUB_REPO || "milnikov/open-tattoo-artists";
const GITHUB_TOKEN = process.env.GITHUB_TOKEN;

const ADMIN_EMAIL = "m.milnikov@gmail.com";

export type AdminDeleteArtistResult =
  | { ok: true; issueUrl: string }
  | { ok: false; error: string };

type AdminDeleteImageRequest = {
  image_id: string;
  image_full: string;
  image_thumb: string;
};

export async function adminDeleteArtist(
  artistId: string,
  artistName: string,
  instagramUrl: string | null,
  tattoos: AdminDeleteImageRequest[]
): Promise<AdminDeleteArtistResult> {
  const cookieStore = await cookies();
  const supabase = await createClient();
  const {
    data: { user },
    error: authError,
  } = await supabase.auth.getUser();

  if (authError || !user) {
    return { ok: false, error: "You must be signed in as admin." };
  }

  if (user.email !== ADMIN_EMAIL) {
    return { ok: false, error: "Only admin can perform this action." };
  }

  if (!artistId.trim() || !artistName.trim()) {
    return { ok: false, error: "Artist is required." };
  }

  if (!GITHUB_TOKEN) {
    console.error(
      "Admin delete: set GITHUB_TOKEN (and optionally GITHUB_REPO) in .env.local. See apps/web/GITHUB_SETUP.md"
    );
    return {
      ok: false,
      error: "GitHub integration is not configured. Please contact the site owner.",
    };
  }

  const [owner, repo] = GITHUB_REPO.split("/");
  if (!owner || !repo) {
    return { ok: false, error: "Invalid GITHUB_REPO configuration." };
  }

  const title = `Admin delete artist: ${artistName}`;

  const lines: string[] = [];
  lines.push("## Admin delete request");
  lines.push("");
  lines.push(`- **Artist ID:** ${artistId}`);
  lines.push(`- **Artist name:** ${artistName}`);
  lines.push(`- **Instagram URL:** ${instagramUrl || "_Not provided_"}`);
  lines.push("");
  lines.push("### Images to remove from JSON + R2");
  lines.push("");

  if (tattoos.length === 0) {
    lines.push("_No images listed in artist JSON._");
  } else {
    for (const t of tattoos) {
      lines.push(
        `- image_id: ${t.image_id} → full: ${t.image_full}, thumb: ${t.image_thumb}`
      );
    }
  }

  lines.push("");
  lines.push("---");
  lines.push(`_Submitted by admin ${user.email}_`);

  const body = lines.join("\n");

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
      body: JSON.stringify({
        title,
        body,
        labels: ["admin:delete-artist"],
      }),
    }
  );

  if (!res.ok) {
    const err = await res.text();
    console.error("GitHub API error (adminDeleteArtist):", res.status, err);
    return {
      ok: false,
      error: "Failed to create GitHub issue. Please try again later.",
    };
  }

  const issue = (await res.json()) as { html_url: string };
  const issueUrl = issue.html_url;

  try {
    cookieStore.set(`admin_hidden_artist_${artistId}`, "1", {
      path: "/",
      maxAge: 60 * 60 * 24 * 365,
    });
  } catch {
    // ignore cookie errors
  }

  return { ok: true, issueUrl };
}

export type AdminDeleteImagesResult =
  | { ok: true; issueUrl: string }
  | { ok: false; error: string };

export async function adminDeleteImages(
  artistId: string,
  artistName: string,
  instagramUrl: string | null,
  images: AdminDeleteImageRequest[]
): Promise<AdminDeleteImagesResult> {
  const cookieStore = await cookies();
  const supabase = await createClient();
  const {
    data: { user },
    error: authError,
  } = await supabase.auth.getUser();

  if (authError || !user) {
    return { ok: false, error: "You must be signed in as admin." };
  }

  if (user.email !== ADMIN_EMAIL) {
    return { ok: false, error: "Only admin can perform this action." };
  }

  if (!artistId.trim() || !artistName.trim()) {
    return { ok: false, error: "Artist is required." };
  }

  if (images.length === 0) {
    return { ok: false, error: "No images selected for deletion." };
  }

  if (!GITHUB_TOKEN) {
    console.error(
      "Admin delete images: set GITHUB_TOKEN (and optionally GITHUB_REPO) in .env.local. See apps/web/GITHUB_SETUP.md"
    );
    return {
      ok: false,
      error: "GitHub integration is not configured. Please contact the site owner.",
    };
  }

  const [owner, repo] = GITHUB_REPO.split("/");
  if (!owner || !repo) {
    return { ok: false, error: "Invalid GITHUB_REPO configuration." };
  }

  const title = `Admin delete images: ${artistName}`;

  const lines: string[] = [];
  lines.push("## Admin delete images request");
  lines.push("");
  lines.push(`- **Artist ID:** ${artistId}`);
  lines.push(`- **Artist name:** ${artistName}`);
  lines.push(`- **Instagram URL:** ${instagramUrl || "_Not provided_"}`);
  lines.push("");
  lines.push("### Images to remove from JSON + R2");
  lines.push("");

  for (const t of images) {
    lines.push(
      `- image_id: ${t.image_id} → full: ${t.image_full}, thumb: ${t.image_thumb}`
    );
  }

  lines.push("");
  lines.push("---");
  lines.push(`_Submitted by admin ${user.email}_`);

  const body = lines.join("\n");

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
      body: JSON.stringify({
        title,
        body,
        labels: ["admin:delete-images"],
      }),
    }
  );

  if (!res.ok) {
    const err = await res.text();
    console.error("GitHub API error (adminDeleteImages):", res.status, err);
    return {
      ok: false,
      error: "Failed to create GitHub issue. Please try again later.",
    };
  }

  const issue = (await res.json()) as { html_url: string };
  const issueUrl = issue.html_url;

  try {
    const key = `admin_hidden_images_${artistId}`;
    const existing = cookieStore.get(key)?.value;
    const currentIds = new Set<string>();
    if (existing) {
      try {
        const parsed = JSON.parse(existing) as string[];
        for (const id of parsed) currentIds.add(id);
      } catch {
        // ignore parse error
      }
    }
    for (const img of images) {
      currentIds.add(img.image_id);
    }
    cookieStore.set(key, JSON.stringify(Array.from(currentIds)), {
      path: "/",
      maxAge: 60 * 60 * 24 * 365,
    });
  } catch {
    // ignore cookie errors
  }

  return { ok: true, issueUrl };
}

