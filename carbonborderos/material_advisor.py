from __future__ import annotations

import pandas as pd

from .data_loader import load_materials


def material_options(cbam_price: float, strength_min: float = 0, max_density: float | None = None) -> pd.DataFrame:
    df = load_materials().copy()
    df["carbon_cost_eur_per_t"] = df["typical_emissions_tco2e_per_t"] * cbam_price
    df["material_cost_eur_per_t"] = df["typical_cost_eur_per_kg"] * 1000
    df["landed_material_plus_carbon_eur_per_t"] = df["material_cost_eur_per_t"] + df["carbon_cost_eur_per_t"]
    df["carbon_penalty_percent"] = 100 * df["carbon_cost_eur_per_t"] / df["material_cost_eur_per_t"].replace(0, pd.NA)
    df["substitution_score"] = (
        0.30 * df["relative_strength_index"]
        + 0.25 * df["availability_score"]
        + 0.25 * df["recyclability_score"]
        - 0.0008 * df["landed_material_plus_carbon_eur_per_t"]
        - 0.0020 * df["density_kg_m3"]
    ).round(1)
    if strength_min:
        df = df[df["relative_strength_index"] >= strength_min]
    if max_density is not None:
        df = df[df["density_kg_m3"] <= max_density]
    return df.sort_values("substitution_score", ascending=False)
