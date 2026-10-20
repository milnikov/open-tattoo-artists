import { buildOpenApiSpec } from "@/lib/agent-surface";

export function GET() {
  return Response.json(buildOpenApiSpec(), {
    headers: {
      "Cache-Control": "public, max-age=3600",
    },
  });
}
