import type { Metadata } from "next";
import { DocumentPage } from "@/components/document-page";
import { DOCS_SECTIONS, DOCS_TITLE } from "@/lib/agent-surface";

export const metadata: Metadata = {
  title: DOCS_TITLE,
  description:
    "Authentication, endpoints, rate limits, and example requests for the thetattoo.world public API.",
  alternates: { canonical: "/docs" },
};

export default function DocsPage() {
  return (
    <DocumentPage
      title={DOCS_TITLE}
      description="Public read API for the tattoo artist directory. No API key."
      sections={DOCS_SECTIONS}
    />
  );
}
