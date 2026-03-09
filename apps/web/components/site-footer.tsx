import Link from "next/link";
import { ArrowUpRight } from "lucide-react";

export function SiteFooter() {
  return (
    <footer className="border-t border-border px-4 py-8 md:px-8 md:py-10">
      <div className="flex flex-col gap-2 text-xs text-muted-foreground w-full max-w-md md:max-w-none">
        <div className="max-w-[400px]">
          <p>
            thetattoo.world is a free, open-source index of tattoo artists —
            built for discovery, research, and community contribution.
          </p>
        </div>
        <div className="flex flex-row flex-wrap justify-between items-baseline gap-x-4 gap-y-2">
          <p>
            by{" "}
            <a
              href="https://t.me/milnikov"
              target="_blank"
              rel="noopener noreferrer"
              className="text-foreground hover:text-muted-foreground transition-colors inline-flex items-center gap-0.5"
            >
              @milnikov
              <ArrowUpRight className="h-3 w-3 inline" />
            </a>
          </p>
          <nav className="flex flex-wrap gap-x-4 gap-y-1" aria-label="Legal">
            <Link
              href="/privacy"
              className="text-foreground hover:text-muted-foreground transition-colors"
            >
              Privacy
            </Link>
            <Link
              href="/terms"
              className="text-foreground hover:text-muted-foreground transition-colors"
            >
              Terms
            </Link>
            <Link
              href="/licenses"
              className="text-foreground hover:text-muted-foreground transition-colors"
            >
              Licenses
            </Link>
          </nav>
        </div>
        <p>{new Date().getFullYear()}</p>
      </div>
    </footer>
  );
}
