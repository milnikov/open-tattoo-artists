import Link from "next/link";
import { SiteFooter } from "@/components/site-footer";

export const metadata = {
  title: "Terms of Service — thetattoo.world",
  description: "Terms of use for thetattoo.world directory.",
};

export default function TermsPage() {
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
        <h1 className="text-lg font-bold text-foreground mb-4">
          Terms of Service
        </h1>
        <p className="text-xs text-muted-foreground mb-6">
          Last updated: March 2026
        </p>

        <div className="prose prose-sm max-w-none text-foreground space-y-6 text-xs text-muted-foreground">
          <section>
            <h2 className="text-sm font-semibold text-foreground mb-2">
              Acceptance
            </h2>
            <p>
              By using thetattoo.world (“the site”), you agree to these
              terms. If you do not agree, please do not use the site.
            </p>
          </section>

          <section>
            <h2 className="text-sm font-semibold text-foreground mb-2">
              What the site is
            </h2>
            <p>
              thetattoo.world is a free, open-source directory of tattoo
              artists and their work. It is built for discovery, research, and
              community contribution. The catalogue data (artist metadata) is
              open and versioned in a public repository; images are hosted for
              directory purposes.
            </p>
          </section>

          <section>
            <h2 className="text-sm font-semibold text-foreground mb-2">
              Acceptable use
            </h2>
            <p>
              You may use the site for personal and non-commercial use in line
              with its purpose. You must not:
            </p>
            <ul className="list-disc pl-5 space-y-1 mt-2">
              <li>Use the site for illegal or harmful purposes</li>
              <li>Attempt to break or abuse authentication, APIs, or infrastructure</li>
              <li>Submit false or misleading “Suggest artist” or “Report problem” requests</li>
              <li>Scrape or automate in a way that overloads the service</li>
            </ul>
          </section>

          <section>
            <h2 className="text-sm font-semibold text-foreground mb-2">
              Disclaimer
            </h2>
            <p>
              The site and its data are provided “as is”. We do not guarantee
              accuracy or completeness of artist information. Tattoo images
              remain the property of the respective artists; we do not claim
              ownership. We are not affiliated with Instagram or other
              third-party platforms. See the{" "}
              <Link href="/licenses" className="text-foreground underline underline-offset-2 hover:text-muted-foreground">
                Licenses
              </Link>{" "}
              page for code, data, and image terms.
            </p>
          </section>

          <section>
            <h2 className="text-sm font-semibold text-foreground mb-2">
              Contributions
            </h2>
            <p>
              When you submit a “Suggest artist” or “Report problem” request, a
              GitHub Issue may be created. By submitting, you agree that
              relevant information can be used to maintain the directory (e.g.
              adding or correcting artist data). Code and data contributions to
              the project are subject to the licenses described on the Licenses
              page.
            </p>
          </section>

          <section>
            <h2 className="text-sm font-semibold text-foreground mb-2">
              Changes
            </h2>
            <p>
              We may update these terms. The “Last updated” date will be
              revised. Continued use of the site after changes means you accept
              the updated terms.
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
