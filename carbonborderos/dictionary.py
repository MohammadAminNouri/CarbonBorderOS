from __future__ import annotations

import pandas as pd


def build_company_dictionary(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    rows = []
    for importer, g in df.groupby("importer", dropna=False):
        cbam = g[g["cbam_relevant"]]
        sectors = "; ".join(sorted(cbam["cbam_sector"].dropna().unique())) or "not_cbam"
        products = "; ".join(g["product_description"].astype(str).drop_duplicates().head(5))
        cn_codes = "; ".join(g["cn_code"].astype(str).drop_duplicates().head(8))
        origins = "; ".join(g["origin_country"].astype(str).drop_duplicates().head(5))
        suppliers = "; ".join(g["supplier"].astype(str).drop_duplicates().head(5))
        rows.append({
            "company_name": importer,
            "role": "EU importer",
            "destination_countries": "; ".join(g["destination_country"].astype(str).drop_duplicates().head(4)),
            "products": products,
            "cn_codes": cn_codes,
            "cbam_sectors": sectors,
            "main_origins": origins,
            "main_suppliers": suppliers,
            "estimated_tonnes_in_file": g["quantity_tonnes"].sum(),
            "estimated_cbam_tonnes_in_file": cbam["quantity_tonnes"].sum(),
            "estimated_cbam_exposure_eur": cbam["estimated_cbam_cost_eur"].sum(),
            "estimated_emissions_tco2e": cbam["gross_embedded_emissions_tco2e"].sum(),
            "avg_supplier_risk": cbam["supplier_risk_score"].mean() if not cbam.empty else 0,
            "source_type": "user_uploaded_or_demo",
            "confidence": "high" if len(g) >= 3 else "medium",
        })
    out = pd.DataFrame(rows)
    numeric = ["estimated_tonnes_in_file", "estimated_cbam_tonnes_in_file", "estimated_cbam_exposure_eur", "estimated_emissions_tco2e", "avg_supplier_risk"]
    for col in numeric:
        out[col] = pd.to_numeric(out[col], errors="coerce").fillna(0).round(2)
    return out.sort_values("estimated_cbam_exposure_eur", ascending=False)


def supplier_network_edges(df: pd.DataFrame) -> pd.DataFrame:
    return df.groupby(["importer", "supplier", "origin_country", "cbam_sector"], dropna=False).agg(
        tonnes=("quantity_tonnes", "sum"),
        cbam_cost_eur=("estimated_cbam_cost_eur", "sum"),
        avg_risk=("supplier_risk_score", "mean"),
    ).reset_index().sort_values("cbam_cost_eur", ascending=False)
