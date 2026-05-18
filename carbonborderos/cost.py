from __future__ import annotations

import numpy as np
import pandas as pd

from .config import DEFAULT_CBAM_PRICE_EUR_TCO2


def estimate_cbam_cost(
    quantity_tonnes: float,
    embedded_emissions_tco2_per_tonne: float,
    cbam_price_eur_per_tco2: float = DEFAULT_CBAM_PRICE_EUR_TCO2,
    foreign_carbon_price_paid: float = 0.0,
    phase_in_factor: float = 1.0,
) -> float:
    gross_emissions = max(float(quantity_tonnes), 0) * max(float(embedded_emissions_tco2_per_tonne), 0)
    effective_price = max(float(cbam_price_eur_per_tco2) - max(float(foreign_carbon_price_paid or 0), 0), 0)
    return gross_emissions * effective_price * max(float(phase_in_factor), 0)


def add_cost_columns(df: pd.DataFrame, cbam_price: float, phase_in_factor: float = 1.0) -> pd.DataFrame:
    df = df.copy()
    if "foreign_carbon_price_eur_per_t" not in df.columns:
        df["foreign_carbon_price_eur_per_t"] = 0.0
    df["foreign_carbon_price_eur_per_t"] = pd.to_numeric(df["foreign_carbon_price_eur_per_t"], errors="coerce").fillna(0.0)
    df["gross_embedded_emissions_tco2e"] = df["quantity_tonnes"] * df["emissions_tco2e_per_t_used"].fillna(0)
    df["effective_cbam_price_eur_tco2e"] = (cbam_price - df["foreign_carbon_price_eur_per_t"]).clip(lower=0)
    df["estimated_cbam_cost_eur"] = df.apply(
        lambda r: estimate_cbam_cost(
            r["quantity_tonnes"],
            r["emissions_tco2e_per_t_used"],
            cbam_price,
            r.get("foreign_carbon_price_eur_per_t", 0.0),
            phase_in_factor,
        ), axis=1)
    df["cost_per_product_tonne_eur"] = np.where(df["quantity_tonnes"] > 0, df["estimated_cbam_cost_eur"] / df["quantity_tonnes"], 0)
    df["cbam_cost_as_percent_of_customs_value"] = np.where(
        df["customs_value_eur"] > 0, 100 * df["estimated_cbam_cost_eur"] / df["customs_value_eur"], 0)
    return df


def scenario_table(df: pd.DataFrame, base_price: float) -> pd.DataFrame:
    scenarios = {
        "bearish carbon price (-20%)": base_price * 0.8,
        "current official/manual price": base_price,
        "bullish carbon price (+20%)": base_price * 1.2,
        "stress test (+50%)": base_price * 1.5,
    }
    rows = []
    for name, price in scenarios.items():
        tmp = add_cost_columns(df, price)
        rows.append({
            "scenario": name,
            "price_eur_tco2e": price,
            "total_cost_eur": tmp["estimated_cbam_cost_eur"].sum(),
            "total_emissions_tco2e": tmp["gross_embedded_emissions_tco2e"].sum(),
            "weighted_cost_per_imported_tonne": tmp["estimated_cbam_cost_eur"].sum() / max(tmp["quantity_tonnes"].sum(), 1),
        })
    return pd.DataFrame(rows)


def default_penalty_savings(df: pd.DataFrame, cbam_price: float) -> pd.DataFrame:
    """Estimate savings from replacing default values with verified supplier data."""
    out = df.copy()
    out["default_cost_eur"] = out.apply(
        lambda r: estimate_cbam_cost(r["quantity_tonnes"], r.get("default_emissions_tco2e_per_t", 0), cbam_price, r.get("foreign_carbon_price_eur_per_t", 0)), axis=1)
    out["actual_or_estimated_cost_eur"] = out["estimated_cbam_cost_eur"]
    out["potential_saving_vs_default_eur"] = (out["default_cost_eur"] - out["actual_or_estimated_cost_eur"]).clip(lower=0)
    return out
