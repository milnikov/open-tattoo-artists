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

# Compound style strings to split into two separate styles
COMPOUND_STYLES = {
    "black and grey micro-realism": ["black&gray", "micro-realism"],
    "color micro-realism": ["watercolor", "micro-realism"],
}

# Alias -> canonical style (merge duplicates; canonical form used in data)
STYLE_NORMALIZE = {
    "new school": "newschool",
    "cover ups": "coverup",
    "trash polka": "trashpolka",
    "fine line": "fineline",
    "line art": "fineline",
    "single needle": "fineline",
    "blackout": "blackwork",
    "japanese · irezumi": "japanese",
    "japanese irezumi": "japanese",
}

# Non-style entries that were scraped as "styles" (sponsors, brands, celebrity names, fake themes, etc.)
JUNK_STYLES = {
    "cara delevingne",
    "celebrity couple tattoos",
    "cheyenne_tattooequipment",
    "erotic",
    "love tattoos",
    "ellie goulding",
    "florence welch",
    "justin bieber",
    "katy perry",
    "killerinktattoo",
    "leejonestattooist",
    "recoveryaftercare",
    "rihanna",
    "sponsor:",
    "stencils",
    "tattoodefender",
    "tattooeverythingsupplies",
    "total_immortal_tattoos",
    "balm_tattoo",
    # Sponsor/brand strings from new artist data
    "venomink.com",
    "bluebirdneedles",
    "paulocruzes",
    "barber_dts",
    "z00tatt00",
    "h2oceanloyalty",
    "tropicaldermoficial",
    "fusion_ink",
    "hardliferotaries",
    "radiantcolorsink",
    "worldfamousink",
    "live.co.uk",
    "killers.kings",
    "axysrotary",
    "sheacare4u",
    "sickcartridges",
    "sumuntattoo",
    "yayofamilia",
    "hooligancarts",
    "jetpackwireless",
    "hardcraftcompany",
    "grupo_amazon",
    "ronintattoocare",
    "peakneedles",
    "goliathneedles",
    "inkedout_uk",
    "fantasiaartsupply",
    "crocarttattoocare",
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
    r"LOVE TATTOOS|EROTIC|PIN-UP|PINUP|EROTICPIN-UP|TATTOOSEROTIC|"
    r"BLACKWORKILLUSTRATIVE|TRADITIONALILLUSTRATIVE|NEOTRADITIONALILLUSTRATIVE|"
    r"COLOR MICRO-REALISM|MICRO-REALISMCOLOR| · IREZUMI|IREZUMI|ART NOUVEAU|RECONSTRUCTIVE|POST MASTECTOMY|BORNEO|CROSS STITCH|CONTINUOUS L|"
    r"OP ARTSACRED GEOMETRY|1 TATTOO|1 LIKE|2 FOLLOWERS|more_hori)"
    r".*",
    re.IGNORECASE,
)

