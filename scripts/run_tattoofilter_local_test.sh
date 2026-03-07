#!/bin/bash
# Quick local test: run TattooFilter pipeline on 2 artists, no R2, no git.
# Run from repo root. Requires Chrome/Chromedriver and venv with scraper deps.

set -e
cd "$(dirname "$0")/.."
source venv/bin/activate
export PYTHONPATH="$(pwd)/packages/scraper/src${PYTHONPATH:+:$PYTHONPATH}"

echo "🧪 TattooFilter local test: 2 artists, --no-r2"
python3 packages/scraper/src/pipeline_tattoofilter.py --limit 2 --no-r2 --no-git
