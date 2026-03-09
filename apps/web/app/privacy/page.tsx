import Link from "next/link";
import { SiteFooter } from "@/components/site-footer";

export const metadata = {
  title: "Privacy Policy — thetattoo.world",
  description: "What data we collect and where it is stored.",
};

export default function PrivacyPage() {
  return (
    <div className="min-h-screen flex flex-col bg-background text-foreground">
      <div className="h-8 md:h-16" />
      <main className="flex-1 px-4 md:px-8 pb-8 max-w-prose mx-auto w-full">
        <Link
          href="/"
          className="text-xs text-muted-foreground hover:text-foreground transition-colors mb-6 inline-block"
        >
          ← Back to directory
        </Link>
        <h1 className="text-lg font-bold text-foreground mb-4">Privacy Policy</h1>
        <p className="text-xs text-muted-foreground mb-6">
          Last updated: March 2026
        </p>

        <div className="prose prose-sm max-w-none text-foreground space-y-6 text-xs text-muted-foreground">
          <section>
            <h2 className="text-sm font-semibold text-foreground mb-2">
              Overview
            </h2>
            <p>
              thetattoo.world is an open-source tattoo artist directory. We
              minimise the data we collect and keep catalogue data (artist
              names, locations, styles, links) open and public. Your personal
              data is stored only when you use optional features (sign-in,
              favourites, contributions).
            </p>
          </section>

          <section>
            <h2 className="text-sm font-semibold text-foreground mb-2">
              What we store and where
            </h2>
            <ul className="list-disc pl-5 space-y-1">
              <li>
                <strong className="text-foreground">Public catalogue (GitHub):</strong>{" "}
                Artist metadata only — names, locations, styles, links. No
                personal data about you.
              </li>
              <li>
                <strong className="text-foreground">Images (Cloudflare R2):</strong>{" "}
                Artist portfolio images only. No user content.
              </li>
              <li>
                <strong className="text-foreground">Your account and activity (Supabase):</strong>{" "}
                If you sign in with Google, we store your account identifier,
                email, and profile info (as provided by Google). We also store
                your saved favourite artists and a record of contributions (e.g.
                “Suggest artist” or “Report problem”) linked to GitHub Issues.
              </li>
            </ul>
          </section>

          <section>
            <h2 className="text-sm font-semibold text-foreground mb-2">
              Cookies and auth
            </h2>
            <p>
              Sign-in uses Supabase Auth (and Google OAuth). Session and
              authentication cookies are used to keep you signed in and to
              associate favourites and contributions with your account. We do
              not use third-party advertising or tracking cookies.
            </p>
          </section>

          <section>
            <h2 className="text-sm font-semibold text-foreground mb-2">
              Your rights
            </h2>
            <p>
              You can stop using the site at any time. To remove your account
              and associated data (favourites, contribution records), contact us
              (e.g. via the link in the footer or a GitHub Issue). Data in the
              public catalogue (artist metadata) is not tied to your identity.
            </p>
          </section>

          <section>
            <h2 className="text-sm font-semibold text-foreground mb-2">
              Changes
            </h2>
            <p>
              We may update this policy occasionally. The “Last updated” date
              at the top will be revised. Continued use of the site after
              changes means you accept the updated policy.
            </p>
          </section>

          <p className="pt-4">
            <Link href="/" className="text-foreground underline underline-offset-2 hover:text-muted-foreground">
              Back to directory
            </Link>
          </p>
        </div>
      </main>
      <SiteFooter />
    </div>
  );
}
