import type { Metadata } from "next";
import { DocumentPage } from "@/components/document-page";
import { ABOUT_SECTIONS, ABOUT_TITLE, SITE_DESCRIPTION } from "@/lib/agent-surface";

export const metadata: Metadata = {
  title: ABOUT_TITLE,
  description: SITE_DESCRIPTION,
  alternates: { canonical: "/about" },
};

export default function AboutPage() {
  return <DocumentPage title={ABOUT_TITLE} sections={ABOUT_SECTIONS} />;
}
