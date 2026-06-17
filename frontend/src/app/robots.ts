import type { MetadataRoute } from "next";

const BASE = "https://threadspace.duckdns.org";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: {
      userAgent: "*",
      allow: "/",
      // Private / non-content routes that shouldn't be indexed.
      disallow: ["/settings", "/github/"],
    },
    sitemap: `${BASE}/sitemap.xml`,
    host: BASE,
  };
}
