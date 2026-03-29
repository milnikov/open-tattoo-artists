#!/usr/bin/env sh
# Vercel "Ignored Build Step": exit 0 = skip build, non-zero = run build.
# https://vercel.com/docs/project-configuration/git-settings#ignored-build-step
#
# Skip when nothing under the web app, artist JSON source, or repo-root package.json changed.
# (e.g. scraper-only or docs-only commits won't spend build minutes.)

set -eu

prev="${VERCEL_GIT_PREVIOUS_SHA:-}"
curr="${VERCEL_GIT_COMMIT_SHA:-HEAD}"

# No baseline to compare (e.g. first deployment on a branch) — always build.
if [ -z "$prev" ]; then
  exit 1
fi

# Same commit (e.g. redeploy) — always build so manual redeploys still work.
if [ "$prev" = "$curr" ]; then
  exit 1
fi

# Shallow clones or rewritten history may not include the previous deployment SHA.
# Without it we cannot diff — build rather than skip or error.
if ! git rev-parse --verify "$prev^{commit}" >/dev/null 2>&1; then
  exit 1
fi

# Paths are relative to Root Directory (apps/web).
git diff --quiet "$prev" "$curr" -- \
  . \
  ../../data \
  ../../package.json
