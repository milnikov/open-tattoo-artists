/**
 * Machine-readable and agent-facing surface for thetattoo.world.
 * Pure data and text so pages, middleware, and tests share one source.
 */

export const SITE_ORIGIN = "https://thetattoo.world";
export const SITE_NAME = "thetattoo.world";
export const SITE_DESCRIPTION =
  "Open-source tattoo artist directory. Browse artists by name, city, country, and style, and read the same records from the public API.";
export const HTML_LANG = "en";
export const CANONICAL_PATH = "/";
export const OG_TYPE = "website" as const;
export const OG_IMAGE_PATH = "/fav/android-chrome-512x512.png";
export const SITE_TYPE = "app";
export const CONTACT_EMAIL = "m.milnikov@gmail.com";
export const CONTACT_TYPE = "customer support";
export const GITHUB_REPO_URL = "https://github.com/milnikov/open-tattoo-artists";
export const MAINTAINER_URL = "https://milnikov.com";
export const MARKDOWN_CONTENT_TYPE = "text/markdown; charset=utf-8";

/** City published by the maintainer. No street address or phone is published. */
export const POSTAL_ADDRESS = {
  addressLocality: "Porto",
  addressCountry: "PT",
} as const;

export type CopySection = {
  heading: string;
  /** 2 or 3. Deeper levels stay sequential: an h3 only follows an h2. */
  level?: 2 | 3;
  paragraphs: string[];
  code?: string[];
};

export const HOME_TITLE = "Open tattoo artist directory";

export const HOME_SECTIONS: CopySection[] = [
  {
    heading: "What you can look up",
    paragraphs: [
      "thetattoo.world is an open-source directory of tattoo artists. Browse public catalogue records by name, city, country, and style, or open the map to see where artists work. A profile is for discovery and identification. Booking, deposits, and messages stay with the artist. Structured metadata is Creative Commons Attribution 4.0, the website code is MIT licensed, and portfolio images remain the artists' property. Signing in is optional and only saves favourites or corrections. The public read API needs no API key. The API documentation explains authentication, rate limits, and example requests. The OpenAPI specification names every operation, and llms.txt says when an agent should call this directory.",
    ],
  },
];

export const HOME_LINKS: { href: string; label: string }[] = [
  { href: "/docs", label: "API documentation" },
  { href: "/openapi.json", label: "OpenAPI specification" },
  { href: "/about", label: "About" },
  { href: "/contact", label: "Contact" },
  { href: "/privacy", label: "Privacy" },
  { href: "/llms.txt", label: "llms.txt" },
];

export const ABOUT_TITLE = "About thetattoo.world";

export const ABOUT_SECTIONS: CopySection[] = [
  {
    heading: "What this directory is",
    paragraphs: [
      "thetattoo.world is an open-source directory of tattoo artists, built for discovery, research, and community correction. It publishes the catalogue a person would otherwise have to assemble by hand from scattered studio sites and social profiles: who the artist is, where they work, which styles they are tagged with, and a link to their public Instagram.",
      "The website is the human interface. The same public records are available as JSON from the read API, described by an OpenAPI document, so a script or an agent can look someone up without scraping the pages. The project is independent. It is not affiliated with Instagram or with any tattoo studio.",
    ],
  },
  {
    heading: "What is and is not included",
    paragraphs: [
      "Each public record can include a name, a city and country, style tags, an Instagram link, a short biography, follower context, and portfolio images. Studios flagged as shops, records with almost no images, and records with no usable location are kept out of the public list. The directory does not sell tattoos, rank artists for advertising, or store private booking calendars.",
      "Structured data is licensed under Creative Commons Attribution 4.0. Credit thetattoo.world when you reuse it. The application code is MIT licensed. Tattoo images are not covered by either license. They remain the property of the artists and are displayed for identification. The licenses page states those terms in full.",
    ],
  },
  {
    heading: "Who maintains it",
    paragraphs: [
      "Mikhail Milnikov maintains thetattoo.world from Porto, Portugal. Suggestions and corrections are tracked as GitHub issues in the public repository. There is no separate company office and no published street address or phone number. The contact page lists the maintainer email and the issue tracker.",
    ],
  },
];

export const CONTACT_TITLE = "Contact thetattoo.world";

