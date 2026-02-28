const BASE = process.env.NEXT_PUBLIC_IMAGES_BASE_URL || "";

export function imageUrl(pathOrUrl: string): string {
  if (pathOrUrl.startsWith("http")) return pathOrUrl;
  if (!BASE) return pathOrUrl;
  return `${BASE.replace(/\/$/, "")}/${pathOrUrl.replace(/^\//, "")}`;
}
