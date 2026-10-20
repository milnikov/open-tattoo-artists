import Link from "next/link";
import { SiteFooter } from "@/components/site-footer";
import { CopySections } from "@/components/copy-sections";
import type { CopySection } from "@/lib/agent-surface";

export function DocumentPage({
  title,
  description,
  sections,
}: {
  title: string;
  description?: string;
  sections: CopySection[];
}) {
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
        <h1 className="text-lg font-bold text-foreground mb-4">{title}</h1>
        {description ? <p className="text-xs text-muted-foreground mb-6">{description}</p> : null}
        <div className="max-w-none space-y-6 text-xs text-muted-foreground">
          <CopySections sections={sections} />
        </div>
      </main>
      <SiteFooter />
    </div>
  );
}
