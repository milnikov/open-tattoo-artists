import { getCompactArtists } from "@/lib/data";
import { NextResponse } from "next/server";

export async function GET() {
  const artists = getCompactArtists();
  return NextResponse.json(artists);
}
