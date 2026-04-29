import type { Metadata } from "next";
import "./globals.css";

const siteUrl = process.env.NEXT_PUBLIC_SITE_URL || "https://lead-radar.vercel.app";

export const metadata: Metadata = {
  metadataBase: new URL(siteUrl),
  title: {
    default: "Lead Radar — Reddit market validation and demand signal scanner",
    template: "%s | Lead Radar",
  },
  description:
    "Turn a plain-language market brief into Reddit demand research, pain-point signals, lead cards, and a downloadable validation report.",
  keywords: [
    "Reddit demand research tool",
    "market validation from Reddit",
    "customer pain point finder",
    "business idea validation tool",
    "SaaS demand signal scanner",
    "commercial insight agent",
    "Reddit lead finder",
  ],
  alternates: { canonical: "/" },
  openGraph: {
    title: "Lead Radar — find market demand signals from Reddit",
    description:
      "A lightweight commercial insight agent for founders, builders, and growth teams validating markets from public community posts.",
    url: siteUrl,
    siteName: "Lead Radar",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "Lead Radar — Reddit market validation tool",
    description: "Input a market idea. Get demand signals, evidence, and a Markdown report.",
  },
  robots: {
    index: true,
    follow: true,
  },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
