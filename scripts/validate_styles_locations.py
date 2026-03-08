#!/usr/bin/env python3
"""
Validate artist styles and location (city/country) for wrong fillings.
Outputs a report; use --fix to apply corrections (location only; styles need manual review).
"""
import json
import re
import sys
from pathlib import Path

ARTISTS_DIR = Path(__file__).resolve().parents[1] / "data" / "artists"

# Non-style entries that were scraped as "styles" (sponsors, brands, etc.)
JUNK_STYLES = {
    "cheyenne_tattooequipment",
    "killerinktattoo",
    "leejonestattooist",
    "recoveryaftercare",
    "sponsor:",
    "tattoodefender",
    "tattooeverythingsupplies",
    "total_immortal_tattoos",
}

# Country names that must not appear in city field (Unknown is allowed per DATA_MODEL)
COUNTRY_NAMES_NO_CITY = {
    "United States", "United Kingdom", "Germany", "France", "Spain", "Italy",
    "Canada", "Australia", "Brazil", "Netherlands", "Belgium", "Austria",
    "Switzerland", "Poland", "Portugal", "Russia", "Ukraine", "Belarus",
    "Mexico", "Argentina", "Chile", "Colombia", "Japan", "South Korea",
    "New Zealand", "Ireland", "Sweden", "Norway", "Denmark", "Finland",
    "Romania", "Hungary", "Czech Republic", "Greece", "India", "Indonesia",
    "Philippines", "South Africa", "Egypt", "Israel", "Turkey",
    "Dominican Republic", "People's Republic Of China", "China",
}

# Style-like tokens that were wrongly concatenated into country field (strip from here)
STYLE_TAG_PATTERN = re.compile(
    r"\s+(?:REALISM|TRADITIONAL|ILLUSTRATIVE|BLACKWORK|DOTWORK|NEOTRADITIONAL|NEW SCHOOL|"
    r"PORTRAIT|MINIMALIST|WATERCOLOR|GEOMETRIC|LETTERING|HAND POKED|SACRED GEOMETRY|HENNA|"
    r"CONTEMPORARY|ABSTRACT|GRAPHIC|SKETCH WORK|SINGLE NEEDLE|CARTOON|KAWAII|ORIENTAL|"
    r"TRIBAL|POLYNESIAN|BIOMECHANICAL|SURREALISM|POP ART|ENGRAVINGS|NORDIC|SAK YANT|"
    r"FREEHAND|LINE ART|FINE LINE|MICRO-REALISM|COVER UPS|BLACK AND GREY|REALISMBLACK|"
    r"minimalist|ILLUSTRATIVECARTOON|ILLUSTRATIVESURREALISM|WATERCOLORILLUSTRATIVE|"
    r"BLACKWORKILLUSTRATIVE|TRADITIONALILLUSTRATIVE|NEOTRADITIONALILLUSTRATIVE)"
    r".*",
    re.IGNORECASE,
)

# Region/state/area -> canonical country (for normalizing wrong country field)
REGION_TO_COUNTRY = {
    "Greater London": "United Kingdom",
    "Community of Madrid": "Spain",
    "Leinster": "Ireland",
    "Scotland": "United Kingdom",
    "Wales": "United Kingdom",
    "England": "United Kingdom",
    "Ontario": "Canada",
    "Quebec": "Canada",
    "British Columbia": "Canada",
    "Alberta": "Canada",
    "Manitoba": "Canada",
    "Victoria": "Australia",
    "Queensland": "Australia",
    "New South Wales": "Australia",
    "South Australia": "Australia",
    "Western Australia": "Australia",
    "Nevada": "United States",
    "Virginia": "United States",
    "Colorado": "United States",
    "Tennessee": "United States",
    "Indiana": "United States",
    "Michigan": "United States",
    "Missouri": "United States",
    "Pennsylvania": "United States",
    "New Jersey": "United States",
    "Jersey": "United Kingdom",
    "Essex": "United Kingdom",
    "Leicestershire": "United Kingdom",
    "South Holland": "Netherlands",
    "North Holland": "Netherlands",
    "North Brabant": "Netherlands",
    "Overijssel": "Netherlands",
    "Minsk Region": "Belarus",
    "Central Taiwan": "Taiwan",
    "Southern Taiwan": "Taiwan",
    "Taiwan": "Taiwan",
    "Hong Kong-china": "China",
    "Macau-china": "China",
    "Hong Kong": "China",
    "Macau": "China",
    "French-reunion": "France",
    "French Polynesia": "France",
    "Asturias": "Spain",
    "Balearic Islands": "Spain",
    "Cantabria": "Spain",
    "Navarre": "Spain",
    "Bizkaia - Vizcaya": "Spain",
    "Greater Manchester": "United Kingdom",
    "West Yorkshire": "United Kingdom",
    "East Sussex": "United Kingdom",
    "East Yorkshire": "United Kingdom",
    "Hampshire": "United Kingdom",
    "Hertfordshire": "United Kingdom",
    "Suffolk": "United Kingdom",
    "Surrey": "United Kingdom",
    "Cambridgeshire": "United Kingdom",
    "Derbyshire": "United Kingdom",
    "Lancashire": "United Kingdom",
    "Merseyside": "United Kingdom",
    "Northamptonshire": "United Kingdom",
    "Oxfordshire": "United Kingdom",
    "Warwickshire": "United Kingdom",
    "South Glamorgan": "United Kingdom",
    "West Glamorgan": "United Kingdom",
    "South Yorkshire": "United Kingdom",
    "Tyne and Wear": "United Kingdom",
    "Arrondissement Kortrijk": "Belgium",
    "Arrondissement de Bordeaux": "France",
    "Arrondissement de Lyon": "France",
    "Arrondissement de Marseille": "France",
    "Arrondissement de Nice": "France",
    "Arrondissement de Perpignan": "France",
    "Arrondissement de Pontoise": "France",
    "Arrondissement de Rennes": "France",
    "Arrondissement de Strasbourg-Ville": "France",
    "Arrondissement de Toulon": "France",
    "Central Greece": "Greece",
    "Central Macedonia": "Greece",
    "Limassol District": "Cyprus",
    "Kreis Viersen": "Germany",
    "Landkreis Kitzingen": "Germany",
    "Landkreis Ravensburg": "Germany",
    "Stadtkreis Heidelberg": "Germany",
    "Stadtkreis Mannheim": "Germany",
    "Stadtkreis Ulm": "Germany",
    "Villach Stadt": "Austria",
    "Leningrad Oblast": "Russia",
    "Moscow Oblast": "Russia",
    "Krasnodar Krai": "Russia",
    "Krasnoyarsk Krai": "Russia",
    "Novosibirsk Oblast": "Russia",
    "Odessa Oblast": "Ukraine",
    "Samara Oblast": "Russia",
    "Sverdlovsk Oblast": "Russia",
    "Vladimir Oblast": "Russia",
    "Lower Silesian Voivodeship": "Poland",
    "Masovian Voivodeship": "Poland",
    "Podkarpackie Voivodeship": "Poland",
    "Silesian Voivodeship": "Poland",
    "Grande Lisboa": "Portugal",
    "Barreiro": "Portugal",
    "Lima Region": "Peru",
    "Antioquia Department": "Colombia",
    "Cundinamarca Department": "Colombia",
    "Chihuahua State": "Mexico",
    "Rio de Janeiro State": "Brazil",
    "Minas Gerais": "Brazil",
    "Rio Grande do Sul": "Brazil",
    "Brest Region": "Belarus",
    "Capital Region of Denmark": "Denmark",
    "Pirkanmaa": "Finland",
    "Wellington Region": "New Zealand",
    "Kanagawa Prefecture": "Japan",
    "Bangkok Metropolitan Region": "Thailand",
    "Western Cape": "South Africa",
    "Mira": "Portugal",
    "Trinidad And Tobago": "Trinidad and Tobago",
    "USA": "United States",
}


