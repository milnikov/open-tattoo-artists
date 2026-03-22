import fs from "fs";
import path from "path";

/**
 * Directory that contains `data/` (indexes, styles). Vercel uses cwd = apps/web → ../..
 * If you run Next with cwd = repo root, `data/indexes/countries.json` sits directly under cwd.
 * Uses one concrete existsSync path (not a scan of parent dirs) so Turbopack does not trace 15k files.
 */
export function getRepoRoot(): string {
  const cwd = process.cwd();
  if (fs.existsSync(path.join(cwd, "data", "indexes", "countries.json"))) {
    return cwd;
  }
  return path.resolve(cwd, "..", "..");
}
