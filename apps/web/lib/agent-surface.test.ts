import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

import {
  ABOUT_SECTIONS,
  splitTextWithLinks,
  ABOUT_TITLE,
  CONTACT_SECTIONS,
  CONTACT_TITLE,
  DOCS_SECTIONS,
  DOCS_TITLE,
  HOME_LINKS,
  HOME_TITLE,
  HTML_LANG,
  OG_IMAGE_PATH,
  OG_TYPE,
  SITE_ORIGIN,
  buildJsonLd,
  buildLlmsTxt,
  buildOpenApiSpec,
  buildSitemapEntries,
  decideAgentResponse,
  homepageNoscriptHtml,
  homepagePlainText,
  notFoundMarkdown,
  prefersMarkdown,
  sectionText,
  toMarkdownHttp,
} from "./agent-surface.ts";

test("autolinked URLs do not swallow trailing punctuation", () => {
  const parts = splitTextWithLinks("See https://thetattoo.world/openapi.json. Then stop.");
  assert.deepEqual(
    parts.filter((part) => part.kind === "link").map((part) => part.value),
    ["https://thetattoo.world/openapi.json"],
  );
});

test("markdown negotiation prefers an explicit markdown accept", () => {
  assert.equal(prefersMarkdown("text/markdown"), true);
  assert.equal(prefersMarkdown("text/html"), false);
  assert.equal(prefersMarkdown("text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"), false);
  assert.equal(prefersMarkdown("*/*"), false);
  assert.equal(prefersMarkdown(null), false);
  assert.equal(prefersMarkdown("text/markdown, text/html;q=0.9"), true);
  assert.equal(prefersMarkdown("text/html, text/markdown;q=0.1"), false);
  assert.equal(prefersMarkdown("text/markdown;q=0, text/html"), false);
});

test("homepage markdown is served only when the client asks for it", () => {
  const markdown = decideAgentResponse({
    pathname: "/",
    method: "GET",
    accept: "text/markdown",
  });
  assert.equal(markdown.action, "markdown");
  if (markdown.action !== "markdown") return;
  assert.equal(markdown.status, 200);
  assert.match(markdown.body, /^# thetattoo\.world/);
  assert.match(markdown.body, /## Open tattoo artist directory/);
  assert.match(markdown.body, /\/docs\)/);
  const http = toMarkdownHttp(markdown, "GET");
  assert.equal(http.headers["Content-Type"], "text/markdown; charset=utf-8");
  assert.equal(http.headers.Vary, "Accept");
  assert.ok(http.body.length > 500);

  const html = decideAgentResponse({ pathname: "/", method: "GET", accept: "text/html" });
  assert.equal(html.action, "next");
});

test("unknown paths return a markdown 404 with a docs link", () => {
  const decision = decideAgentResponse({
    pathname: "/__ora-404-probe-454xnqur",
    method: "GET",
    accept: "text/markdown",
  });
  assert.equal(decision.action, "markdown");
  if (decision.action !== "markdown") return;
  assert.equal(decision.status, 404);
  const http = toMarkdownHttp(decision, "GET");
  assert.equal(http.headers["Content-Type"], "text/markdown; charset=utf-8");
  assert.match(http.headers.Vary, /Accept/);
  assert.ok(http.body.length >= 20);
  assert.match(http.body, /not found/i);
  assert.match(http.body, /https:\/\/thetattoo\.world\/(?:docs|sitemap\.xml|llms\.txt)/);
  assert.equal(notFoundMarkdown("/missing").includes("https://thetattoo.world/llms.txt"), true);

  const html = decideAgentResponse({
    pathname: "/__ora-404-probe-454xnqur",
    method: "GET",
    accept: "text/html",
  });
  assert.equal(html.action, "next");
});

test("API, OpenAPI, and artist routes stay on their own handlers", () => {
  for (const pathname of ["/api/artists/compact", "/openapi.json", "/llms.txt", "/sitemap.xml", "/artists/example"]) {
    const decision = decideAgentResponse({ pathname, method: "GET", accept: "text/markdown" });
    assert.equal(decision.action, "next", pathname);
  }
});

test("homepage HTML copy is long enough and links to the API docs", () => {
  const text = homepagePlainText();
  assert.ok(text.length >= 500, `homepage text is ${text.length} characters`);
  assert.match(text, new RegExp(HOME_TITLE));
  assert.equal(HOME_LINKS.some((link) => link.href === "/docs"), true);
  const noscript = homepageNoscriptHtml();
  assert.match(noscript, /<h1>/);
  assert.match(noscript, /href="\/docs"/);
  assert.equal(HTML_LANG, "en");
  assert.equal(OG_TYPE, "website");
  assert.match(OG_IMAGE_PATH, /^\/fav\/.+\.png$/);
  const homePage = fs.readFileSync(new URL("../app/page.tsx", import.meta.url), "utf8");
  assert.match(homePage, /type: OG_TYPE/);
  assert.match(homePage, /url: OG_IMAGE_PATH/);
  assert.match(homePage, /canonical: CANONICAL_PATH/);
});

test("trust pages have at least 500 characters", () => {
  assert.ok(sectionText(ABOUT_SECTIONS).length >= 500);
  assert.match(ABOUT_TITLE, /thetattoo\.world/);
  assert.ok(sectionText(CONTACT_SECTIONS).length >= 500);
  assert.match(CONTACT_TITLE, /thetattoo\.world/);

  const privacy = fs.readFileSync(new URL("../app/privacy/page.tsx", import.meta.url), "utf8");
  const privacyText = privacy
    .replace(/<[^>]+>/g, " ")
    .replace(/\{[^}]+\}/g, " ")
    .replace(/\s+/g, " ");
  assert.ok(privacyText.length >= 500, `privacy source text is ${privacyText.length} characters`);
});

