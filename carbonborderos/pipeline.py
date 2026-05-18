from __future__ import annotations

import pandas as pd

from .scope import add_scope_columns, enrich_with_emissions
from .cost import add_cost_columns
from .risk import add_supplier_risk, anomaly_flags


def process_imports(df: pd.DataFrame, cbam_price: float, phase_in_factor: float = 1.0, threshold_tonnes: float = 50.0) -> pd.DataFrame:
    out = add_scope_columns(df, threshold_tonnes=threshold_tonnes)
    out = enrich_with_emissions(out)
    out = add_cost_columns(out, cbam_price=cbam_price, phase_in_factor=phase_in_factor)
    out = add_supplier_risk(out)
    out = anomaly_flags(out)
    return out
