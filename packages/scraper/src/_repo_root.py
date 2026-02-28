"""Resolve repo root so scripts work when run from packages/scraper or packages/scraper/src."""
from pathlib import Path

# This file is packages/scraper/src/_repo_root.py
# parent=src, parent.parent=scraper, parent.parent.parent=packages, parent.parent.parent.parent=repo root
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent

def repo_path(*parts: str) -> Path:
    """Path under repo root. E.g. repo_path('discovered_pages.json') or repo_path('TATTOODO', 'discovered_pages.json')."""
    return _REPO_ROOT.joinpath(*parts)

REPO_ROOT = _REPO_ROOT
