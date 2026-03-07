import type { Metadata } from "next";
import { Inter, Spectral } from "next/font/google";
import "./globals.css";
import { SiteHeader } from "@/components/site-header";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });
const spectral = Spectral({
  subsets: ["latin"],
  weight: ["400"],
  style: ["italic"],
  variable: "--font-spectral-italic",
  display: "block", // wait for font before showing logo text (no fallback flash)
});

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
      <body className={`${inter.variable} ${spectral.variable} ${inter.className} min-h-screen bg-background text-foreground antialiased`}>
        <SiteHeader />
        {children}
      </body>
    </html>
  );
}
