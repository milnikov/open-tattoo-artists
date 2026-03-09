import type { Metadata, Viewport } from "next";
import { Inter, Spectral } from "next/font/google";
import { Analytics } from "@vercel/analytics/next";
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
  metadataBase: new URL("https://thetattoo.world"),
  title: "thetattoo.world",
  description: "Open-source tattoo artist directory",
  manifest: "/manifest.webmanifest",
  icons: {
    icon: [
      { url: "/fav/favicon-16x16.png", sizes: "16x16", type: "image/png" },
      { url: "/fav/favicon-32x32.png", sizes: "32x32", type: "image/png" },
      { url: "/fav/favicon-96x96.png", sizes: "96x96", type: "image/png" },
      { url: "/fav/favicon-128x128.png", sizes: "128x128", type: "image/png" },
      { url: "/fav/favicon-196x196.png", sizes: "196x196", type: "image/png" },
    ],
    apple: [
      { url: "/fav/apple-touch-icon-57x57.png", sizes: "57x57", type: "image/png" },
      { url: "/fav/apple-touch-icon-60x60.png", sizes: "60x60", type: "image/png" },
      { url: "/fav/apple-touch-icon-72x72.png", sizes: "72x72", type: "image/png" },
      { url: "/fav/apple-touch-icon-76x76.png", sizes: "76x76", type: "image/png" },
      { url: "/fav/apple-touch-icon-114x114.png", sizes: "114x114", type: "image/png" },
      { url: "/fav/apple-touch-icon-120x120.png", sizes: "120x120", type: "image/png" },
      { url: "/fav/apple-touch-icon-144x144.png", sizes: "144x144", type: "image/png" },
      { url: "/fav/apple-touch-icon-152x152.png", sizes: "152x152", type: "image/png" },
      { url: "/fav/apple-touch-icon-167x167.png", sizes: "167x167", type: "image/png" },
      { url: "/fav/apple-touch-icon-180x180.png", sizes: "180x180", type: "image/png" },
    ],
  },
  appleWebApp: {
    capable: true,
    statusBarStyle: "default",
    title: "thetattoo.world",
  },
};

/** Prevents iOS from zooming on input focus; allows small font in form fields. */
export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 1,
  userScalable: false,
  themeColor: "#fafafa",
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
        <Analytics />
      </body>
    </html>
  );
}