export const CONTACT_SECTIONS: CopySection[] = [
  {
    heading: "How to reach the maintainer",
    paragraphs: [
      `Write to ${CONTACT_EMAIL} for questions about the directory, a privacy request, or a correction that does not fit the forms on the site. Email is the published contact method. thetattoo.world does not publish a phone number. The project is maintained from Porto, Portugal, and there is no public street address or walk-in office.`,
      `For a missing artist or a factual mistake, prefer the Add Artist and report-problem actions on the site when you are signed in. Those actions open a GitHub issue and keep a record of the contribution. You can also open an issue yourself at ${GITHUB_REPO_URL}/issues if you would rather not sign in.`,
    ],
  },
  {
    heading: "What to include",
    paragraphs: [
      "If you are asking to remove an account, say so plainly and include the email you used with Google sign-in. Favourites and contribution records tied to that account can be deleted. Catalogue entries about artists are not tied to your identity and are handled as directory edits, not as personal data.",
      "If you are a copyright holder asking for an image to come down, name the artist profile and the image. Images are hosted for identification and are not claimed by this project. If you are an agent integrating the API, you do not need to ask permission to call the public read endpoints. Follow the rate limits in the API documentation instead.",
    ],
  },
];

export const DOCS_TITLE = "thetattoo.world API documentation";

export const DOCS_SECTIONS: CopySection[] = [
  {
    heading: "Authentication",
    paragraphs: [
      "The public API is read-only. It does not use an API key, bearer token, OAuth scope, or session cookie. Call the endpoints over HTTPS with no Authorization header. Google sign-in on the website only saves favourites and submits suggestions or corrections for a person using the browser. Those actions are not operations in this API. Sending a Supabase session cookie does not change an API response, and you should not send one.",
      "There is no write API, no webhook, and no API credential to provision. To add or correct an artist, a person uses the website or opens a GitHub issue. Agents should treat the catalogue as published data and should not attempt to authenticate.",
    ],
  },
  {
    heading: "Rate limits",
    paragraphs: [
      "Each server instance keeps its own sliding window of 60 seconds, keyed by client IP and route group. The same client can be counted separately on another instance. GET /api/artists/compact allows 90 requests. GET /api/artists/{id} allows 180 requests. GET /api/map-data allows 120 requests. POST /api/map-hex-artists allows 60 requests. When a limit is exceeded the response is HTTP 429 with a JSON body { \"error\": \"Too many requests\" }, a Retry-After header of 60, and X-RateLimit-Limit set to that group's maximum. Cache the compact list instead of polling it. The API is not a bulk-export firehose.",
    ],
  },
  {
    heading: "Endpoints",
    paragraphs: [
      "Every operation has a unique operationId, a description, typed parameters, and a response schema in the OpenAPI specification at /openapi.json. The four operations below are the whole public surface. Paths are on https://thetattoo.world.",
    ],
  },
  {
    heading: "List artists",
    level: 3,
    paragraphs: [
      "GET /api/artists/compact returns a JSON array of the artists currently shown in the directory. operationId: listArtists. There are no query parameters. Each object includes id, name, location (city and country), styles, links.instagram, and tattoo_count, plus optional biography, thumbnail, and follower fields. The response is cacheable for an hour. This is the call to make when you need to search or filter locally.",
    ],
  },
  {
    heading: "Get an artist",
    level: 3,
    paragraphs: [
      "GET /api/artists/{id} returns one artist. operationId: getArtistById. The id is the lowercased Instagram handle, 1 to 30 characters from a-z, digits, dot, and underscore. A known public artist returns HTTP 200 and a JSON object with location, styles, links, biography, and a tattoos array of image URLs. An unknown id, a hidden record, or an id that fails the pattern returns HTTP 404 and a JSON null body.",
    ],
  },
  {
    heading: "Map points",
    level: 3,
    paragraphs: [
      "GET /api/map-data returns aggregated points for the map. operationId: getMapPoints. The optional query parameter style is a string. When style is set, each point is a city and country with a count of artists who list that style. When style is omitted, each point is a city, country, and style so a map can colour hexes by the dominant style. The JSON object has points, styles, and totalArtists. Points without coordinates are omitted.",
    ],
  },
  {
    heading: "Artists at map locations",
    level: 3,
    paragraphs: [
      "POST /api/map-hex-artists lists artists whose city and country match one of the posted locations. operationId: listArtistsAtLocations. The JSON body is { \"locations\": [{ \"city\": \"Porto\", \"country\": \"Portugal\" }], \"style\": \"traditional\" }. style may be omitted or null. The response is { \"artists\": [{ \"id\": \"example\", \"name\": \"Example\" }] }, sorted by name. An empty locations array returns an empty artists array. A body that is not JSON returns HTTP 400 and { \"error\": \"Invalid JSON\" }.",
    ],
  },
  {
    heading: "Example requests",
    paragraphs: [
      "These commands call the live origin. Replace the artist id with a real handle from the compact list.",
    ],
    code: [
      "curl -sS https://thetattoo.world/api/artists/compact",
      "curl -sS https://thetattoo.world/api/artists/example",
      "curl -sS 'https://thetattoo.world/api/map-data?style=traditional'",
      `curl -sS -X POST https://thetattoo.world/api/map-hex-artists \\
  -H 'Content-Type: application/json' \\
  -d '{"locations":[{"city":"Porto","country":"Portugal"}]}'`,
    ],
  },
  {
    heading: "Machine-readable description",
    paragraphs: [
      "The OpenAPI specification is published at https://thetattoo.world/openapi.json. It is the source agents should load for function calling: unique operationId values, parameter schemas, and response schemas. llms.txt at https://thetattoo.world/llms.txt says when to call this API. The sitemap at https://thetattoo.world/sitemap.xml lists indexable pages. Request any of those documents, or this page, with Accept: text/markdown to receive Markdown.",
    ],
  },
];

