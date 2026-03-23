#!/usr/bin/env python3
"""
Validate artist styles and location (city/country) for wrong fillings.
Outputs a report; use --fix to apply corrections (location only; styles need manual review).

Also infers country from city using global statistics (all artists, all regions): when a city
name overwhelmingly maps to one country, align Unknown/outlier/wrong scrape values — with
homonym-city safeguards (e.g. Paris, Portland: only fill Unknown, do not override US/FR).
"""
import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
ARTISTS_DIR = REPO_ROOT / "data" / "artists"
COUNTRIES_JSON = REPO_ROOT / "data" / "indexes" / "countries.json"

# Same city name in multiple countries: only set country when it is Unknown (never override US/UK/etc.).
CITY_MAJORITY_ONLY_FILL_UNKNOWN = frozenset(
    {
        "paris",
        "brighton",
        "portland",
        "manchester",
        "perth",
        "birmingham",
        "springfield",
        "columbus",
        "frankfurt",
        "moscow",
        "richmond",
        "santiago",
        "san jose",
        "valencia",
        "geneva",
        "troy",
        "odessa",
        "memphis",
        "washington",
        "glasgow",
        "alexandria",
        "tripoli",
        "melbourne",
        "lebanon",
        "georgia",
        "texas",
        "hollywood",
        "florence",
        "naples",
        "toronto",  # GTA vs Ohio — keep non-Unknown as-is
        "vancouver",  # BC vs WA
        "hamilton",
        "kingston",
        "san pedro",
        "san pedro de macorís",
        "monaco",
        "rome",
    }
)

