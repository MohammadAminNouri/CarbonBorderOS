"""Configuration constants for CarbonBorderOS.

The app is designed to run immediately with demo values, then be upgraded by
replacing CSV files and optional API URLs with official/licensed data feeds.
"""
from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"

# Published first official CBAM certificate price for Q1 2026.
# Keep editable in Streamlit because official prices update quarterly in 2026
# and weekly from 2027 according to the European Commission.
DEFAULT_CBAM_PRICE_EUR_TCO2 = 75.36

# The 50 t annual mass threshold is modelled for covered goods. Electricity and
# hydrogen may require special treatment depending on the legal period and update.
DEFAULT_ANNUAL_THRESHOLD_TONNES = 50.0

OFFICIAL_LINKS = {
    "cbam_home": "https://taxation-customs.ec.europa.eu/carbon-border-adjustment-mechanism_en",
    "cbam_prices": "https://taxation-customs.ec.europa.eu/carbon-border-adjustment-mechanism/price-cbam-certificates_en",
    "cbam_guidance": "https://taxation-customs.ec.europa.eu/carbon-border-adjustment-mechanism/cbam-legislation-and-guidance_en",
    "eurostat_itg": "https://ec.europa.eu/eurostat/web/international-trade-in-goods/database",
    "eex_eu_ets": "https://www.eex.com/en/markets/environmental-markets/eu-ets-spot-futures-options",
}

REQUIRED_COLUMNS = [
    "date",
    "importer",
    "supplier",
    "product_description",
    "cn_code",
    "origin_country",
    "destination_country",
    "quantity_tonnes",
    "customs_value_eur",
]
