#!/usr/bin/env python3
"""Refresh docs/wikipedia_list_of_tattoo_artists.json from English Wikipedia."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "wikipedia_list_of_tattoo_artists.json"
API = "https://en.wikipedia.org/w/api.php"
PAGE = "List_of_tattoo_artists"
SOURCE = "https://en.wikipedia.org/wiki/List_of_tattoo_artists"


def cell_text(el) -> str:
    t = el.get_text(" ", strip=True)
    return re.sub(r"\s+", " ", t)


def main() -> None:
    r = requests.get(
        API,
        params={"action": "parse", "page": PAGE, "prop": "text", "format": "json", "formatversion": "2"},
        headers={"User-Agent": "TattooArtistsRepo/1.0 (structured list export)"},
        timeout=60,
    )
    r.raise_for_status()
    html = r.json()["parse"]["text"]
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table", class_=lambda c: c and "wikitable" in c.split())
    if not table:
        sys.exit("No wikitable found on page")

    rows: list[dict] = []
    for tr in table.find_all("tr"):
        cells = tr.find_all(["th", "td"])
        if len(cells) < 4:
            continue
        if cells[0].name == "th" and "Name" in cell_text(cells[0]):
            continue
        name_cell, date_cell, nat_cell, note_cell = cells[0], cells[1], cells[2], cells[3]
        link = name_cell.find("a")
        title = link.get("title") if link and link.has_attr("title") else None
        href = link.get("href") if link else None
        wikipedia_url = urljoin("https://en.wikipedia.org", href) if href else None
        name = cell_text(name_cell)
        name = re.sub(r"\s*\[\d+\]\s*$", "", name).strip()
        rows.append(
            {
                "name": name,
                "wikipedia_title": title,
                "wikipedia_url": wikipedia_url,
                "life_dates": cell_text(date_cell),
                "nationality": cell_text(nat_cell),
                "note": cell_text(note_cell),
            }
        )

    out = {
        "source": SOURCE,
        "license": "Wikipedia text is CC BY-SA 4.0; this JSON is a structured extract for internal reference.",
        "retrieved_via": f"{API}?action=parse&page={PAGE}",
        "count": len(rows),
        "artists": rows,
    }
    OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {len(rows)} rows to {OUT}")


if __name__ == "__main__":
    main()
