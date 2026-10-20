import type { Metadata } from "next";
import { DocumentPage } from "@/components/document-page";
import { CONTACT_SECTIONS, CONTACT_TITLE } from "@/lib/agent-surface";

export const metadata: Metadata = {
  title: CONTACT_TITLE,
  description: "Email the maintainer of thetattoo.world, or open a GitHub issue to correct the directory.",
  alternates: { canonical: "/contact" },
};

export default function ContactPage() {
  return <DocumentPage title={CONTACT_TITLE} sections={CONTACT_SECTIONS} />;
}
