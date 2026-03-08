# Validation report: Artist styles & country/city

Summary of wrong fillings found and fixes applied (run: `python3 scripts/validate_styles_locations.py`).

## Styles – wrong fillings (non-style tags)

These entries were scraped as “styles” but are sponsor/brand tags, not tattoo styles. **Removed** from the listed artists:

| Wrong "style" | Description | Artists affected |
|---------------|-------------|------------------|
| `sponsor:`    | Label prefix  | 6 artists |
| `killerinktattoo` | Brand | boyetattoo, bradwallistattoo |
| `recoveryaftercare` | Brand | blackhatchettattoos |
| `tattoodefender` | Brand | borto_tattooer |
| `tattooeverythingsupplies` | Brand | bootattoo89 |
| `total_immortal_tattoos` | Brand | boomer_reagan |

**Total:** 6 artists corrected (junk styles removed).

---

## Country/City – wrong fillings

Per `docs/DATA_MODEL.md`, **city** must be a city name and **country** the country; use `"Unknown"` only when not known. In 20 records the **country name was in the city field**. These were corrected as follows:

- **city** set to `"Unknown"`
- **country** set to the value that was wrongly in city (or kept as-is when already correct)

| Artist ID | Before (city / country) | After |
|-----------|-------------------------|--------|
| _adamchenko_ | Belarus / Unknown | Unknown / Belarus |
| _mfox | Portugal / Unknown | Unknown / Portugal |
| aaronmedare, adambeardless, aquapixietattoos, ashlewistattoo, blakeytattooer | United Kingdom / Unknown | Unknown / United Kingdom |
| abiru_tattoo, ari_tattooer, bb_rung | South Korea / Unknown | Unknown / South Korea |
| adela_tattooer, anthony50tattoos, bk_tattooer, blackfeeltattoo | South Korea / South Korea | Unknown / South Korea |
| adamexiste | Spain / Unknown | Unknown / Spain |
| alves_ak, anamacedo_tattoo | Brazil / Unknown | Unknown / Brazil |
| andrewwatkinstattoos | India / Unknown | Unknown / India |
| bashi_art_chuan | People's Republic Of China / Unknown | Unknown / China |
| blackvelvettattoos | Mexico / United States | Unknown / United States (US artist; city was wrong) |

**Total:** 20 artists corrected.

---

## How to re-run

- **Report only:**  
  `python3 scripts/validate_styles_locations.py`

- **Apply fixes (location + junk styles):**  
  `python3 scripts/validate_styles_locations.py --fix`

Script: `scripts/validate_styles_locations.py`.