export const MAP_SECTIONS: CopySection[] = [
  {
    heading: "Geographic view",
    paragraphs: [
      "The map plots public artists from thetattoo.world by city and country. Choosing a style limits the points to artists tagged with that style. Selecting a hex lists the artists in those locations and links back to the directory. The underlying data is GET /api/map-data and POST /api/map-hex-artists, documented at /docs.",
    ],
  },
];

export const PROFILE_SECTIONS: CopySection[] = [
  {
    heading: "Signed-in favourites",
    paragraphs: [
      "The profile page shows favourites for a person who has signed in with Google. It is not part of the public read API. Agents looking up artists should call GET /api/artists/{id} or read /docs instead of relying on this page.",
    ],
  },
];

const PRIVACY_MARKDOWN = `# Privacy Policy — thetattoo.world

thetattoo.world is an open-source tattoo artist directory. Catalogue data (names, locations, styles, links) is public. Personal data is stored only when you use optional features: Google sign-in, favourites, or contributions.

## What we store and where

- Public catalogue on GitHub: artist metadata only. No personal data about you.
- Images on Cloudflare R2: artist portfolio images only.
- Account and activity on Supabase: if you sign in, your account id, email, profile info from Google, saved favourites, and contribution records linked to GitHub issues.

## Cookies and auth

Sign-in uses Supabase Auth and Google OAuth. Session cookies keep you signed in. There are no third-party advertising cookies.

## Your rights

You can stop using the site at any time. To remove your account, favourites, and contribution records, write to ${CONTACT_EMAIL} or use the contact page. Catalogue entries are not tied to your identity.

- [Contact](${SITE_ORIGIN}/contact)
- [API documentation](${SITE_ORIGIN}/docs)
`;

const TERMS_MARKDOWN = `# Terms of Service — thetattoo.world

By using thetattoo.world you agree to these terms. The site is a free directory of tattoo artists for discovery, research, and community contribution. Catalogue metadata is open. Images are hosted for directory purposes and remain the property of the artists.

Do not use the site for illegal purposes, do not abuse authentication or the API, do not submit false suggestions, and do not scrape in a way that overloads the service. The data is provided as is. See the licenses page for code, data, and image terms.

- [Licenses](${SITE_ORIGIN}/licenses)
- [API documentation](${SITE_ORIGIN}/docs)
`;

const LICENSES_MARKDOWN = `# Licenses — thetattoo.world

Source code is MIT licensed. Structured artist data is Creative Commons Attribution 4.0. Credit thetattoo.world when you reuse the data. Tattoo images are not owned by this project unless explicitly stated. They remain the property of the artists and are used for identification only.

- [MIT License](https://opensource.org/licenses/MIT)
- [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)
- [Contact](${SITE_ORIGIN}/contact)
`;