# Non-country strings (cookie banners, etc.) -> treat as Unknown
COUNTRY_JUNK_PATTERN = re.compile(
    r"WE CONSIDER THAT YOU AGREE|COOKIE POLICY|LEARN MORE ABOUT",
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
    "Kreisfreie Stadt Köln": "Germany",
    "Villach Stadt": "Austria",
    "California": "United States",
    "Los Angeles County": "United States",
    "New York City": "United States",
    "Illinois": "United States",
    "Cook County": "United States",
    "Alameda County": "United States",
    "Barcelona Province": "Spain",
    "Province of Granada": "Spain",
    "Province of Alicante": "Spain",
    "Province of Rome": "Italy",
    "Province of Turin": "Italy",
    "Province of Naples": "Italy",
    "Gipuzkoa - Guipúzcoa": "Spain",
    "Plzeň Region": "Czech Republic",
    "Aveiro District": "Portugal",
    "Federal District (Brazil)": "Brazil",
    "Rio de Janeiro State": "Brazil",
    "São Paulo State": "Brazil",
    "Santa Fe Province": "Argentina",
    "Buenos Aires Province": "Argentina",
    "Tirana County": "Albania",
    "Tel Aviv District": "Israel",
    "Ankara Province": "Turkey",
    "Sarawak": "Malaysia",
    "Special Region of Yogyakarta": "Indonesia",
    "Utrecht (province)": "Netherlands",
    "Île-de-France": "France",
    "Arrondissement de Grenoble": "France",
    "Attica": "Greece",
    "Brussels-Capital Region": "Belgium",
    "Bezirk Zürich": "Switzerland",
    "Kiev Oblast": "Ukraine",
    "Kaliningrad Oblast": "Russia",
    "Leningrad Oblast": "Russia",
    "Jalisco": "Mexico",
    "Arrondissement de Bayonne": "France",
    "Kantō region": "Japan",
    "Istanbul Province": "Turkey",
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
    # Japan prefectures
    "Aichi Prefecture": "Japan",
    "Chiba Prefecture": "Japan",
    "Gunma Prefecture": "Japan",
    "Kyoto Prefecture": "Japan",
    "Saitama Prefecture": "Japan",
    # Brazil states/regions
    "Bahia": "Brazil",
    "Ceará": "Brazil",
    "Goiás": "Brazil",
    "Maranhão": "Brazil",
    "Paraná State": "Brazil",
    # US states and counties
    "Arizona": "United States",
    "Maryland": "United States",
    "Allegheny County": "United States",
    "Bucks County": "United States",
    "Dallas County": "United States",
    "Denver County": "United States",
    "Floyd County": "United States",
    "Harris County": "United States",
    "King County": "United States",
    "Lane County": "United States",
    "Miami-Dade County": "United States",
    "Multnomah County": "United States",
    "Muskegon County": "United States",
    "Oakland County": "United States",
    "Orange County": "United States",
    "Philadelphia County": "United States",
    "Santa Cruz County": "United States",
    "Travis County": "United States",
    "Wayne County": "United States",
    # UK counties/regions
    "Berkshire": "United Kingdom",
    "Devon": "United Kingdom",
    "Dorset": "United Kingdom",
    "Kent": "United Kingdom",
    "Norfolk": "United Kingdom",
    "Nottinghamshire": "United Kingdom",
    "Shropshire": "United Kingdom",
    "Staffordshire": "United Kingdom",
    "Worcestershire": "United Kingdom",
    # France/Belgium arrondissements
    "Arrondissement Hasselt": "Belgium",
    "Arrondissement Maaseik": "Belgium",
    "Arrondissement de Boulogne-Billancourt": "France",
    "Arrondissement de Clermont-Ferrand": "France",
    "Arrondissement de Lille": "France",
    "Arrondissement de Liège": "Belgium",
    "Arrondissement de Toulouse": "France",
    "Arrondissement de Verviers": "Belgium",
    "Arrondissement du Havre": "France",
    "Arrondissement d'Albi": "France",
    "Arrondissement d'Annecy": "France",
    "Arrondissement d\u2019Albi": "France",  # curly apostrophe
    "Arrondissement d\u2019Annecy": "France",  # curly apostrophe
    # Other regions
    "Auckland Region": "New Zealand",
    "Central Bohemian Region": "Czech Republic",
    "Bursa Province": "Turkey",
    "İzmir Province": "Turkey",
    "Formosa Province": "Argentina",
    "La Pampa Province": "Argentina",
    "Misiones Province": "Argentina",
    "Province of Bergamo": "Italy",
    "Province of Brescia": "Italy",
    "Province of Cagliari": "Italy",
    "Province of Girona": "Spain",
    "Province of Milan": "Italy",
    "Province of Monza and Brianza": "Italy",
    "Province of Padua": "Italy",
    "Province of Pavia": "Italy",
    "Province of Treviso": "Italy",
    "Province of Valencia": "Spain",
    "Province of Zaragoza": "Spain",
    "Region of Murcia": "Spain",
    "Region of Southern Denmark": "Denmark",
    "Nitra Region": "Slovakia",
    "Dnipropetrovsk Oblast": "Ukraine",
    "Nizhny Novgorod Oblast": "Russia",
    "Republic of Tatarstan": "Russia",
    "Rostov Oblast": "Russia",
    "Republika Srpska": "Bosnia and Herzegovina",
    "City of Belgrade": "Serbia",
    "Gyeonggi Province": "South Korea",
    "Maharashtra": "India",
    "Sichuan": "China",
    "State of Mexico": "Mexico",
    "Nuevo León": "Mexico",
    "Santiago Province": "Chile",
    "Santander Department": "Colombia",
    "Canary Islands": "Spain",
    "Crimea": "Ukraine",
    "Puerto Rico": "United States",
    "Jura-Nord vaudois District": "Switzerland",
    "Veveyse District": "Switzerland",
    "Kreis Wesel": "Germany",
    "Kreisfreie Stadt Essen": "Germany",
    "Kreisfreie Stadt München": "Germany",
    "Landeshauptstadt Magdeburg": "Germany",
    "Landkreis Heilbronn": "Germany",
    "Landkreis Lindau": "Germany",
    "Landkreis Offenbach": "Germany",
    "Stadtkreis Stuttgart": "Germany",
    "North Karelia": "Finland",
    "Pest County": "Hungary",
    "Skåne County": "Sweden",
    "Örebro County": "Sweden",
    "Distrito de Viseu": "Portugal",
    "Sintra": "Portugal",
    "Skopje Statistical Region": "North Macedonia",
    # More regions from validation
    "Kreisfreie Stadt Braunschweig": "Germany",
    "Opole Voivodeship": "Poland",
    "Western Australia": "Australia",
    "South Australia": "Australia",
    "San José Province": "Costa Rica",
    "Province of Málaga": "Spain",
    "Province of Seville": "Spain",
    "Union County": "United States",
    "Jefferson County": "United States",
    "Oregon": "United States",
    "Arrondissement d'Albertville": "France",
    "Arrondissement d\u2019Albertville": "France",
    "Somerset": "United Kingdom",
    "Frankfurt am Main": "Germany",
    # More regions from validation
    "Oberbergischer Kreis": "Germany",
    "Morges District": "Switzerland",
    "West Sussex": "United Kingdom",
    "Province of Neuquén": "Argentina",
    "San Bernardino County": "United States",
    "Sonora": "Mexico",
    "Hennepin County": "United States",
    "Province of Cádiz": "Spain",
    "Suffolk County": "United States",
    "Arrondissement de Cosne-Cours-sur-Loire": "France",
    "Kreisfreie Stadt Leverkusen": "Germany",
    "Lesser Poland Voivodeship": "Poland",
    "Lausanne District": "Switzerland",
    "Eisenstadt Stadt": "Austria",
    "Arrondissement de Mulhouse": "France",
    "Arrondissement d'Épinal": "France",
    "Arrondissement d\u2019Épinal": "France",
    "Osceola County": "United States",
    "Trnava Region": "Slovakia",
    "West Midlands County": "United Kingdom",
    "Northamptonshire": "United Kingdom",
    "Cornwall": "United Kingdom",
    # More regions
    "Geary County": "United States",
    "Province of Trieste": "Italy",
    "Fulton County": "United States",
    "Antalya Province": "Turkey",
    "Nassau County": "United States",
    "Suffolk": "United Kingdom",
    "Province of Palermo": "Italy",
    "Arrondissement du Puy": "France",
    "Province of Bologna": "Italy",
    "Upper Carniola": "Slovenia",
    "Gloucestershire": "United Kingdom",
    "Arrondissement de Mons": "Belgium",
    "Province of Modena": "Italy",
    "Province of Almería": "Spain",
}


