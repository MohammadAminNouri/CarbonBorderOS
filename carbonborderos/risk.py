from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

HIGH_RISK_ORIGINS = {
    "China", "India", "Russia", "Kazakhstan", "Egypt", "Saudi Arabia", "South Africa"
}
LOW_CARBON_ORIGINS = {"Norway", "Sweden", "Iceland", "Switzerland", "France"}


def add_supplier_risk(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    doc_quality = pd.to_numeric(df.get("document_quality_score", 60), errors="coerce").fillna(60)
    missing_emissions = df["supplier_emissions_tco2e_per_t"].isna().astype(int) if "supplier_emissions_tco2e_per_t" in df else 1
    unverified = (~df.get("verified", False)).astype(int) if "verified" in df else 1
    high_origin = df["origin_country"].isin(HIGH_RISK_ORIGINS).astype(int)
    low_origin = df["origin_country"].isin(LOW_CARBON_ORIGINS).astype(int)
    emissions_ratio = (df["emissions_tco2e_per_t_used"].fillna(0) / df["high_risk_tco2e_per_t"].replace(0, np.nan)).fillna(0)

    risk = (
        22 * missing_emissions
        + 18 * unverified
        + 18 * high_origin
        - 10 * low_origin
        + 20 * emissions_ratio.clip(0, 1.5)
        + (100 - doc_quality).clip(0, 100) * 0.18
        + df["cbam_relevant"].astype(int) * 8
    )
    df["supplier_risk_score"] = risk.clip(0, 100).round(1)
    df["supplier_risk_band"] = pd.cut(
        df["supplier_risk_score"],
        bins=[-1, 35, 65, 100],
        labels=["low", "medium", "high"],
    ).astype(str)
    df["risk_drivers"] = df.apply(_risk_drivers, axis=1)
    return df


def _risk_drivers(row: pd.Series) -> str:
    drivers = []
    if pd.isna(row.get("supplier_emissions_tco2e_per_t")):
        drivers.append("missing supplier emissions")
    if not bool(row.get("verified", False)):
        drivers.append("unverified data")
    if row.get("origin_country") in HIGH_RISK_ORIGINS:
        drivers.append("high-risk origin signal")
    if float(row.get("document_quality_score", 60) or 60) < 60:
        drivers.append("weak document quality")
    if float(row.get("emissions_tco2e_per_t_used", 0) or 0) >= float(row.get("high_risk_tco2e_per_t", 999) or 999):
        drivers.append("high emissions intensity")
    return ", ".join(drivers) if drivers else "no major risk driver"


def supplier_summary(df: pd.DataFrame) -> pd.DataFrame:
    grp = df.groupby(["supplier", "origin_country"], dropna=False).agg(
        cbam_cost_eur=("estimated_cbam_cost_eur", "sum"),
        emissions_tco2e=("gross_embedded_emissions_tco2e", "sum"),
        tonnes=("quantity_tonnes", "sum"),
        avg_risk=("supplier_risk_score", "mean"),
        high_risk_lines=("supplier_risk_band", lambda s: (s == "high").sum()),
        cbam_lines=("cbam_relevant", "sum"),
    ).reset_index()
    grp["avg_risk"] = grp["avg_risk"].round(1)
    grp = grp.sort_values(["avg_risk", "cbam_cost_eur"], ascending=[False, False])
    return grp


def anomaly_flags(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    features = df[["quantity_tonnes", "customs_value_eur", "emissions_tco2e_per_t_used", "cost_per_product_tonne_eur"]].fillna(0)
    if len(features) < 6:
        df["anomaly_flag"] = False
        df["anomaly_note"] = "not enough rows for IsolationForest"
        return df
    model = IsolationForest(contamination=min(0.25, max(0.05, 2 / len(features))), random_state=42)
    pred = model.fit_predict(features)
    df["anomaly_flag"] = pred == -1
    df["anomaly_note"] = np.where(df["anomaly_flag"], "unusual quantity/value/emissions/cost pattern", "normal pattern")
    return df
