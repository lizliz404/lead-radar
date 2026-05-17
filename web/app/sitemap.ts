import { MetadataRoute } from "next";
import { reports } from "./examples/reports";

export const dynamic = "force-static";

export default function sitemap(): MetadataRoute.Sitemap {
  const siteUrl = process.env.NEXT_PUBLIC_SITE_URL || "https://lead-radar.lizliz.xyz";
  const now = new Date();

  return [
    {
      url: `${siteUrl}/`,
      lastModified: now,
      changeFrequency: "weekly",
      priority: 1,
    },
    {
      url: `${siteUrl}/examples`,
      lastModified: now,
      changeFrequency: "weekly",
      priority: 0.8,
    },
    {
      url: `${siteUrl}/preview`,
      lastModified: now,
      changeFrequency: "weekly",
      priority: 0.8,
    },
    ...reports.map((report) => ({
      url: `${siteUrl}/examples/${report.slug}`,
      lastModified: now,
      changeFrequency: "monthly" as const,
      priority: 0.7,
    })),
  ];
}
