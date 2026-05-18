from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import requests

from .config import DEFAULT_CBAM_PRICE_EUR_TCO2, OFFICIAL_LINKS


@dataclass
class PriceSignal:
    official_cbam_price: float
    live_eua_proxy_price: float | None
    fx_eurusd: float | None
    source_note: str
    updated_at: str


def _get_json(url: str, timeout: int = 8) -> Any | None:
    try:
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
        return response.json()
    except Exception:
        return None


def get_live_price_signal(manual_cbam_price: float = DEFAULT_CBAM_PRICE_EUR_TCO2) -> PriceSignal:
    """Fetch optional live signals.

    Set one of these environment variables in Streamlit Cloud secrets or local .env:
    - EUA_PRICE_API_URL: endpoint returning {'price': 75.36} or {'eua_price': 75.36}
    - EURUSD_API_URL: endpoint returning {'rates': {'USD': 1.08}} or {'eurusd': 1.08}

    The app remains useful without APIs because official CBAM prices can be entered
    manually and import data is processed locally.
    """
    eua_price = None
    fx = None
    notes = []

    eua_url = os.getenv("EUA_PRICE_API_URL", "").strip()
    if eua_url:
        data = _get_json(eua_url)
        if isinstance(data, dict):
            eua_price = data.get("price") or data.get("eua_price") or data.get("last")
            try:
                eua_price = float(eua_price)
                notes.append("EUA proxy loaded from EUA_PRICE_API_URL")
            except Exception:
                eua_price = None
                notes.append("EUA_PRICE_API_URL returned no numeric price")

    fx_url = os.getenv("EURUSD_API_URL", "").strip()
    if fx_url:
        data = _get_json(fx_url)
        try:
            if isinstance(data, dict) and "rates" in data:
                fx = float(data["rates"]["USD"])
            elif isinstance(data, dict):
                fx = float(data.get("eurusd") or data.get("EURUSD"))
            notes.append("EUR/USD loaded from EURUSD_API_URL")
        except Exception:
            fx = None
            notes.append("EURUSD_API_URL returned no numeric FX rate")

    if not notes:
        notes.append("offline/manual mode: no live API URLs configured")

    return PriceSignal(
        official_cbam_price=float(manual_cbam_price),
        live_eua_proxy_price=eua_price,
        fx_eurusd=fx,
        source_note="; ".join(notes),
        updated_at=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    )


def official_sources_table() -> list[dict[str, str]]:
    return [
        {"source": "European Commission CBAM home", "url": OFFICIAL_LINKS["cbam_home"], "use": "legal scope, guidance, regulatory updates"},
        {"source": "European Commission CBAM certificate prices", "url": OFFICIAL_LINKS["cbam_prices"], "use": "official certificate prices"},
        {"source": "European Commission CBAM guidance files", "url": OFFICIAL_LINKS["cbam_guidance"], "use": "default values, templates, sector methods"},
        {"source": "Eurostat international trade in goods / Comext", "url": OFFICIAL_LINKS["eurostat_itg"], "use": "monthly public trade data by product/partner/reporter"},
        {"source": "EEX EU ETS markets", "url": OFFICIAL_LINKS["eex_eu_ets"], "use": "EUA market signal / futures / auction context"},
    ]
