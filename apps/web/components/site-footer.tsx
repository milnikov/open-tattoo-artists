import { ArrowUpRight } from "lucide-react";

export function SiteFooter() {
  return (
    <footer className="border-t border-border px-4 py-8 md:px-8 md:py-10">
      <div className="flex flex-col gap-2 text-xs text-muted-foreground max-w-md">
        <p>
          Open Tattoo Artists is a free, open-source index of tattoo artists —
          built for discovery, research, and community contribution.
        </p>
        <p>
          by{" "}
          <a
            href="https://t.me/milnikov"
            target="_blank"
            rel="noopener noreferrer"
            className="text-foreground hover:text-muted-foreground transition-colors inline-flex items-center gap-0.5 underline underline-offset-2"
          >
            @milnikov
            <ArrowUpRight className="h-3 w-3 inline" />
          </a>
        </p>
        <p>{new Date().getFullYear()}</p>
      </div>
    </footer>
  );
}