def normalize_country(country: str) -> str:
    """Strip style tags and map region -> country. Returns normalized country or original if already clean."""
    if not country or not country.strip():
        return "Unknown"
    raw = country.strip()
    if COUNTRY_JUNK_PATTERN.search(raw):
        return "Unknown"
    cleaned = STYLE_TAG_PATTERN.sub("", raw).strip()
    if not cleaned:
        return "Unknown"
    if COUNTRY_JUNK_PATTERN.search(cleaned):
        return "Unknown"
    if cleaned in REGION_TO_COUNTRY:
        return REGION_TO_COUNTRY[cleaned]
    if cleaned.upper() == "USA":
        return "United States"
    return cleaned


def normalize_city(city: str) -> str:
    """Strip style tags from city (e.g. 'Singapore SINGLE NEEDLE...' -> 'Singapore'). 'On the road' -> Unknown."""
    if not city or not city.strip():
        return "Unknown"
    raw = city.strip()
    cleaned = STYLE_TAG_PATTERN.sub("", raw).strip()
    if not cleaned:
        return "Unknown"
    if cleaned.lower().startswith("on the road"):
        return "Unknown"
    return cleaned


def main():
    fix = "--fix" in sys.argv
    style_issues = []
    location_issues = []
    junk_found = []
    compound_found_list = []  # (aid, compound_style, expanded)
    style_normalize_list = []  # (aid, before, after)
    country_issues = []
    city_issues = []

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
        normalized_country = normalize_country(country)
        if normalized_country != country:
            country_issues.append((aid, country, normalized_country))
            if fix:
                data["location"]["country"] = normalized_country

        # Location: strange city (style tags concatenated, e.g. "Singapore SINGLE NEEDLE...", "On the road ILLUSTRATIVE...")
        normalized_city = normalize_city(city)
        if normalized_city != city:
            city_issues.append((aid, city, normalized_city))
            if fix:
                data["location"]["city"] = normalized_city
                # If city was "Singapore ..." or "Hong Kong ...", set country if missing
                if not country or country == "Unknown":
                    if normalized_city == "Singapore":
                        data["location"]["country"] = "Singapore"
                    elif normalized_city == "Hong Kong":
                        data["location"]["country"] = "China"

        # Styles: junk entries
        styles = list(data.get("styles") or [])
        bad = [s for s in styles if s in JUNK_STYLES]
        if bad:
            junk_found.append((aid, bad, list(styles)))
            if fix:
                styles = [s for s in styles if s not in JUNK_STYLES]
                data["styles"] = styles

        # Styles: split compound styles into two (e.g. "black and grey micro-realism" -> black&gray + micro-realism)
        compound_found = [s for s in styles if s in COMPOUND_STYLES]
        if compound_found:
            compound_found_list.append((aid, compound_found, [part for c in compound_found for part in COMPOUND_STYLES[c]]))
            if fix:
                new_styles = [s for s in styles if s not in COMPOUND_STYLES]
                for comp in compound_found:
                    for part in COMPOUND_STYLES[comp]:
                        if part not in new_styles:
                            new_styles.append(part)
                data["styles"] = new_styles
                styles = new_styles

        # Styles: normalize aliases (merge duplicates: new school->newschool, line art/fine line/single needle->fineline, blackout->blackwork, etc.)
        current_styles = data.get("styles", styles) if fix else styles
        normalized_styles = []
        seen = set()
        for s in current_styles:
            canon = STYLE_NORMALIZE.get(s, s)
            if canon not in seen:
                seen.add(canon)
                normalized_styles.append(canon)
        style_normalize_changed = normalized_styles != current_styles
        if style_normalize_changed:
            style_normalize_list.append((aid, current_styles, normalized_styles))
            if fix:
                data["styles"] = normalized_styles

        if fix and (city in COUNTRY_NAMES_NO_CITY or bad or compound_found or style_normalize_changed or normalized_country != country or normalized_city != city):
            f.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    # Report
    print("=== STYLES: wrong fillings (non-style tags) ===\n")
    for aid, bad, all_styles in junk_found:
        print(f"  {aid}: remove {bad} from {all_styles}")
    print(f"\nTotal artists with junk styles: {len(junk_found)}\n")

    print("=== STYLES: compound split (one string -> two styles) ===\n")
    for aid, comps, parts in compound_found_list:
        print(f"  {aid}: {comps} -> {parts}")
    print(f"\nTotal artists with compound styles split: {len(compound_found_list)}\n")

    print("=== STYLES: normalized (alias -> canonical, merged duplicates) ===\n")
    for aid, before, after in style_normalize_list[:50]:
        print(f"  {aid}: {before} -> {after}")
    if len(style_normalize_list) > 50:
        print(f"  ... and {len(style_normalize_list) - 50} more")
    print(f"\nTotal artists with styles normalized: {len(style_normalize_list)}\n")

    print("=== LOCATION: wrong fillings (country in city field) ===\n")
    loc_wrong = [x for x in location_issues if "country name" in x[3]]
    for aid, city, country, issue in loc_wrong:
        print(f"  {aid}: city={city!r} country={country!r} -> {issue}")
    print(f"\nTotal location issues (country-in-city): {len(loc_wrong)}\n")

    print("=== LOCATION: strange city (style tags in city field) ===\n")
    for aid, raw, norm in city_issues[:40]:
        print(f"  {aid}: {raw!r} -> {norm!r}")
    if len(city_issues) > 40:
        print(f"  ... and {len(city_issues) - 40} more")
    print(f"\nTotal strange city: {len(city_issues)}\n")

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
