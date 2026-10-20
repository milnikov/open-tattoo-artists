import { homepageNoscriptHtml } from "@/lib/agent-surface";

/**
 * Agent-readable homepage copy for clients that do not run JavaScript.
 * Browsers with JavaScript ignore noscript, so the directory layout is unchanged.
 */
export function HomeIntro() {
  return <noscript dangerouslySetInnerHTML={{ __html: homepageNoscriptHtml() }} />;
}
