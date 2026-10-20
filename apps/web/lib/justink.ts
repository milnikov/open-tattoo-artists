export const JUSTINK_STATUSES = [
  { value: "", label: "Empty" },
  { value: "reached", label: "Reached" },
  { value: "no_reply", label: "No reply" },
  { value: "interested", label: "Interested" },
  { value: "not_interested", label: "Not interested" },
  { value: "scheduled", label: "Scheduled" },
  { value: "got_feedback", label: "Got feedback" },
  { value: "became_a_user", label: "Became a user" },
] as const;

export type JustinkStatus = (typeof JUSTINK_STATUSES)[number]["value"];

export type JustinkOutreachRow = {
  artist_id: string;
  status: JustinkStatus | null;
  comment: string;
};

export type JustinkArtist = {
  id: string;
  name: string;
  location: { city: string; country: string };
  styles: string[];
  instagram: string;
  follower_count: number;
  source_domain?: string;
  instagram_enriched?: boolean;
};

export const JUSTINK_COMMENT_MAX = 4000;

const STATUS_VALUES = new Set<string>(JUSTINK_STATUSES.map((s) => s.value));

export function isJustinkStatus(value: string): value is JustinkStatus {
  return STATUS_VALUES.has(value);
}

export function normalizeOutreachStatus(
  value: string | null | undefined
): JustinkStatus {
  if (!value) return "";
  return isJustinkStatus(value) ? value : "";
}

export function errorMessage(err: unknown, fallback: string): string {
  if (err instanceof Error && err.message) return err.message;
  if (
    typeof err === "object" &&
    err !== null &&
    "message" in err &&
    typeof (err as { message: unknown }).message === "string" &&
    (err as { message: string }).message
  ) {
    return (err as { message: string }).message;
  }
  return fallback;
}
