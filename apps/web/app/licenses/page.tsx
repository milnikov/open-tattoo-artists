import Link from "next/link";
import { SiteFooter } from "@/components/site-footer";

export const metadata = {
  title: "Licenses — Open Tattoo Artists",
  description: "Code, data, and image licenses for the Open Tattoo Artists directory.",
};

export default function LicensesPage() {
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
        <h1 className="text-lg font-bold text-foreground mb-4">Licenses</h1>
        <p className="text-xs text-muted-foreground mb-6">
          How you may use the code, data, and images in this project.
        </p>

        <div className="prose prose-sm max-w-none text-foreground space-y-8 text-xs text-muted-foreground">
          <section>
            <h2 className="text-sm font-semibold text-foreground mb-2">
              1. Source code — MIT License
            </h2>
            <p className="mb-2">
              The source code of this project is licensed under the MIT License.
            </p>
            <p className="mb-2">You are free to:</p>
            <ul className="list-disc pl-5 space-y-1 mb-2">
              <li>Use, copy, modify, merge, publish, distribute, sublicense, and sell copies of the software</li>
            </ul>
            <p className="mb-2">
              Under the condition that the above copyright notice and this
              permission notice are included in all copies or substantial
              portions of the software. The software is provided “as is”, without
              warranty of any kind.
            </p>
            <p>
              Full text:{" "}
              <a
                href="https://opensource.org/licenses/MIT"
                target="_blank"
                rel="noopener noreferrer"
                className="text-foreground underline underline-offset-2 hover:text-muted-foreground"
              >
                opensource.org/licenses/MIT
              </a>
            </p>
          </section>

          <section>
            <h2 className="text-sm font-semibold text-foreground mb-2">
              2. Structured artist data — CC BY 4.0
            </h2>
            <p className="mb-2">
              All structured artist data (JSON files, metadata, tags, schemas,
              normalized fields) is licensed under Creative Commons Attribution
              4.0 International (CC BY 4.0).
            </p>
            <p className="mb-2">You are free to:</p>
            <ul className="list-disc pl-5 space-y-1 mb-2">
              <li>Share — copy and redistribute the data in any medium or format</li>
              <li>Adapt — remix, transform, and build upon the data</li>
              <li>Use commercially</li>
            </ul>
            <p className="mb-2">
              Under the following term: you must give appropriate credit to
              “Open Tattoo Artists Directory”, provide a link to the project,
              and indicate if changes were made.
            </p>
            <p>
              Full license:{" "}
              <a
                href="https://creativecommons.org/licenses/by/4.0/"
                target="_blank"
                rel="noopener noreferrer"
                className="text-foreground underline underline-offset-2 hover:text-muted-foreground"
              >
                creativecommons.org/licenses/by/4.0
              </a>
            </p>
          </section>

          <section>
            <h2 className="text-sm font-semibold text-foreground mb-2">
              3. Tattoo images
            </h2>
            <p className="mb-2">
              Tattoo images are <strong className="text-foreground">not</strong>{" "}
              owned by this project unless explicitly stated.
            </p>
            <ul className="list-disc pl-5 space-y-1 mb-2">
              <li>They remain the property of their respective tattoo artists</li>
              <li>They are used for identification and directory purposes only</li>
              <li>They are not covered by the MIT License or CC BY 4.0</li>
            </ul>
            <p>
              If you are a copyright owner and want an image removed, please
              open an issue in the project repository.
            </p>
          </section>

          <section>
            <h2 className="text-sm font-semibold text-foreground mb-2">
              4. Contributions
            </h2>
            <p>
              By submitting a Pull Request or Issue, you agree that code
              contributions are licensed under MIT, data contributions under CC
              BY 4.0, and that you have the legal right to submit the content.
            </p>
          </section>

          <section>
            <h2 className="text-sm font-semibold text-foreground mb-2">
              5. No affiliation
            </h2>
            <p>
              This project is independent and not affiliated with Instagram or
              any other third-party platform.
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
