import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";

import { getClientIp, rateLimitAllow } from "@/lib/rate-limit-ip";

const WINDOW_MS = 60_000;

type Group = "map-data" | "map-hex" | "compact" | "artists";

function getRateGroup(pathname: string, method: string): Group | null {
  if (pathname === "/api/map-data") return "map-data";
  if (pathname === "/api/map-hex-artists") return "map-hex";
  if (pathname === "/api/artists/compact") return "compact";
  if (pathname.startsWith("/api/artists/")) return "artists";
  return null;
}

function limitsForGroup(group: Group, method: string): { windowMs: number; max: number } {
  switch (group) {
    case "map-data":
      return { windowMs: WINDOW_MS, max: 120 };
    case "map-hex":
      return {
        windowMs: WINDOW_MS,
        max: method === "POST" ? 60 : 20,
      };
    case "compact":
      return { windowMs: WINDOW_MS, max: 90 };
    case "artists":
      return { windowMs: WINDOW_MS, max: 180 };
    default:
      return { windowMs: WINDOW_MS, max: 100 };
  }
}

export function middleware(request: NextRequest) {
  const pathname = request.nextUrl.pathname;
  const group = getRateGroup(pathname, request.method);
  if (!group) return NextResponse.next();

  const ip = getClientIp(request);
  const key = `${ip}:${group}`;
  const rule = limitsForGroup(group, request.method);

  if (!rateLimitAllow(key, rule)) {
    return new NextResponse(JSON.stringify({ error: "Too many requests" }), {
      status: 429,
      headers: {
        "Content-Type": "application/json",
        "Retry-After": "60",
        "X-RateLimit-Limit": String(rule.max),
        "X-RateLimit-Window": String(rule.windowMs / 1000),
      },
    });
  }

  const res = NextResponse.next();
  res.headers.set("X-RateLimit-Limit", String(rule.max));
  res.headers.set("X-RateLimit-Window", String(rule.windowMs / 1000));
  return res;
}

export const config = {
  matcher: [
    "/api/map-data",
    "/api/map-hex-artists",
    "/api/artists/compact",
    "/api/artists/:path*",
  ],
};
