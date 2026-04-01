import Link from "next/link";
import { ArrowUpRight } from "lucide-react";

export function SiteFooter() {
  return (
    <footer className="border-t border-border px-4 py-8 md:px-8 md:py-10">
      <div className="flex flex-col gap-2 text-xs text-black w-full max-w-md md:max-w-none">
        <div className="max-w-[400px]">
          <p>
            thetattoo.world is an open database of tattoo artists{"\u00A0"}—
            built for discovery, research, and community contribution.
          </p>
        </div>
        <div className="flex flex-row flex-wrap justify-between items-baseline gap-x-4 gap-y-2">
          <p>
            by{" "}
            <a
              href="https://milnikov.com"
              target="_blank"
              rel="noopener noreferrer"
              className="text-black hover:underline inline-flex items-center gap-0.5"
            >
              @milnikov
              <ArrowUpRight className="h-3 w-3 inline" />
            </a>
          </p>
          <nav className="flex flex-wrap gap-x-4 gap-y-1" aria-label="Legal">
            <Link
              href="/privacy"
              className="text-black hover:underline"
            >
              Privacy
            </Link>
            <Link
              href="/terms"
              className="text-black hover:underline"
            >
              Terms
            </Link>
            <Link
              href="/licenses"
              className="text-black hover:underline"
            >
              Licenses
            </Link>
          </nav>
        </div>
      </div>
    </footer>
  );
}