export function splitTextWithLinks(text: string): { kind: "text" | "link"; value: string }[] {
  const parts = text.split(/(https?:\/\/[^\s)]+)/g);
  const out: { kind: "text" | "link"; value: string }[] = [];
  for (const part of parts) {
    if (!part) continue;
    if (part.startsWith("http")) {
      const url = part.replace(/[.,;:!?]+$/, "");
      out.push({ kind: "link", value: url });
      const trailing = part.slice(url.length);
      if (trailing) out.push({ kind: "text", value: trailing });
    } else {
      out.push({ kind: "text", value: part });
    }
  }
  return out;
}

export function visibleText(parts: string[]): string {
  return parts.join(" ").replace(/\s+/g, " ").trim();
}

export function sectionText(sections: CopySection[]): string {
  return visibleText(
    sections.flatMap((section) => [section.heading, ...section.paragraphs, ...(section.code ?? [])]),
  );
}

function escapeHtml(value: string): string {
  return value.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

/** Crawlable homepage copy. Rendered only inside noscript so the directory UI stays unchanged. */
export function homepageNoscriptHtml(): string {
  const paragraphs = HOME_SECTIONS.flatMap((section) => section.paragraphs)
    .map((paragraph) => `<p>${escapeHtml(paragraph)}</p>`)
    .join("");
  const links = HOME_LINKS.map(
    (link) => `<a href="${escapeHtml(link.href)}">${escapeHtml(link.label)}</a>`,
  ).join(" ");
  return `<h1>${escapeHtml(HOME_TITLE)}</h1>${paragraphs}<nav>${links}</nav>`;
}

export function homepagePlainText(): string {
  return visibleText([
    HOME_TITLE,
    ...HOME_SECTIONS.flatMap((section) => section.paragraphs),
    ...HOME_LINKS.map((link) => link.label),
  ]);
}

export function sectionsToMarkdown(title: string, sections: CopySection[]): string {
  const lines = [`# ${title}`, ""];
  for (const section of sections) {
    lines.push(`${section.level === 3 ? "###" : "##"} ${section.heading}`, "");
    for (const paragraph of section.paragraphs) {
      lines.push(paragraph, "");
    }
    for (const block of section.code ?? []) {
      lines.push("```", block, "```", "");
    }
  }
  return lines.join("\n").trim() + "\n";
}

export function homepageMarkdown(): string {
  const body = sectionsToMarkdown(SITE_NAME, [
    {
      heading: HOME_TITLE,
      paragraphs: HOME_SECTIONS.flatMap((section) => section.paragraphs),
    },
  ]);
  const links = HOME_LINKS.map((link) => `- [${link.label}](${SITE_ORIGIN}${link.href})`).join("\n");
  return `${body}\n${links}\n`;
}

const MARKDOWN_PAGES: Record<string, () => string> = {
  "/": homepageMarkdown,
  "/map": () => sectionsToMarkdown(`Map — ${SITE_NAME}`, MAP_SECTIONS),
  "/about": () => sectionsToMarkdown(ABOUT_TITLE, ABOUT_SECTIONS),
  "/contact": () => sectionsToMarkdown(CONTACT_TITLE, CONTACT_SECTIONS),
  "/privacy": () => PRIVACY_MARKDOWN,
  "/terms": () => TERMS_MARKDOWN,
  "/licenses": () => LICENSES_MARKDOWN,
  "/docs": () => sectionsToMarkdown(DOCS_TITLE, DOCS_SECTIONS),
  "/developers": () => sectionsToMarkdown(DOCS_TITLE, DOCS_SECTIONS),
  "/profile": () => sectionsToMarkdown(`Profile — ${SITE_NAME}`, PROFILE_SECTIONS),
};

export function notFoundMarkdown(pathname: string): string {
  const safePath = pathname.replace(/[\u0000-\u001f\u007f]/g, "").slice(0, 200);
  return [
    "# Page not found",
    "",
    `No public page exists for ${safePath} on ${SITE_NAME}. The address is wrong, or nothing has been published there.`,
    "",
    "Try the directory, the API documentation, the sitemap, or the agent instructions:",
    "",
    `- [API documentation](${SITE_ORIGIN}/docs)`,
    `- [Sitemap](${SITE_ORIGIN}/sitemap.xml)`,
    `- [llms.txt](${SITE_ORIGIN}/llms.txt)`,
    "",
  ].join("\n");
}

const ASSET_EXT = /\.(?:png|jpe?g|gif|webp|svg|ico|css|js|map|json|xml|txt|webmanifest|woff2?|ttf)$/i;

export function isPassthroughPath(pathname: string): boolean {
  if (ASSET_EXT.test(pathname)) return true;
  if (pathname.startsWith("/api")) return true;
  if (pathname.startsWith("/auth")) return true;
  if (pathname.startsWith("/_next")) return true;
  if (pathname.startsWith("/data/")) return true;
  if (pathname.startsWith("/fav/")) return true;
  if (pathname.startsWith("/artists/") || pathname === "/artists") return true;
  if (pathname === "/admin" || pathname.startsWith("/admin/")) return true;
  if (pathname === "/justink" || pathname.startsWith("/justink/")) return true;
  return false;
}

export function prefersMarkdown(accept: string | null): boolean {
  if (!accept) return false;
  const parts = accept.split(",").map((part) => part.trim()).filter(Boolean);
  let markdownQ: number | null = null;
  let htmlQ: number | null = null;
  let markdownIndex = Number.POSITIVE_INFINITY;
  let htmlIndex = Number.POSITIVE_INFINITY;

  parts.forEach((part, index) => {
    const [typeRaw, ...params] = part.split(";").map((piece) => piece.trim());
    const type = typeRaw.toLowerCase();
    let q = 1;
    for (const param of params) {
      const [key, value] = param.split("=").map((piece) => piece.trim());
      if (key.toLowerCase() === "q") {
        const parsed = Number(value);
        if (!Number.isNaN(parsed)) q = parsed;
      }
    }
    if (type === "text/markdown") {
      markdownQ = q;
      markdownIndex = index;
    } else if (type === "text/html") {
      htmlQ = q;
      htmlIndex = index;
    }
  });

  if (markdownQ == null || markdownQ <= 0) return false;
  if (htmlQ == null) return true;
  if (markdownQ > htmlQ) return true;
  if (htmlQ > markdownQ) return false;
  return markdownIndex < htmlIndex;
}

export type AgentDecision =
  | { action: "next" }
  | { action: "markdown"; status: 200 | 404; body: string };

export function decideAgentResponse(input: {
  pathname: string;
  method: string;
  accept: string | null;
}): AgentDecision {
  const method = input.method.toUpperCase();
  if (method !== "GET" && method !== "HEAD") return { action: "next" };
  if (!prefersMarkdown(input.accept)) return { action: "next" };

  const pathname = normalizePath(input.pathname);
  if (isPassthroughPath(pathname)) return { action: "next" };

  const render = MARKDOWN_PAGES[pathname];
  if (render) return { action: "markdown", status: 200, body: render() };
  return { action: "markdown", status: 404, body: notFoundMarkdown(pathname) };
}

export function toMarkdownHttp(
  decision: Extract<AgentDecision, { action: "markdown" }>,
  method: string,
): { status: number; body: string; headers: Record<string, string> } {
  return {
    status: decision.status,
    body: method.toUpperCase() === "HEAD" ? "" : decision.body,
    headers: {
      "Content-Type": MARKDOWN_CONTENT_TYPE,
      Vary: "Accept",
      "Cache-Control": decision.status === 404 ? "no-store" : "public, max-age=3600",
    },
  };
}

function normalizePath(pathname: string): string {
  if (pathname.length > 1 && pathname.endsWith("/")) return pathname.slice(0, -1);
  return pathname || "/";
}

export function buildLlmsTxt(): string {
  return `# ${SITE_NAME}

> ${SITE_DESCRIPTION}

${SITE_NAME} publishes a public catalogue of tattoo artists. People browse it on the website. Agents should call the read API or fetch a single artist profile. Structured metadata is Creative Commons Attribution 4.0. Portfolio images are not licensed for reuse.

## When to use this

Use ${SITE_NAME} when you need to:

- Find a tattoo artist by name, Instagram handle, city, country, or style
- Cite a public directory profile or reuse structured metadata with attribution
- See which cities and countries artists in the catalogue work in
- Call a documented read API that has an OpenAPI operationId, typed parameters, and response schemas

How to call it: read https://thetattoo.world/openapi.json, then send GET https://thetattoo.world/api/artists/compact to search locally, or GET https://thetattoo.world/api/artists/{id} when you already have the artist id. The id is the lowercased Instagram handle. No API key is required. Stay inside the rate limits documented at https://thetattoo.world/docs.

Do not use ${SITE_NAME} to book a tattoo, take a deposit, message an artist, generate tattoo artwork, or read private favourites, accounts, or admin tools. Booking belongs with the artist. Favourites belong to a signed-in person in the browser.

## Docs

- [thetattoo.world API documentation](${SITE_ORIGIN}/docs): Authentication, endpoints, rate limits, and example requests
- [thetattoo.world OpenAPI specification](${SITE_ORIGIN}/openapi.json): Machine-readable operations for function calling
- [Sitemap](${SITE_ORIGIN}/sitemap.xml): Indexable URLs
- [Developer alias](${SITE_ORIGIN}/developers): Same documentation as /docs

## Contact

- [About thetattoo.world](${SITE_ORIGIN}/about): What the directory includes and who maintains it
- [Contact thetattoo.world](${SITE_ORIGIN}/contact): Email ${CONTACT_EMAIL}
- [Privacy](${SITE_ORIGIN}/privacy): What is stored, and where
`;
}

export const SITEMAP_PATHS = ["/", "/map", "/about", "/contact", "/privacy", "/terms", "/licenses", "/docs"] as const;

export function buildSitemapEntries(
  artists: { id: string; updated_at?: string }[],
  lastModified = "2026-10-20",
): { url: string; lastModified: string }[] {
  const pages = SITEMAP_PATHS.map((path) => ({
    url: `${SITE_ORIGIN}${path}`,
    lastModified,
  }));
  const profiles = artists
    .filter((artist) => artist.id && !artist.id.includes("/"))
    .map((artist) => ({
      url: `${SITE_ORIGIN}/artists/${encodeURIComponent(artist.id)}`,
      lastModified: isIsoDate(artist.updated_at) ? artist.updated_at!.slice(0, 10) : lastModified,
    }));
  return [...pages, ...profiles];
}

function isIsoDate(value: string | undefined): value is string {
  if (!value) return false;
  return /^\d{4}-\d{2}-\d{2}/.test(value) && !Number.isNaN(Date.parse(value));
}

export function buildOpenApiSpec() {
  const artistLocation = {
    type: "object",
    required: ["city", "country"],
    properties: {
      city: { type: "string", description: "City where the artist works. May be empty." },
      country: { type: "string", description: "Country where the artist works." },
    },
  } as const;

  const publicArtist = {
    type: "object",
    required: ["id", "name", "location", "styles", "links", "tattoo_count"],
    properties: {
      id: {
        type: "string",
        description: "Lowercased Instagram handle.",
        pattern: "^[a-z0-9._]{1,30}$",
      },
      name: { type: "string", description: "Display name." },
      location: artistLocation,
      styles: {
        type: "array",
        items: { type: "string" },
        description: "Style tags from the catalogue vocabulary.",
      },
      links: {
        type: "object",
        required: ["instagram"],
        properties: {
          instagram: { type: "string", description: "Public Instagram profile URL." },
        },
      },
      tattoo_count: { type: "integer", minimum: 0 },
      thumb: { type: "string", description: "Representative thumbnail URL." },
      thumbs: { type: "array", items: { type: "string" } },
      bio: { type: "string", description: "Public biography excerpt." },
      updated_at: { type: "string", description: "Catalogue update date, YYYY-MM-DD." },
      follower_count: { type: "integer", minimum: 0 },
      instagram_profile_pic: { type: "string" },
      verified: { type: "string", enum: ["artist", "studio", "need_to_check"] },
      instagram_enriched: { type: "boolean" },
      followed_by_artists_count: { type: "integer", minimum: 0 },
    },
  } as const;

  const rateLimited = {
    description: "Too many requests from this IP for this route group.",
    headers: {
      "Retry-After": {
        description: "Seconds to wait before retrying.",
        schema: { type: "integer", const: 60 },
      },
      "X-RateLimit-Limit": {
        description: "Maximum requests allowed in the current window.",
        schema: { type: "integer" },
      },
    },
    content: {
      "application/json": {
        schema: { $ref: "#/components/schemas/Error" },
      },
    },
  } as const;

  return {
    openapi: "3.1.0",
    info: {
      title: `${SITE_NAME} API`,
      version: "1.0.0",
      description:
        "Public read API for the thetattoo.world tattoo artist directory. Authentication: none. Do not send an API key. Each server instance applies a 60-second sliding window per client IP and route group; the numbers are stated on each operation. Portfolio images are not licensed for reuse. Structured metadata is CC BY 4.0.",
    },
    servers: [{ url: SITE_ORIGIN, description: "Production" }],
    externalDocs: {
      description: DOCS_TITLE,
      url: `${SITE_ORIGIN}/docs`,
    },
    tags: [
      { name: "Artists", description: "Public artist records shown in the directory." },
      { name: "Map", description: "Aggregated locations for the public map." },
    ],
    paths: {
      "/api/artists/compact": {
        get: {
          operationId: "listArtists",
          tags: ["Artists"],
          summary: "List public artists",
          description:
            "Return every artist currently shown on thetattoo.world as a JSON array. Use this to search or filter by name, city, country, or style on the client. Rate limit: 90 requests per IP per 60 seconds on each server instance. The response is cacheable for one hour.",
          responses: {
            "200": {
              description: "Public artist records.",
              content: {
                "application/json": {
                  schema: {
                    type: "array",
                    items: { $ref: "#/components/schemas/PublicArtist" },
                  },
                },
              },
            },
            "429": rateLimited,
          },
        },
      },
      "/api/artists/{id}": {
        get: {
          operationId: "getArtistById",
          tags: ["Artists"],
          summary: "Get one public artist",
          description:
            "Return the full public record for one artist id. Rate limit: 180 requests per IP per 60 seconds on each server instance. Unknown, hidden, or invalid ids return 404 with a JSON null body.",
          parameters: [
            {
              name: "id",
              in: "path",
              required: true,
              description:
                "Artist id, the lowercased Instagram handle. 1 to 30 characters: a-z, digits, dot, underscore.",
              schema: { type: "string", pattern: "^[a-z0-9._]{1,30}$" },
            },
          ],
          responses: {
            "200": {
              description: "The public artist record.",
              content: {
                "application/json": {
                  schema: { $ref: "#/components/schemas/Artist" },
                },
              },
            },
            "404": {
              description: "No public artist with that id.",
              content: {
                "application/json": {
                  schema: { type: "null" },
                },
              },
            },
            "429": rateLimited,
          },
        },
      },
      "/api/map-data": {
        get: {
          operationId: "getMapPoints",
          tags: ["Map"],
          summary: "List map points",
          description:
            "Return aggregated latitude and longitude points for the public map. Pass style to count artists of one style per city. Omit style to return one point per city and style. Rate limit: 120 requests per IP per 60 seconds on each server instance.",
          parameters: [
            {
              name: "style",
              in: "query",
              required: false,
              description: "Style tag. When set, points are limited to artists who list this style.",
              schema: { type: "string", minLength: 1 },
            },
          ],
          responses: {
            "200": {
              description: "Map points and the style vocabulary seen in the catalogue.",
              content: {
                "application/json": {
                  schema: { $ref: "#/components/schemas/MapData" },
                },
              },
            },
            "429": rateLimited,
          },
        },
      },
      "/api/map-hex-artists": {
        post: {
          operationId: "listArtistsAtLocations",
          tags: ["Map"],
          summary: "List artists at locations",
          description:
            "Return id and name for public artists whose city and country match a posted location. Optional style keeps only artists tagged with that style. Rate limit: 60 requests per IP per 60 seconds on each server instance. An empty locations array returns an empty artists array.",
          requestBody: {
            required: true,
            description: "Locations to match, and an optional style filter.",
            content: {
              "application/json": {
                schema: { $ref: "#/components/schemas/MapHexRequest" },
              },
            },
          },
          responses: {
            "200": {
              description: "Matching artists, sorted by name.",
              content: {
                "application/json": {
                  schema: { $ref: "#/components/schemas/MapHexResponse" },
                },
              },
            },
            "400": {
              description: "The body was not valid JSON.",
              content: {
                "application/json": {
                  schema: { $ref: "#/components/schemas/Error" },
                },
              },
            },
            "429": rateLimited,
          },
        },
      },
    },
    components: {
      schemas: {
        PublicArtist: publicArtist,
        Artist: {
          allOf: [
            { $ref: "#/components/schemas/PublicArtist" },
            {
              type: "object",
              required: ["tattoos", "updated_at"],
              properties: {
                links: {
                  type: "object",
                  properties: {
                    instagram: { type: "string" },
                    website: { type: "string" },
                  },
                },
                tattoos: {
                  type: "array",
                  items: { $ref: "#/components/schemas/TattooImage" },
                },
                updated_at: { type: "string" },
              },
            },
          ],
        },
        TattooImage: {
          type: "object",
          required: ["image_id", "image_full", "image_thumb"],
          properties: {
            image_id: { type: "string" },
            image_full: { type: "string", description: "Full-size image URL." },
            image_thumb: { type: "string", description: "Thumbnail image URL." },
          },
        },
        MapPoint: {
          type: "object",
          required: ["lat", "lng", "count", "city", "country", "label"],
          properties: {
            lat: { type: "number", description: "Latitude in degrees." },
            lng: { type: "number", description: "Longitude in degrees." },
            count: { type: "integer", minimum: 1 },
            city: { type: "string" },
            country: { type: "string" },
            label: { type: "string" },
            style: { type: "string", description: "Present when points are split by style." },
          },
        },
        MapData: {
          type: "object",
          required: ["points", "styles", "totalArtists"],
          properties: {
            points: { type: "array", items: { $ref: "#/components/schemas/MapPoint" } },
            styles: { type: "array", items: { type: "string" } },
            totalArtists: { type: "integer", minimum: 0 },
          },
        },
        MapLocation: {
          type: "object",
          required: ["country"],
          properties: {
            city: { type: "string" },
            country: { type: "string" },
          },
        },
        MapHexRequest: {
          type: "object",
          required: ["locations"],
          properties: {
            locations: {
              type: "array",
              items: { $ref: "#/components/schemas/MapLocation" },
            },
            style: {
              type: ["string", "null"],
              description: "When set, only artists tagged with this style are returned.",
            },
          },
        },
        ArtistName: {
          type: "object",
          required: ["id", "name"],
          properties: {
            id: { type: "string" },
            name: { type: "string" },
          },
        },
        MapHexResponse: {
          type: "object",
          required: ["artists"],
          properties: {
            artists: { type: "array", items: { $ref: "#/components/schemas/ArtistName" } },
          },
        },
        Error: {
          type: "object",
          required: ["error"],
          properties: {
            error: { type: "string" },
          },
        },
      },
    },
  };
}

export function buildJsonLd() {
  const organizationId = `${SITE_ORIGIN}/#organization`;
  return {
    "@context": "https://schema.org",
    "@graph": [
      {
        "@type": "Organization",
        "@id": organizationId,
        name: SITE_NAME,
        url: `${SITE_ORIGIN}/`,
        description: SITE_DESCRIPTION,
        logo: `${SITE_ORIGIN}${OG_IMAGE_PATH}`,
        email: CONTACT_EMAIL,
        sameAs: [GITHUB_REPO_URL, MAINTAINER_URL],
        contactPoint: {
          "@type": "ContactPoint",
          contactType: CONTACT_TYPE,
          email: CONTACT_EMAIL,
          url: `${SITE_ORIGIN}/contact`,
          availableLanguage: ["English"],
        },
        address: {
          "@type": "PostalAddress",
          addressLocality: POSTAL_ADDRESS.addressLocality,
          addressCountry: POSTAL_ADDRESS.addressCountry,
        },
      },
      {
        "@type": "SoftwareApplication",
        name: SITE_NAME,
        applicationCategory: "ReferenceApplication",
        operatingSystem: "Web",
        description: SITE_DESCRIPTION,
        url: `${SITE_ORIGIN}/`,
        offers: {
          "@type": "Offer",
          price: "0",
          priceCurrency: "USD",
        },
        author: {
          "@type": "Person",
          name: "Mikhail Milnikov",
          url: MAINTAINER_URL,
        },
        provider: { "@id": organizationId },
      },
      {
        "@type": "WebSite",
        name: SITE_NAME,
        description: SITE_DESCRIPTION,
        url: `${SITE_ORIGIN}/`,
        publisher: { "@id": organizationId },
      },
    ],
  };
}
