from carbonborderos.cost import estimate_cbam_cost
from carbonborderos.data_loader import load_sample_imports
from carbonborderos.pipeline import process_imports


def test_cost_formula():
    assert estimate_cbam_cost(100, 2, 75, 5) == 14000


def test_pipeline_runs():
    df = load_sample_imports()
    out = process_imports(df, cbam_price=75.36)
    assert "estimated_cbam_cost_eur" in out.columns
    assert out["estimated_cbam_cost_eur"].sum() > 0
    assert "supplier_risk_score" in out.columns
