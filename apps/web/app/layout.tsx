import type { Metadata } from "next";
import "./globals.css";

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
      <body className="min-h-screen bg-gray-50 text-gray-900 antialiased">
        <nav className="border-b bg-white">
          <div className="mx-auto max-w-6xl px-4 py-3 flex items-center justify-between">
            <a href="/" className="text-xl font-bold">
              Open Tattoo Artists
            </a>
            <div className="flex gap-4">
              <a href="/" className="hover:underline">Directory</a>
              <a href="/profile" className="hover:underline">Profile</a>
            </div>
          </div>
        </nav>
        <main className="mx-auto max-w-6xl px-4 py-8">{children}</main>
      </body>
    </html>
  );
}
