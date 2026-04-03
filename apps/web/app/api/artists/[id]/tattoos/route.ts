import { getArtist } from "@/lib/data";
import { NextRequest, NextResponse } from "next/server";

const MAX_LIMIT = 48;

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const offsetParam = request.nextUrl.searchParams.get("offset");
  const limitParam = request.nextUrl.searchParams.get("limit");

  const offset = Math.max(0, Number.parseInt(offsetParam ?? "0", 10) || 0);
  const limitRaw = Number.parseInt(limitParam ?? "12", 10) || 12;
  const limit = Math.min(MAX_LIMIT, Math.max(1, limitRaw));

  const artist = await getArtist(id, { cache: "no-store" });
  if (!artist) {
    return NextResponse.json({ error: "Not found" }, { status: 404 });
  }

  const tattoos = artist.tattoos ?? [];
  const slice = tattoos.slice(offset, offset + limit);

  return NextResponse.json({
    tattoos: slice,
    total: tattoos.length,
    offset,
    limit: slice.length,
    hasMore: offset + slice.length < tattoos.length,
  });
}
