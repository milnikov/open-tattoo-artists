"use server";

import { createClient } from "@/lib/supabase/server";
import { REPORT_PROBLEM_OPTIONS } from "@/lib/report-problem-options";

const GITHUB_REPO = process.env.GITHUB_REPO || "milnikov/open-tattoo-artists";
const GITHUB_TOKEN = process.env.GITHUB_TOKEN;

export type ReportProblemResult =
  | { ok: true; issueUrl: string }
  | { ok: false; error: string };

export async function reportProblem(
  artistId: string,
  artistName: string,
  artistPageUrl: string,
  instagramHandle: string,
  whatWrong: string[],
  description: string,
  suggestedFix?: string
): Promise<ReportProblemResult> {
  const supabase = await createClient();
  const {
    data: { user },
    error: authError,
  } = await supabase.auth.getUser();

  if (authError || !user) {
    return { ok: false, error: "You must be signed in to request an update." };
  }

  if (!artistId.trim() || !artistName.trim()) {
    return { ok: false, error: "Artist is required." };
  }

  if (whatWrong.length === 0) {
    return { ok: false, error: "Please select at least one option for what's wrong." };
  }

  if (!GITHUB_TOKEN) {
    console.error(
      "Report problem: set GITHUB_TOKEN (and optionally GITHUB_REPO) in .env.local. See apps/web/GITHUB_SETUP.md"
    );
    return {
      ok: false,
      error: "GitHub integration is not configured. Please contact the site owner.",
    };
  }

  const optionsLabels = REPORT_PROBLEM_OPTIONS.map((o) => o.label);
  const whatWrongLabels = whatWrong
    .map((v) => optionsLabels[REPORT_PROBLEM_OPTIONS.findIndex((o) => o.value === v)] ?? v)
    .filter(Boolean);

  const title = `Report problem: ${artistName}`;
  const body = [
    "## Artist",
    "",
    `**Instagram handle (required):** ${instagramHandle || "_Not provided_"}`,
    `**Artist page URL (if available):** ${artistPageUrl || "_Not provided_"}`,
    "",
    "## What's wrong?",
    "",
    ...whatWrongLabels.map((l) => `- [x] ${l}`),
    "",
    "## Describe the issue",
    "",
    description.trim() || "_No description_",
    "",
    "## Suggested fix (optional)",
    "",
    suggestedFix?.trim() || "_None_",
    "",
    "---",
    `_Submitted by ${user.email}_`,
    `_artist_id: ${artistId}_`,
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
      body: JSON.stringify({
        title,
        body,
        labels: ["report:problem"],
      }),
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

  const row = {
    user_id: user.id,
    type: "report" as const,
    artist_id: artistId,
    github_issue_url: issueUrl,
    status: "open" as const,
  };
  let { error: insertError } = await supabase.from("contributions").insert({
    ...row,
    contributor_email: user.email ?? undefined,
  });
  if (insertError?.message?.includes("contributor_email")) {
    insertError = (await supabase.from("contributions").insert(row)).error;
  }

  if (insertError) {
    console.error("Supabase insert error:", insertError);
    return {
      ok: false,
      error: "Issue was created but we could not save your contribution. Please contact support.",
    };
  }

  return { ok: true, issueUrl };
}
