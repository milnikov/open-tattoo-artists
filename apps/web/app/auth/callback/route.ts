import { NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";

export async function GET(request: Request) {
  const url = new URL(request.url);
  const { searchParams } = url;
  const code = searchParams.get("code");
  const next = searchParams.get("next") ?? "/profile";
  const origin = url.origin;

  if (!code) {
    return NextResponse.redirect(`${origin}/profile?error=missing_code`);
  }

  const supabase = await createClient();
  const { error } = await supabase.auth.exchangeCodeForSession(code);

  if (error) {
    console.error("Auth callback error:", error.message);
    return NextResponse.redirect(`${origin}/profile?error=auth_failed`);
  }

  const path = next.startsWith("/") ? next : `/${next}`;
  const forwardedHost = request.headers.get("x-forwarded-host");
  const isLocal = process.env.NODE_ENV === "development";
  const redirectUrl = isLocal || !forwardedHost
    ? `${origin}${path}`
    : `https://${forwardedHost}${path}`;

  return NextResponse.redirect(redirectUrl);
}
