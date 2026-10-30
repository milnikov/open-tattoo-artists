import { Suspense } from "react";
import type { Metadata } from "next";
import { getAllowedCountryNames, getDirectoryPreview } from "@/lib/data";
import {
  ArtistDirectoryFallback,
  ArtistListPage,
} from "@/components/artist-list-page";
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
 * The document includes the directory shell and the first page of names.
 * The full compact catalog stays on /api/artists/compact (too large for the RSC
 * payload) and loads in the background for search, filters, and later pages.
 */
export const revalidate = 3600;

export default function HomePage() {
  const allowedCountryNames = getAllowedCountryNames();
  const preview = getDirectoryPreview();
  return (
    <>
      <HomeIntro />
      <Suspense
        fallback={
          <ArtistDirectoryFallback
            artists={preview.artists}
            totalCount={preview.totalCount}
            styles={preview.styles}
            countries={preview.countries}
          />
        }
      >
        <ArtistListPage
          allowedCountryNames={allowedCountryNames}
          initialArtists={preview.artists}
          initialTotalCount={preview.totalCount}
          facetStyles={preview.styles}
          facetCountries={preview.countries}
        />
      </Suspense>
    </>
  );
}
