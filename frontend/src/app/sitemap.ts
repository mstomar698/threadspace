import type { MetadataRoute } from "next";

const BASE = "https://threadspace.duckdns.org";

export default function sitemap(): MetadataRoute.Sitemap {
  const now = new Date();
  const routes: Array<{ path: string; priority: number }> = [
    { path: "", priority: 1 },
    { path: "/projects", priority: 0.7 },
    { path: "/search", priority: 0.6 },
    { path: "/login", priority: 0.4 },
    { path: "/register", priority: 0.4 },
  ];
  return routes.map(({ path, priority }) => ({
    url: `${BASE}${path}`,
    lastModified: now,
    changeFrequency: "daily",
    priority,
  }));
}