def normalize_country(country: str) -> str:
    """Strip style tags and map region -> country. Returns normalized country or original if already clean."""
    if not country or not country.strip():
        return "Unknown"
    raw = country.strip()
    cleaned = STYLE_TAG_PATTERN.sub("", raw).strip()
    if not cleaned:
        return "Unknown"
    if cleaned in REGION_TO_COUNTRY:
        return REGION_TO_COUNTRY[cleaned]
    if cleaned.upper() == "USA":
        return "United States"
    return cleaned


def main():
    fix = "--fix" in sys.argv
    style_issues = []
    location_issues = []
    junk_found = []
    country_issues = []

    for f in sorted(ARTISTS_DIR.glob("*.json")):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except Exception as e:
            location_issues.append((f.stem, "city", "country", f"parse error: {e}"))
            continue

        aid = data.get("id") or f.stem
        loc = data.get("location") or {}
        city = (loc.get("city") or "").strip()
        country = (loc.get("country") or "").strip()

        # Location: empty
        if not city:
            location_issues.append((aid, city, country, "empty city"))
        if not country:
            location_issues.append((aid, city, country, "empty country"))

        # Location: country name in city field (city="Unknown" is allowed)
        if city and city in COUNTRY_NAMES_NO_CITY:
            location_issues.append((aid, city, country, "city is a country name (wrong filling)"))
            if fix:
                data["location"]["city"] = "Unknown"
                if not country or country == "Unknown":
                    if aid == "bashi_art_chuan":
                        data["location"]["country"] = "China"
                    elif aid == "blackvelvettattoos":
                        data["location"]["country"] = "United States"
                    else:
                        data["location"]["country"] = city

        # Location: strange country (style tags or region instead of country)
        normalized = normalize_country(country)
        if normalized != country:
            country_issues.append((aid, country, normalized))
            if fix:
                data["location"]["country"] = normalized

        # Styles: junk entries
        styles = data.get("styles") or []
        bad = [s for s in styles if s in JUNK_STYLES]
        if bad:
            junk_found.append((aid, bad, styles))
            if fix:
                data["styles"] = [s for s in styles if s not in JUNK_STYLES]

        if fix and (city in COUNTRY_NAMES_NO_CITY or bad or normalized != country):
            f.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    # Report
    print("=== STYLES: wrong fillings (non-style tags) ===\n")
    for aid, bad, all_styles in junk_found:
        print(f"  {aid}: remove {bad} from {all_styles}")
    print(f"\nTotal artists with junk styles: {len(junk_found)}\n")

    print("=== LOCATION: wrong fillings (country in city field) ===\n")
    loc_wrong = [x for x in location_issues if "country name" in x[3]]
    for aid, city, country, issue in loc_wrong:
        print(f"  {aid}: city={city!r} country={country!r} -> {issue}")
    print(f"\nTotal location issues (country-in-city): {len(loc_wrong)}\n")

    print("=== LOCATION: strange country (style tags / region in country field) ===\n")
    for aid, raw, norm in country_issues[:80]:
        print(f"  {aid}: {raw!r} -> {norm!r}")
    if len(country_issues) > 80:
        print(f"  ... and {len(country_issues) - 80} more")
    print(f"\nTotal strange country: {len(country_issues)}\n")

    if fix:
        print("Applied --fix: location and junk styles corrected in place.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
