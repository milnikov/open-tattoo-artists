import { Suspense } from "react";
import type { Metadata } from "next";
import { getAllowedCountryNames } from "@/lib/data";
import { ArtistListPage } from "@/components/artist-list-page";
import { HomeIntro } from "@/components/home-intro";
import {
  CANONICAL_PATH,
  OG_IMAGE_PATH,
  OG_TYPE,
  SITE_DESCRIPTION,
  SITE_NAME,
} from "@/lib/agent-surface";

export const metadata: Metadata = {
  alternates: { canonical: CANONICAL_PATH },
  openGraph: {
    type: OG_TYPE,
    url: CANONICAL_PATH,
    siteName: SITE_NAME,
    title: SITE_NAME,
    description: SITE_DESCRIPTION,
    images: [{ url: OG_IMAGE_PATH, width: 512, height: 512, alt: SITE_NAME }],
  },
};

/**
 * Cache the small server shell (country allowlist only). Artist rows load via
 * /api/artists/compact on the client so the ISR payload stays under Vercel’s limit
 * (full compact JSON serialized into RSC was ~19MB).
 */
export const revalidate = 3600;

function ArtistListPageFallback() {
  return (
    <div className="flex flex-col items-center justify-center py-32 px-4">
      <p className="text-muted-foreground">Loading…</p>
    </div>
  );
}

export default function HomePage() {
  const allowedCountryNames = getAllowedCountryNames();
  return (
    <>
      <HomeIntro />
      <Suspense fallback={<ArtistListPageFallback />}>
        <ArtistListPage allowedCountryNames={allowedCountryNames} />
      </Suspense>
    </>
  );
}
