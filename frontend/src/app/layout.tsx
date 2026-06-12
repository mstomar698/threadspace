import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { Providers } from "@/providers/providers";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  metadataBase: new URL("https://threadspace.duckdns.org"),
  title: {
    default: "ThreadSpace — build in public for the open-source world",
    template: "%s · ThreadSpace",
  },
  description:
    "ThreadSpace is a build-in-public social network for the open-source world. Share devlogs with real GitHub artifacts — repos, releases, commits, PRs — follow makers and projects, and discover what others are shipping.",
  keywords: [
    "ThreadSpace",
    "build in public",
    "open source",
    "devlog",
    "GitHub",
    "developers",
    "social network",
  ],
  openGraph: {
    type: "website",
    siteName: "ThreadSpace",
    url: "https://threadspace.duckdns.org",
    title: "ThreadSpace — build in public for the open-source world",
    description:
      "Share devlogs with real GitHub artifacts, follow makers and projects, and discover what others are shipping.",
  },
  twitter: {
    card: "summary",
    title: "ThreadSpace — build in public",
    description: "A social network for the open-source world.",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
