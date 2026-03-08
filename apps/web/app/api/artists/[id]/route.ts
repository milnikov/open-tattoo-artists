import { getArtist } from "@/lib/data";
import { NextResponse } from "next/server";

export async function GET(
  _request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const artist = getArtist(id);
  if (!artist) return NextResponse.json(null, { status: 404 });
  return NextResponse.json(artist);
}