# Italy was often scraped as country for Spanish (and some Latin) cities; always align to majority Spain/LatAm.
SPANISH_CITY_KEYS = frozenset(
    {
        "barcelona",
        "madrid",
        "valencia",
        "seville",
        "sevilla",
        "bilbao",
        "zaragoza",
        "malaga",
        "málaga",
        "murcia",
        "alicante",
        "granada",
        "cordoba",
        "córdoba",
        "cadiz",
        "cádiz",
        "valladolid",
        "santander",
        "pamplona",
        "toledo",
        "salamanca",
        "vigo",
        "gijón",
        "gijon",
        "oviedo",
        "burgos",
        "leon",
        "león",
        "almería",
        "almeria",
        "huelva",
        "tarragona",
        "lleida",
        "badajoz",
        "logroño",
        "logrono",
        "donostia - san sebastián",
        "donostia - san sebastian",
        "san sebastián",
        "san sebastian",
        "palma",
        "las palmas",
        "marbella",
        "sitges",
        "girona",
        "tenerife",
    }
)

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
    "atlastattoosupplies",
    "meaculpairons",
    "wildcatbarcelona",
    "kingpintattoosupply",
    "hotmail.com",
    "viking_inks",
    "xtremtattoo",
    "fkirons",
    "brouktattoosupply",
    "hushanesthetic",
    "goldinkcorp",
    "kwadron",
    "electrumstencilproducts",
    "needlejig",
    "tsunami_tattoo_needles",
    "fifthfingerstudio",
    "fistflame",
    "technicaltattoosupply",
    "inkjecta",
    "deluxeirons",
    "starrtattoosupplies",
    "starbritecolors",
    "juanpetattoo.es",
    "stigmarotary",
    "tattooarmourpro",
    "blkpowder",
    "mba.easytattoo",
    "gmail.com",
    "zootattoo",
    "kurosumitattooink",
    "eternalink",
    "relyaidtattoosupply",
    "inkofcocotattooskincare",
    # Brands / supplies / events / studios scraped as "styles" (browse UI)
    "bepantholtattoo",
    "chchtattooexpo",
    "elgatonegrotatt",
    "foreverforgottenaftercare",
    "fytsuppliesmy",
    "gattonerotattoo",
    "hardliferotaries.",
    "imperialinks",
    "intenzetattooink",
    "magnumtattoo",
    "nuclearwhiteink",
    "numbedrx",
    "panormostattoo",
    "premiertattoocare",
    "think_tattoo_aftercare",
    "tombowpt",
    "truegenttsttoosupplies",
    "ultimatetattoosupply",
    "dermacaretattoo",
    "monsterenergy",
    "industryinks",
    "eztattooing",
    "easyglowpigments",
    "skintattoocare",
    "believatattoo",
    "electricink",
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
    r"OP ARTSACRED GEOMETRY|1 TATTOO|1 LIKE|2 FOLLOWERS|more_hori|"
    r"EMBROIDERY|LACE|COSMETIC TATTOOING|MICROBLADING|TEBORI|FRECKLES)"
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
    "West Pomeranian Voivodeship": "Poland",
    "Kreisfreie Stadt Bonn": "Germany",
    "Essex County": "United States",
    "Arrondissement de Nancy": "France",
    "Napa County": "United States",
    "Province of Vicenza": "Italy",
    "North Yorkshire": "United Kingdom",
    "Surrey": "United Kingdom",
    # Belgium arrondissements
    "Arrondissement Antwerpen": "Belgium",
    "Arrondissement Gent": "Belgium",
    "Arrondissement Halle-Vilvoorde": "Belgium",
    "Arrondissement Turnhout": "Belgium",
    "Arrondissement de Charleroi": "Belgium",
    "Arrondissement de Dinant": "Belgium",
    "Arrondissement de Neufchâteau": "Belgium",
    # France arrondissements
    "Arrondissement d'Antony": "France",
    "Arrondissement de Beauvais": "France",
    "Arrondissement de Belley": "France",
    "Arrondissement de Besançon": "France",
    "Arrondissement de Céret": "France",
    "Arrondissement de Dijon": "France",
    "Arrondissement de Douai": "France",
    "Arrondissement de Draguignan": "France",
    "Arrondissement de Dunkerque": "France",
    "Arrondissement de Fontainebleau": "France",
    "Arrondissement de Forcalquier": "France",
    "Arrondissement de Gex": "France",
    "Arrondissement de Grasse": "France",
    "Arrondissement de La Roche-sur-Yon": "France",
    "Arrondissement de La Rochelle": "France",
    "Arrondissement de Lons-le-Saunier": "France",
    "Arrondissement de Lyon": "France",
    "Arrondissement de Metz-Ville": "France",
    "Arrondissement de Montluçon": "France",
    "Arrondissement de Nanterre": "France",
    "Arrondissement de Nantes": "France",
    "Arrondissement de Narbonne": "France",
    "Arrondissement de Nîmes": "France",
    "Arrondissement de Poitiers": "France",
    "Arrondissement de Ribeauvillé": "France",
    "Arrondissement de Rouen": "France",
    "Arrondissement de Saint-Dié": "France",
    "Arrondissement de Saint-Germain-en-Laye": "France",
    "Arrondissement de Saint-Étienne": "France",
    "Arrondissement de Torcy": "France",
    "Arrondissement de Tours": "France",
    "Arrondissement de Troyes": "France",
    "Arrondissement d'Aix-en-Provence": "France",
    "Arrondissement d\u2019Aix-en-Provence": "France",
    "Arrondissement d'Angers": "France",
    "Arrondissement d\u2019Angers": "France",
    "Arrondissement d'Orléans": "France",
    "Arrondissement d\u2019Orléans": "France",
    "Arrondissement of Montpellier": "France",
    # US counties
    "Atlantic County": "United States",
    "Bergen County": "United States",
    "Berks County": "United States",
    "Bernalillo County": "United States",
    "Bexar County": "United States",
    "Blue Earth County": "United States",
    "Boulder County": "United States",
    "Brevard County": "United States",
    "Broward County": "United States",
    "Caledonia County": "United States",
    "Chatham County": "United States",
    "Cheshire County": "United States",
    "Chester County": "United States",
    "Cobb County": "United States",
    "Coconino County": "United States",
    "Cumberland County": "United States",
    "Cuyahoga County": "United States",
    "Denton County": "United States",
    "Dutchess County": "United States",
    "El Paso County": "United States",
    "Erie County": "United States",
    "Forsyth County": "United States",
    "Franklin County": "United States",
    "Fresno County": "United States",
    "Gilmer County": "United States",
    "Hamilton County": "United States",
    "Hampshire County": "United States",
    "Hardin County": "United States",
    "Hays County": "United States",
    "Henry County": "United States",
    "Hernando County": "United States",
    "Hillsborough County": "United States",
    "Honolulu County": "United States",
    "Ingham County": "United States",
    "Island County": "United States",
    "Lake County": "United States",
    "Livingston County": "United States",
    "Los Angeles County": "United States",
    "Lowndes County": "United States",
    "Lubbock County": "United States",
    "Luzerne County": "United States",
    "Macomb County": "United States",
    "Maricopa County": "United States",
    "Maui County": "United States",
    "Mecklenburg County": "United States",
    "Medina County": "United States",
    "Middlesex County": "United States",
    "Monroe County": "United States",
    "Montgomery County": "United States",
    "New Haven County": "United States",
    "Ocean County": "United States",
    "Orange County": "United States",
    "Oxford County": "United States",
    "Palm Beach County": "United States",
    "Pasco County": "United States",
    "Pickaway County": "United States",
    "Pinellas County": "United States",
    "Providence County": "United States",
    "Riverside County": "United States",
    "Sacramento County": "United States",
    "Salt Lake County": "United States",
    "San Diego County": "United States",
    "Santa Barbara County": "United States",
    "Santa Clara County": "United States",
    "Spokane County": "United States",
    "Strafford County": "United States",
    "Summit County": "United States",
    "Utah County": "United States",
    "Ventura County": "United States",
    "Warren County": "United States",
    "Washington County": "United States",
    "Will County": "United States",
    # UK / Ireland
    "County Antrim": "United Kingdom",
    "County Durham": "United Kingdom",
    "County Tyrone": "United Kingdom",
    # Sweden
    "Stockholm County": "Sweden",
    "Västra Götaland County": "Sweden",
    "Dalarna County": "Sweden",
    "Gävleborg County": "Sweden",
    "Jönköping County": "Sweden",
    "Kronoberg County": "Sweden",
    "Östergötland County": "Sweden",
    "Västerbotten County": "Sweden",
    "Västmanland County": "Sweden",
    # Japan prefectures
    "Osaka Prefecture": "Japan",
    "Fukuoka Prefecture": "Japan",
    "Fukushima Prefecture": "Japan",
    "Iwate Prefecture": "Japan",
    "Okayama Prefecture": "Japan",
    "Okinawa Prefecture": "Japan",
    "Shiga Prefecture": "Japan",
    "Yamaguchi Prefecture": "Japan",
    "Kanagawa Prefecture": "Japan",
    # South Korea
    "South Chungcheong Province": "South Korea",
    "South Jeolla Province": "South Korea",
    # Poland voivodeships
    "Pomeranian Voivodeship": "Poland",
    "Greater Poland Voivodeship": "Poland",
    "Łódź Voivodeship": "Poland",
    "Lublin Voivodeship": "Poland",
    "Kuyavian-Pomeranian Voivodeship": "Poland",
    "Warmian-Masurian Voivodeship": "Poland",
    # Germany
    "Kreisfreie Stadt Leipzig": "Germany",
    "Kreisfreie Stadt Dortmund": "Germany",
    "Kreisfreie Stadt Würzburg": "Germany",
    "Kreisfreie Stadt Augsburg": "Germany",
    "Kreisfreie Stadt Darmstadt": "Germany",
    "Kreisfreie Stadt Düsseldorf": "Germany",
    "Kreisfreie Stadt Nürnberg": "Germany",
    "Kreisfreie Stadt Bochum": "Germany",
    "Kreisfreie Stadt Bielefeld": "Germany",
    "Kreisfreie Stadt Bremen": "Germany",
    "Kreisfreie Stadt Coburg": "Germany",
    "Kreisfreie Stadt Dresden": "Germany",
    "Kreisfreie Stadt Ingolstadt": "Germany",
    "Kreisfreie Stadt Kassel": "Germany",
    "Kreisfreie Stadt Kiel": "Germany",
    "Kreisfreie Stadt Koblenz": "Germany",
    "Kreisfreie Stadt Krefeld": "Germany",
    "Kreisfreie Stadt Köln": "Germany",
    "Kreisfreie Stadt Ludwigshafen am Rhein": "Germany",
    "Kreisfreie Stadt Lübeck": "Germany",
    "Kreisfreie Stadt Münster": "Germany",
    "Kreisfreie Stadt Oberhausen": "Germany",
    "Kreisfreie Stadt Remscheid": "Germany",
    "Kreisfreie Stadt Trier": "Germany",
    "Kreisfreie Stadt Wiesbaden": "Germany",
    "Kreisfreie Stadt Wuppertal": "Germany",
    "Ennepe-Ruhr-Kreis": "Germany",
    "Landkreis Barnim": "Germany",
    "Landkreis Böblingen": "Germany",
    "Landkreis Gießen": "Germany",
    "Landkreis Konstanz": "Germany",
    "Landkreis Neunkirchen": "Germany",
    "Landkreis Neuwied": "Germany",
    "Landkreis Passau": "Germany",
    "Landkreis Reutlingen": "Germany",
    "Landkreis Vechta": "Germany",
    "Region Hannover": "Germany",
    "Regionalverband Saarbrücken": "Germany",
    "Rems-Murr-Kreis": "Germany",
    "Rhein-Erft-Kreis": "Germany",
    "Stadtkreis Heilbronn": "Germany",
    "Stadtkreis Karlsruhe": "Germany",
    # Ukraine/Russia oblasts
    "Kharkiv Oblast": "Ukraine",
    "Cherkasy Oblast": "Ukraine",
    "Bryansk Oblast": "Russia",
    "Chelyabinsk Oblast": "Russia",
    "Kirov Oblast": "Russia",
    "Omsk Oblast": "Russia",
    "Tyumen Oblast": "Russia",
    "Voronezh Oblast": "Russia",
    "Yaroslavl Oblast": "Russia",
    # Italy provinces
    "Province of Bari": "Italy",
    "Province of Belluno": "Italy",
    "Province of A Coruña": "Spain",
    "Province of Tarragona": "Spain",
    "Province of Rimini": "Italy",
    "Province of Genoa": "Italy",
    "Province of Florence": "Italy",
    "Province of Castellón": "Spain",
    "Province of Las Palmas": "Spain",
    "Province of Pescara": "Italy",
    "Province of Ourense": "Spain",
    "Province of Lleida": "Spain",
    "Province of Verona": "Italy",
    "Province of Pontevedra": "Spain",
    "Province of Ravenna": "Italy",
    "Province of Ancona": "Italy",
    "Province of León": "Spain",
    "Province of Massa and Carrara": "Italy",
    "Province of Pistoia": "Italy",
    "Province of Varese": "Italy",
    "Province of Perugia": "Italy",
    "Province of Toledo": "Spain",
    "Province of Viterbo": "Italy",
    "Piacenza Province": "Italy",
    "Province of Badajoz": "Spain",
    "Province of Arezzo": "Italy",
    "Province of Campobasso": "Italy",
    "Province of Catanzaro": "Italy",
    "Province of Chieti": "Italy",
    "Province of Ciudad Real": "Spain",
    "Province of Como": "Italy",
    "Province of Cuenca": "Spain",
    "Province of Cuneo": "Italy",
    "Province of Cáceres": "Spain",
    "Province of Fermo": "Italy",
    "Province of Forlì-Cesena": "Italy",
    "Province of Grosseto": "Italy",
    "Province of Imperia": "Italy",
    "Province of Jaén": "Spain",
    "Province of Latina": "Italy",
    "Province of Lecco": "Italy",
    "Province of Livorno": "Italy",
    "Province of Lucca": "Italy",
    "Province of Mantua": "Italy",
    "Province of Messina": "Italy",
    "Province of Ourense": "Spain",
    "Province of Rovigo": "Italy",
    "Province of Santa Cruz de Tenerife": "Spain",
    "Province of South Sardinia": "Italy",
    "Province of Udine": "Italy",
    "Province of Valladolid": "Spain",
    "Province of Zamora": "Spain",
    # Spain/Argentina/Thailand/Costa Rica/Ecuador/Bolivia/Cuba
    "Chaco Province": "Argentina",
    "Mendoza Province": "Argentina",
    "Tierra del Fuego Province": "Argentina",
    "Santa Cruz Province": "Argentina",
    "Cordoba Province": "Argentina",
    "Chiang Mai Province": "Thailand",
    "Chonburi Province": "Thailand",
    "Surat Thani Province": "Thailand",
    "Trat Province": "Thailand",
    "Cartago Province": "Costa Rica",
    "Guanacaste Province": "Costa Rica",
    "Pichincha Province": "Ecuador",
    "Potosí Department": "Bolivia",
    "Holguín Province": "Cuba",
    # Other
    "Bay of Plenty Region": "New Zealand",
    "Central Denmark Region": "Denmark",
    "Canton of Geneva": "Switzerland",
    "Bern-Mittelland District": "Switzerland",
    "Biel/Bienne District": "Switzerland",
    "Region Imboden": "Switzerland",
    "Braga District": "Portugal",
    "Bratislava Region": "Slovakia",
    "South Moravian Region": "Czech Republic",
    "Liberec Region": "Czech Republic",
    "Drava Statistical Region": "Slovenia",
    "Borsod-Abaúj-Zemplén County": "Hungary",
    "Jász-Nagykun-Szolnok County": "Hungary",
    "Harju County": "Estonia",
    "Tartu County": "Estonia",
    "Vilnius County": "Lithuania",
    "Telšiai County": "Lithuania",
    "Nicosia District": "Cyprus",
    "Muğla Province": "Turkey",
    "Montevideo Department": "Uruguay",
    "Risaralda Department": "Colombia",
    "Paramaribo District": "Suriname",
    "Santiago Metropolitan Region": "Chile",
    "Coquimbo Region": "Chile",
    "Valparaíso Region": "Chile",
    "Talsi Municipality": "Latvia",
    # --- Fix: artists were storing subdivision/region names in `location.country` ---
    # Values below are taken from frontend-style "strange country" detection:
    # `country` not in `data/indexes/countries.json`.
    "Santa Catarina": "Brazil",
    "Espírito Santo": "Brazil",
    "People's Republic Of China": "China",
    "Península de Setúbal": "Portugal",
    "Tasmania": "Australia",
    "Cheshire": "United Kingdom",
    "Lincolnshire": "United Kingdom",
    "North Kuta": "Indonesia",
    "Gelderland": "Netherlands",
    "Gemeente Den Haag": "Netherlands",
    "Pernambuco": "Brazil",
    "Uusimaa": "Finland",
    "Valencian Community": "Spain",
    "Wiltshire": "United Kingdom",
    "Alagoas": "Brazil",
    "Algarve": "Portugal",
    "Bedfordshire": "United Kingdom",
    "Limburg": "Netherlands",
    "Metropolitan City of Venice": "Italy",
    "North Carolina": "United States",
    "Nova Scotia": "Canada",
    "Quintana Roo": "Mexico",
    "Rio Grande do Norte": "Brazil",
    "Saskatchewan": "Canada",
    "Altai Krai": "Russia",
    "Ayrshire and Arran": "United Kingdom",
    "Bali": "Indonesia",
    "Bashkortostan": "Russia",
    "Buckinghamshire": "United Kingdom",
    "Carabobo State": "Venezuela",
    "Chūbu region": "Japan",
    "Cumbria": "United Kingdom",
    "Dessau-Roßlau": "Germany",
    "Grande Porto": "Portugal",
    "Michoacán": "Mexico",
    "Nordland": "Norway",
    "Paraíba": "Brazil",
    "Perm Krai": "Russia",
    "Salzburg Stadt": "Austria",
    "South Tyrol": "Italy",
    "Wahlkreis Rheintal": "Switzerland",
    "Yucatán": "Mexico",
    "Zwickau (district)": "Germany",
    "Alabama": "United States",
    "Aosta Valley": "Italy",
    "Araba - Álava": "Spain",
    "Baden-Württemberg": "Germany",
    "Baja California": "Mexico",
    "Bezirk Winterthur": "Switzerland",
    "Canterbury": "United Kingdom",
    "Connecticut": "United States",
    "Eastern Cape": "South Africa",
    "Friesland": "Netherlands",
    "Fujian": "China",
    "Gauteng": "South Africa",
    "Graz Stadt": "Austria",
    "Herefordshire": "United Kingdom",
    "Hokkaido": "Japan",
    "Hordaland": "Norway",
    "Idaho": "United States",
    "Innsbruck Stadt": "Austria",
    "Iowa": "United States",
    "Khabarovsk Krai": "Russia",
    "Khanty-Mansi Autonomous Okrug": "Russia",
    "La Rioja": "Spain",
    "Lecce": "Italy",
    "Massachusetts": "United States",
    "Mato Grosso": "Brazil",
    "Matosinhos": "Portugal",
    "Metro Manila": "Philippines",
    "Mid Glamorgan": "United Kingdom",
    "New Brunswick": "Canada",
    "New York City OP ARTTRIBAL": "United States",
    "New York": "United States",
    "Newfoundland and Labrador": "Canada",
    "Northern Taiwan": "Taiwan",
    "Ortenaukreis": "Germany",
    "Otago": "New Zealand",
    "Perth and Kinross": "United Kingdom",
    "Politischer Bezirk Feldkirch": "Austria",
    "Politischer Bezirk Weiz": "Austria",
    "Provincia di Siracusa": "Italy",
    "Puebla": "Mexico",
    "Querétaro": "Mexico",
    "Republic of Karelia": "Russia",
    "Roraima": "Brazil",
    "Saalfeld-Rudolstadt": "Germany",
    "Saba And Sint Eustatius": "Netherlands",
    "San Luis Potosí": "Mexico",
    "Sonora OP ARTLINE ARTFINE LINESINGLE NEEDLE": "Mexico",
    "South Carolina": "United States",
    "State of Aguascalientes": "Mexico",
    "State of Guanajuato": "Mexico",
    "State of Zacatecas": "Mexico",
    "Steyr Stadt": "Austria",
    "Städteregion Aachen": "Germany",
    "São Paulo State OP ART": "Brazil",
    "The Bahamas": "Bahamas",
    "Troms": "Norway",
    "Vestfold": "Norway",
    "Vojvodina": "Serbia",
    "Vulkaneifel": "Germany",
    "West Bank": "Palestine",
    "West Flanders": "Belgium",
    "Wetteraukreis": "Germany",
    "Wyoming": "United States",
    "Østfold": "Norway",
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


