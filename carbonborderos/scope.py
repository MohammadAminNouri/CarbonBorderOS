from __future__ import annotations

import re
from dataclasses import dataclass

import pandas as pd

from .config import DEFAULT_ANNUAL_THRESHOLD_TONNES
from .data_loader import load_cn_prefixes, load_defaults

KEYWORD_SECTORS = {
    "aluminium": ["aluminium", "aluminum", "alumina", "bauxite", "6063", "6082", "7075"],
    "iron_steel": ["steel", "iron", "stainless", "galvanised", "galvanized", "coil", "bar", "bolt", "fastener", "sheet"],
    "cement": ["cement", "clinker", "portland", "lime"],
    "fertilisers": ["fertiliser", "fertilizer", "ammonia", "ammonium", "nitrate", "urea"],
    "hydrogen": ["hydrogen", "h2"],
    "electricity": ["electricity", "electric power", "power import"],
}


@dataclass(frozen=True)
class ScopeResult:
    sector: str
    cbam_relevant: bool
    confidence: float
    reason: str


def _clean_code(cn_code: str) -> str:
    return re.sub(r"\D", "", str(cn_code))[:8]


def classify_by_cn(cn_code: str, prefixes: pd.DataFrame | None = None) -> ScopeResult:
    prefixes = prefixes if prefixes is not None else load_cn_prefixes()
    code = _clean_code(cn_code)
    if not code:
        return ScopeResult("not_cbam", False, 0.0, "missing CN/HS code")

    best = None
    for _, row in prefixes.sort_values("prefix", key=lambda s: s.str.len(), ascending=False).iterrows():
        prefix = str(row["prefix"])
        if code.startswith(prefix):
            best = row
            break

    if best is None:
        return ScopeResult("not_cbam", False, 0.72, "CN/HS prefix not in demo CBAM prefix map")
    return ScopeResult(
        sector=str(best["sector"]),
        cbam_relevant=True,
        confidence=float(best.get("confidence", 0.75)),
        reason=f"matched CN/HS prefix {best['prefix']} ({best.get('scope_note', 'demo scope map')})",
    )


def classify_by_description(description: str) -> ScopeResult:
    desc = str(description).lower()
    scores: dict[str, int] = {}
    for sector, words in KEYWORD_SECTORS.items():
        scores[sector] = sum(1 for w in words if w in desc)
    sector, score = max(scores.items(), key=lambda kv: kv[1])
    if score == 0:
        return ScopeResult("not_cbam", False, 0.55, "no CBAM material keywords detected")
    confidence = min(0.55 + score * 0.12, 0.92)
    return ScopeResult(sector, True, confidence, f"matched {score} product-description keyword(s)")


def classify_row(row: pd.Series, prefixes: pd.DataFrame | None = None) -> ScopeResult:
    by_cn = classify_by_cn(str(row.get("cn_code", "")), prefixes)
    by_text = classify_by_description(str(row.get("product_description", "")))

    if by_cn.cbam_relevant and by_text.cbam_relevant and by_cn.sector == by_text.sector:
        return ScopeResult(by_cn.sector, True, min(0.99, (by_cn.confidence + by_text.confidence) / 2 + 0.08),
                           f"CN and product text agree: {by_cn.reason}; {by_text.reason}")
    if by_cn.cbam_relevant:
        return by_cn
    if by_text.cbam_relevant:
        return by_text
    return by_cn


def add_scope_columns(df: pd.DataFrame, threshold_tonnes: float = DEFAULT_ANNUAL_THRESHOLD_TONNES) -> pd.DataFrame:
    df = df.copy()
    prefixes = load_cn_prefixes()
    results = [classify_row(row, prefixes) for _, row in df.iterrows()]
    df["cbam_sector"] = [r.sector for r in results]
    df["cbam_relevant"] = [r.cbam_relevant for r in results]
    df["scope_confidence"] = [round(r.confidence, 3) for r in results]
    df["scope_reason"] = [r.reason for r in results]

    annual_mass = df.groupby("importer")["quantity_tonnes"].transform("sum")
    cbam_mass = df.where(df["cbam_relevant"], 0).groupby(df["importer"])["quantity_tonnes"].transform("sum")
    df["importer_total_tonnes_in_file"] = annual_mass
    df["importer_cbam_tonnes_in_file"] = cbam_mass
    df["above_50t_threshold_in_file"] = cbam_mass >= threshold_tonnes
    df["threshold_note"] = df.apply(
        lambda r: "below 50t in this dataset" if r["cbam_relevant"] and not r["above_50t_threshold_in_file"] else
        "above 50t in this dataset" if r["cbam_relevant"] else "outside demo CBAM scope", axis=1)
    return df


def enrich_with_emissions(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    defaults = load_defaults()[["sector", "default_emissions_tco2e_per_t", "low_benchmark_tco2e_per_t", "high_risk_tco2e_per_t"]]
    df = df.merge(defaults, left_on="cbam_sector", right_on="sector", how="left").drop(columns=["sector"], errors="ignore")
    df["emissions_source"] = "default_factor"
    has_supplier = df["supplier_emissions_tco2e_per_t"].notna()
    df.loc[has_supplier, "emissions_source"] = "supplier_reported"
    df.loc[has_supplier & df["verified"], "emissions_source"] = "verified_supplier_reported"
    df["emissions_tco2e_per_t_used"] = df["supplier_emissions_tco2e_per_t"].fillna(df["default_emissions_tco2e_per_t"])
    df.loc[~df["cbam_relevant"], "emissions_tco2e_per_t_used"] = 0.0
    return df
