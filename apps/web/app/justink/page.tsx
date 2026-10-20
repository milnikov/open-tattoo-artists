import type { Metadata } from "next";
import { redirect } from "next/navigation";
import { isAdminEmail } from "@/lib/admin";
import { createClient } from "@/lib/supabase/server";
import { JustinkPageClient } from "@/components/JustinkPageClient";

export const revalidate = 0;

export const metadata: Metadata = {
  title: "JustInk outreach",
  robots: { index: false, follow: false },
};

export default async function JustinkPage() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user || !isAdminEmail(user.email)) {
    redirect("/profile");
  }

  return <JustinkPageClient />;
}
