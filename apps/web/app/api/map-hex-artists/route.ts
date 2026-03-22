import { getCompactArtists } from "@/lib/data";
import { NextRequest, NextResponse } from "next/server";

type Location = { city: string; country: string };

function normalize(s: string): string {
  return s.trim();
}

function locationKey(city: string, country: string): string {
  return `${normalize(city)}|${normalize(country)}`;
}

export async function POST(request: NextRequest) {
  let body: { locations?: Location[]; style?: string | null };
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: "Invalid JSON" }, { status: 400 });
  }

  const raw = body.locations;
  if (!Array.isArray(raw) || raw.length === 0) {
    return NextResponse.json({ artists: [] });
  }

  const allowed = new Set<string>();
  for (const loc of raw) {
    if (!loc || typeof loc.country !== "string" || !normalize(loc.country)) continue;
    allowed.add(locationKey(loc.city ?? "", loc.country));
  }
  if (allowed.size === 0) {
    return NextResponse.json({ artists: [] });
  }

  const styleFilter = typeof body.style === "string" && body.style.trim() ? body.style.trim() : null;
  const artists = getCompactArtists();
  const out: { id: string; name: string }[] = [];
  const seen = new Set<string>();

  for (const a of artists) {
    const city = a.location?.city ?? "";
    const country = a.location?.country ?? "";
    if (!allowed.has(locationKey(city, country))) continue;
    if (styleFilter && !a.styles.includes(styleFilter)) continue;
    if (seen.has(a.id)) continue;
    seen.add(a.id);
    out.push({ id: a.id, name: a.name });
  }

  out.sort((x, y) => x.name.localeCompare(y.name, undefined, { sensitivity: "base" }));

  return NextResponse.json({ artists: out });
}