def normalize_city_key(city: str) -> str:
    """Stable lowercase key for grouping one physical city across artists."""
    if not city or not city.strip() or city.strip().lower() == "unknown":
        return ""
    s = unicodedata.normalize("NFKC", city.strip().lower())
    s = re.sub(r"\s+", " ", s).strip()
    return s


def load_countries_official_by_lower() -> dict[str, str]:
    """Map lower(country) -> official string from countries.json."""
    if not COUNTRIES_JSON.is_file():
        return {}
    try:
        raw = json.loads(COUNTRIES_JSON.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(raw, list):
        return {}
    return {str(c).strip().lower(): str(c).strip() for c in raw if str(c).strip()}


def build_city_canonical_country_map(
    allowed_lower: dict[str, str],
    *,
    min_artists: int = 8,
    min_known: int = 6,
    min_top_share_of_known: float = 0.91,
    min_second_for_ambiguous: int = 5,
    second_share_ambiguous: float = 0.15,
) -> tuple[dict[str, str], dict[str, Counter]]:
    """
    From ALL artists, infer one canonical country per city when the data are
    overwhelmingly consistent (any region). Skips ambiguous cities (e.g. strong
    second country: Paris FR/US, Valencia ES/VE).
    """
    city_country: dict[str, Counter] = defaultdict(Counter)
    for f in sorted(ARTISTS_DIR.glob("*.json")):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        loc = data.get("location") or {}
        city = normalize_city((loc.get("city") or "").strip())
        if city == "Unknown":
            continue
        ck = normalize_city_key(city)
        if not ck:
            continue
        co_raw = (loc.get("country") or "").strip()
        if not co_raw:
            co_n = "Unknown"
        else:
            co_n = normalize_country(co_raw)
        city_country[ck][co_n] += 1

    out: dict[str, str] = {}
    for ck, cc in city_country.items():
        total_all = sum(cc.values())
        if total_all < min_artists:
            continue
        known = {c: n for c, n in cc.items() if c and c != "Unknown"}
        total_known = sum(known.values())
        if total_known < min_known:
            continue
        ranked = sorted(known.items(), key=lambda x: -x[1])
        top_c, top_n = ranked[0]
        second_n = ranked[1][1] if len(ranked) > 1 else 0
        if second_n >= max(min_second_for_ambiguous, int(second_share_ambiguous * total_known)):
            continue
        if top_n / total_known < min_top_share_of_known:
            continue
        low = top_c.strip().lower()
        if low not in allowed_lower:
            continue
        out[ck] = allowed_lower[low]
    return out, dict(city_country)


def should_fix_city_country_majority(
    ck: str,
    co_n: str,
    co_raw: str,
    canonical_c: str,
    cc: Counter | None,
) -> bool:
    """Whether to set country to canonical_c for this artist (conservative for homonym cities)."""
    if co_n.lower() == canonical_c.lower():
        return False
    if not cc:
        return False
    known = {c: n for c, n in cc.items() if c and c != "Unknown"}
    total_known = sum(known.values())
    if total_known < 1:
        return False

    if ck in CITY_MAJORITY_ONLY_FILL_UNKNOWN:
        return not co_raw.strip() or co_n == "Unknown"

    if not co_raw.strip() or co_n == "Unknown":
        return True

    if co_n == "Italy":
        if canonical_c == "Spain" and ck in SPANISH_CITY_KEYS:
            return True
        it_n = cc.get("Italy", 0)
        if canonical_c != "Italy" and it_n <= max(3, int(0.035 * total_known)):
            return True

    minority_n = cc.get(co_n, 0)
    if minority_n <= max(3, int(0.035 * total_known)):
        return True
    return False


def main():
    fix = "--fix" in sys.argv
    style_issues = []
    location_issues = []
    junk_found = []
    compound_found_list = []  # (aid, compound_style, expanded)
    style_normalize_list = []  # (aid, before, after)
    country_issues = []
    city_issues = []
    city_country_mismatch = []  # (aid, city, country_before, country_canonical, city_key)

    allowed_lower = load_countries_official_by_lower()
    city_canonical, city_country_counts = build_city_canonical_country_map(allowed_lower)

    for f in sorted(ARTISTS_DIR.glob("*.json")):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except Exception as e:
            location_issues.append((f.stem, "city", "country", f"parse error: {e}"))
            continue

        aid = data.get("id") or f.stem
        dirty = False
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
                dirty = True
                data["location"]["city"] = "Unknown"
                if not country or country == "Unknown":
                    if aid == "bashi_art_chuan":
                        data["location"]["country"] = "China"
                    elif aid == "blackvelvettattoos":
                        data["location"]["country"] = "United States"
                    else:
                        data["location"]["country"] = city

        # After mutating location above, refresh locals so normalize_* sees written values (--fix).
        if fix:
            loc = data.get("location") or {}
            city = (loc.get("city") or "").strip()
            country = (loc.get("country") or "").strip()

        # Location: strange country (style tags or region instead of country)
        normalized_country = normalize_country(country)
        if normalized_country != country:
            country_issues.append((aid, country, normalized_country))
            if fix:
                dirty = True
                data["location"]["country"] = normalized_country

        if fix:
            loc = data.get("location") or {}
            city = (loc.get("city") or "").strip()
            country = (loc.get("country") or "").strip()

        # Location: strange city (style tags concatenated, e.g. "Singapore SINGLE NEEDLE...", "On the road ILLUSTRATIVE...")
        normalized_city = normalize_city(city)
        if normalized_city != city:
            city_issues.append((aid, city, normalized_city))
            if fix:
                dirty = True
                data["location"]["city"] = normalized_city
                # If city was "Singapore ..." or "Hong Kong ...", set country if missing
                if not country or country == "Unknown":
                    if normalized_city == "Singapore":
                        data["location"]["country"] = "Singapore"
                    elif normalized_city == "Hong Kong":
                        data["location"]["country"] = "China"

        # Location: city ↔ country consistency (global majority over ALL artists / regions)
        city_line = (data.get("location") or {}).get("city") or ""
        city_eff = normalize_city(city_line.strip())
        ck = normalize_city_key(city_eff) if city_eff != "Unknown" else ""
        canonical_c = city_canonical.get(ck) if ck else None
        cc = city_country_counts.get(ck) if ck else None
        if canonical_c and cc is not None:
            co_line = (data.get("location") or {}).get("country") or ""
            co_raw = co_line.strip()
            if not co_raw:
                co_n = "Unknown"
            else:
                co_n = normalize_country(co_raw)
            if should_fix_city_country_majority(ck, co_n, co_raw, canonical_c, cc):
                city_country_mismatch.append((aid, city_eff, co_raw or co_n, canonical_c, ck))
                if fix:
                    dirty = True
                    data["location"]["country"] = canonical_c

        if fix:
            loc = data.get("location") or {}
            city = (loc.get("city") or "").strip()
            country = (loc.get("country") or "").strip()

        # Styles: junk entries
        styles = list(data.get("styles") or [])
        bad = [s for s in styles if s in JUNK_STYLES]
        if bad:
            junk_found.append((aid, bad, list(styles)))
            if fix:
                dirty = True
                styles = [s for s in styles if s not in JUNK_STYLES]
                data["styles"] = styles

        # Styles: split compound styles into two (e.g. "black and grey micro-realism" -> black&gray + micro-realism)
        compound_found = [s for s in styles if s in COMPOUND_STYLES]
        if compound_found:
            compound_found_list.append((aid, compound_found, [part for c in compound_found for part in COMPOUND_STYLES[c]]))
            if fix:
                dirty = True
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
                dirty = True
                data["styles"] = normalized_styles

        if fix and dirty:
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

    print("=== LOCATION: city vs country (global majority, all regions) ===\n")
    for aid, cty, co_bef, co_can, ck in city_country_mismatch[:80]:
        print(f"  {aid}: city={cty!r} country={co_bef!r} -> {co_can!r} (key={ck!r})")
    if len(city_country_mismatch) > 80:
        print(f"  ... and {len(city_country_mismatch) - 80} more")
    print(f"\nTotal city/country mismatches vs global majority: {len(city_country_mismatch)}\n")

    if fix:
        print("Applied --fix: location and junk styles corrected in place.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
