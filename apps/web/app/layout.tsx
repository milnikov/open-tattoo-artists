import type { Metadata } from "next";
import "./globals.css";
import { SiteHeader } from "@/components/site-header";

export const metadata: Metadata = {
  title: "Open Tattoo Artists",
  description: "Open-source tattoo artist directory",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-background text-foreground antialiased overflow-x-hidden">
        <SiteHeader />
        {children}
      </body>
    </html>
  );
}
