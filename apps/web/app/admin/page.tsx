import { redirect } from "next/navigation";
import { getCompactArtists } from "@/lib/data";
import { createClient } from "@/lib/supabase/server";
import { AdminPageClient } from "@/components/AdminPageClient";

const ADMIN_EMAIL = "m.milnikov@gmail.com";

export const revalidate = 0;

export default async function AdminPage() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user || user.email !== ADMIN_EMAIL) {
    redirect("/profile");
  }

  const artists = getCompactArtists();

  return <AdminPageClient artists={artists} />;
}

