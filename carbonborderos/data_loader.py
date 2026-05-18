from __future__ import annotations

from pathlib import Path
from typing import BinaryIO

import pandas as pd

from .config import DATA_DIR, REQUIRED_COLUMNS


def load_csv(name: str) -> pd.DataFrame:
    return pd.read_csv(DATA_DIR / name)


def load_sample_imports() -> pd.DataFrame:
    return normalize_imports(load_csv("sample_imports.csv"))


def load_defaults() -> pd.DataFrame:
    return load_csv("default_factors.csv")


def load_cn_prefixes() -> pd.DataFrame:
    df = load_csv("cbam_cn_prefixes.csv")
    df["prefix"] = df["prefix"].astype(str)
    return df


def load_company_dictionary() -> pd.DataFrame:
    return load_csv("company_dictionary.csv")


def load_materials() -> pd.DataFrame:
    return load_csv("material_substitution.csv")


def read_uploaded_file(uploaded_file: BinaryIO | None) -> pd.DataFrame | None:
    if uploaded_file is None:
        return None
    name = getattr(uploaded_file, "name", "")
    if name.lower().endswith((".xlsx", ".xls")):
        df = pd.read_excel(uploaded_file)
    else:
        df = pd.read_csv(uploaded_file)
    return normalize_imports(df)


def normalize_imports(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(c).strip().lower().replace(" ", "_") for c in df.columns]
    alias_map = {
        "description": "product_description",
        "product": "product_description",
        "hs_code": "cn_code",
        "cn8": "cn_code",
        "mass_tonnes": "quantity_tonnes",
        "quantity": "quantity_tonnes",
        "value_eur": "customs_value_eur",
        "supplier_emissions": "supplier_emissions_tco2e_per_t",
    }
    df = df.rename(columns={c: alias_map.get(c, c) for c in df.columns})

    for col in REQUIRED_COLUMNS:
        if col not in df.columns:
            if col == "date":
                df[col] = pd.Timestamp.today().strftime("%Y-%m-%d")
            elif col in ["quantity_tonnes", "customs_value_eur"]:
                df[col] = 0.0
            else:
                df[col] = "unknown"

    df["cn_code"] = df["cn_code"].astype(str).str.replace(r"\D", "", regex=True).str[:8]
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["quantity_tonnes"] = pd.to_numeric(df["quantity_tonnes"], errors="coerce").fillna(0.0)
    df["customs_value_eur"] = pd.to_numeric(df["customs_value_eur"], errors="coerce").fillna(0.0)

    optional_numeric = [
        "supplier_emissions_tco2e_per_t",
        "foreign_carbon_price_eur_per_t",
        "recycled_content_percent",
        "document_quality_score",
    ]
    for col in optional_numeric:
        if col not in df.columns:
            df[col] = pd.NA
        df[col] = pd.to_numeric(df[col], errors="coerce")

    if "verified" not in df.columns:
        df["verified"] = False
    df["verified"] = df["verified"].astype(str).str.lower().isin(["true", "1", "yes", "y", "verified"])

    if "production_route" not in df.columns:
        df["production_route"] = "unknown"

    return df


def validate_import_schema(df: pd.DataFrame) -> list[str]:
    missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    warnings: list[str] = []
    if missing:
        warnings.append(f"Missing columns: {', '.join(missing)}")
    if df["cn_code"].astype(str).str.len().lt(4).any():
        warnings.append("Some CN/HS codes are shorter than 4 digits; scope detection confidence will be lower.")
    if (df["quantity_tonnes"] <= 0).any():
        warnings.append("Some rows have zero or negative quantity_tonnes.")
    return warnings