test("llms.txt tells agents when to use the directory", () => {
  const text = buildLlmsTxt();
  assert.match(text, /## When to use this/i);
  assert.match(text, /Instagram handle/);
  assert.match(text, /Do not use thetattoo\.world to book a tattoo/);
  assert.match(text, /https:\/\/thetattoo\.world\/openapi\.json/);
  assert.match(text, /https:\/\/thetattoo\.world\/docs/);
});

test("OpenAPI spec is self-describing for function calling", () => {
  const spec = buildOpenApiSpec();
  assert.equal(spec.openapi, "3.1.0");
  assert.match(spec.info.title, /thetattoo\.world/);
  const operationIds: string[] = [];
  for (const [path, methods] of Object.entries(spec.paths)) {
    for (const [method, operation] of Object.entries(methods)) {
      assert.equal(typeof operation.operationId, "string", `${method} ${path} operationId`);
      assert.ok(operation.description.length > 20, `${method} ${path} description`);
      operationIds.push(operation.operationId);
      for (const parameter of operation.parameters ?? []) {
        assert.equal(typeof parameter.name, "string");
        assert.equal(typeof parameter.schema.type, "string");
        assert.ok(parameter.description.length > 0);
      }
      if (operation.requestBody) {
        assert.ok(operation.requestBody.content["application/json"].schema);
      }
      for (const response of Object.values(operation.responses)) {
        assert.ok(response.description.length > 0);
        const schema = response.content?.["application/json"]?.schema;
        assert.ok(schema, `${operation.operationId} response schema`);
      }
    }
  }
  assert.equal(new Set(operationIds).size, operationIds.length);
  assert.deepEqual(operationIds.sort(), [
    "getArtistById",
    "getMapPoints",
    "listArtists",
    "listArtistsAtLocations",
  ]);
});

test("JSON-LD identifies the organization and the product", () => {
  const data = buildJsonLd();
  const organization = data["@graph"].find((node) => node["@type"] === "Organization");
  assert.ok(organization);
  assert.equal(organization.contactPoint.contactType, "customer support");
  assert.match(organization.contactPoint.email, /@/);
  assert.equal(organization.address["@type"], "PostalAddress");
  assert.ok(organization.address.addressCountry);
  assert.equal(organization.name, "thetattoo.world");
  assert.match(organization.url, /^https:\/\/thetattoo\.world/);

  const app = data["@graph"].find((node) => node["@type"] === "SoftwareApplication");
  assert.ok(app);
  assert.equal(app.name, "thetattoo.world");
  assert.ok(app.description.length > 40);
  assert.match(app.url, /^https:\/\/thetattoo\.world/);
  assert.equal(app.offers["@type"], "Offer");
  assert.ok(app.author);
});

test("sitemap lists trust pages and artist profiles with lastmod", () => {
  const entries = buildSitemapEntries([
    { id: "example", updated_at: "2026-03-06" },
    { id: "older" },
  ]);
  const urls = entries.map((entry) => entry.url);
  for (const path of ["/", "/about", "/contact", "/privacy", "/docs"]) {
    assert.ok(urls.includes(`${SITE_ORIGIN}${path}`), path);
  }
  assert.ok(urls.includes(`${SITE_ORIGIN}/artists/example`));
  assert.equal(entries.every((entry) => /^\d{4}-\d{2}-\d{2}$/.test(entry.lastModified)), true);
  assert.equal(urls.some((url) => url.includes("/admin") || url.includes("/api/")), false);
});

test("docs headings stay sequential and name the product", () => {
  assert.match(DOCS_TITLE, /thetattoo\.world/);
  let previous = 1;
  for (const section of DOCS_SECTIONS) {
    const level = section.level ?? 2;
    assert.ok(level <= previous + 1, `${section.heading} skips a heading level`);
    previous = level;
  }
  assert.match(sectionText(DOCS_SECTIONS), /does not use an API key/);
  assert.match(sectionText(DOCS_SECTIONS), /Each server instance/);
  assert.match(sectionText(CONTACT_SECTIONS), /https:\/\/github\.com\/milnikov\/open-tattoo-artists\/issues/);
  assert.match(sectionText(DOCS_SECTIONS), /curl -sS https:\/\/thetattoo\.world\/api\/artists\/compact/);
});
