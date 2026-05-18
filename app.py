from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from carbonborderos.config import DEFAULT_CBAM_PRICE_EUR_TCO2, OFFICIAL_LINKS
from carbonborderos.connectors import get_live_price_signal, official_sources_table
from carbonborderos.cost import default_penalty_savings, scenario_table
from carbonborderos.data_loader import load_company_dictionary, load_sample_imports, read_uploaded_file, validate_import_schema
from carbonborderos.dictionary import build_company_dictionary, supplier_network_edges
from carbonborderos.material_advisor import material_options
from carbonborderos.pipeline import process_imports
from carbonborderos.reporting import to_excel_bytes
from carbonborderos.risk import supplier_summary

st.set_page_config(
    page_title="CarbonBorderOS | Live CBAM Intelligence",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded",
)

CUSTOM_CSS = """
<style>
.block-container {padding-top: 1.1rem; padding-bottom: 3rem;}
.metric-card {
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 18px;
    padding: 18px;
    background: linear-gradient(135deg, rgba(17,24,39,0.98), rgba(15,23,42,0.96));
    box-shadow: 0 12px 32px rgba(0,0,0,.22);
}
.small-muted {color: #9CA3AF; font-size: 0.88rem;}
.big-title {font-size: 2.45rem; font-weight: 800; letter-spacing: -0.04em;}
.green {color: #22C55E;}
.warning {color: #F59E0B;}
.danger {color: #EF4444;}
hr {border-color: rgba(255,255,255,0.08)}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


@st.cache_data(show_spinner=False)
def load_demo_data() -> pd.DataFrame:
    return load_sample_imports()


@st.cache_data(show_spinner=False)
def run_pipeline_cached(df: pd.DataFrame, price: float, phase: float, threshold: float) -> pd.DataFrame:
    return process_imports(df, cbam_price=price, phase_in_factor=phase, threshold_tonnes=threshold)


def euro(x: float) -> str:
    return f"€{x:,.0f}"


def tonnes(x: float) -> str:
    return f"{x:,.1f} t"


def header():
    st.markdown('<div class="big-title">CarbonBorderOS <span class="green">Live CBAM Intelligence</span></div>', unsafe_allow_html=True)
    st.caption("Not another CBAM calculator: scope detection + cost exposure + supplier risk + company dictionary + scenario intelligence.")


def sidebar_controls():
    with st.sidebar:
        st.title("CarbonBorderOS")
        st.caption("Open-source CBAM intelligence demo")
        page = st.radio(
            "Workspace",
            [
                "Situation Room",
                "Upload & Analyze",
                "Supplier Risk AI",
                "Company Dictionary",
                "Scenario Lab",
                "Material Substitution",
                "Data Sources & Deploy",
            ],
        )
        st.divider()
        st.subheader("CBAM assumptions")
        price = st.number_input(
            "CBAM certificate price €/tCO₂e",
            min_value=0.0,
            max_value=500.0,
            value=float(DEFAULT_CBAM_PRICE_EUR_TCO2),
            step=1.0,
            help="Use the official EC price for compliance; use live EUA proxy only for scenario and risk monitoring.",
        )
        phase = st.slider("Phase-in / stress factor", 0.0, 1.5, 1.0, 0.05)
        threshold = st.number_input("Importer covered-goods threshold, tonnes", 0.0, 1000.0, 50.0, 5.0)
        st.divider()
        uploaded = st.file_uploader("Upload import ledger CSV/XLSX", type=["csv", "xlsx", "xls"])
        if uploaded:
            df = read_uploaded_file(uploaded)
            data_note = f"Using uploaded file: {uploaded.name}"
        else:
            df = load_demo_data()
            data_note = "Using built-in synthetic demo import ledger"
        return page, price, phase, threshold, df, data_note


def kpi_row(df: pd.DataFrame):
    total_cost = df["estimated_cbam_cost_eur"].sum()
    total_emissions = df["gross_embedded_emissions_tco2e"].sum()
    cbam_tonnes = df.loc[df["cbam_relevant"], "quantity_tonnes"].sum()
    high_risk = (df["supplier_risk_band"] == "high").sum()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Estimated CBAM exposure", euro(total_cost))
    c2.metric("Embedded emissions", f"{total_emissions:,.0f} tCO₂e")
    c3.metric("CBAM-covered mass", tonnes(cbam_tonnes))
    c4.metric("High-risk lines", f"{high_risk:,}")


def situation_room(df: pd.DataFrame, price: float):
    header()
    signal = get_live_price_signal(price)
    st.info(
        f"Price mode: official/manual CBAM price = **€{signal.official_cbam_price:,.2f}/tCO₂e**. "
        f"Live signal: {signal.source_note}. Updated {signal.updated_at}."
    )
    kpi_row(df)

    c1, c2 = st.columns([1.2, 1])
    with c1:
        sector = df.groupby("cbam_sector", as_index=False).agg(cost=("estimated_cbam_cost_eur", "sum"), tonnes=("quantity_tonnes", "sum"))
        fig = px.bar(sector.sort_values("cost", ascending=False), x="cbam_sector", y="cost", text_auto=".2s",
                     title="CBAM exposure by sector")
        fig.update_layout(yaxis_title="Estimated cost (€)", xaxis_title="Sector")
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        country = df.groupby("origin_country", as_index=False).agg(cost=("estimated_cbam_cost_eur", "sum"), emissions=("gross_embedded_emissions_tco2e", "sum"))
        fig = px.treemap(country, path=["origin_country"], values="cost", color="emissions", title="Origin-country exposure map")
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Live action feed")
    actions = []
    if df["estimated_cbam_cost_eur"].sum() > 0:
        top_supplier = df.groupby("supplier")["estimated_cbam_cost_eur"].sum().idxmax()
        actions.append(f"Largest cost exposure is linked to **{top_supplier}**. Prioritize verified emissions documents there.")
    missing = df[df["supplier_emissions_tco2e_per_t"].isna() & df["cbam_relevant"]]
    if len(missing):
        actions.append(f"**{len(missing)} CBAM-covered lines** use default/demo factors because supplier emissions are missing.")
    high = df[df["supplier_risk_band"] == "high"]
    if len(high):
        actions.append(f"**{len(high)} high-risk import lines** need document audit or supplier challenge.")
    for item in actions or ["No urgent action under current demo assumptions."]:
        st.markdown(f"- {item}")


def upload_analyze(df: pd.DataFrame, data_note: str):
    header()
    st.success(data_note)
    warnings = validate_import_schema(df)
    for w in warnings:
        st.warning(w)
    kpi_row(df)

    st.subheader("Import line intelligence")
    show_cols = [
        "date", "importer", "supplier", "origin_country", "product_description", "cn_code",
        "cbam_sector", "cbam_relevant", "scope_confidence", "threshold_note", "emissions_source",
        "emissions_tco2e_per_t_used", "estimated_cbam_cost_eur", "supplier_risk_score", "risk_drivers",
    ]
    st.dataframe(df[show_cols], use_container_width=True, height=420)

    c1, c2 = st.columns(2)
    with c1:
        fig = px.bar(
            df.groupby("supplier", as_index=False)["estimated_cbam_cost_eur"].sum().sort_values("estimated_cbam_cost_eur", ascending=False),
            x="supplier", y="estimated_cbam_cost_eur", title="Cost by supplier", text_auto=".2s")
        fig.update_layout(xaxis_tickangle=-30, yaxis_title="€")
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        fig = px.scatter(
            df, x="quantity_tonnes", y="estimated_cbam_cost_eur", color="supplier_risk_band",
            size="gross_embedded_emissions_tco2e", hover_name="product_description",
            title="Cost vs mass: bubbles expose high-risk lines")
        st.plotly_chart(fig, use_container_width=True)


def supplier_risk_page(df: pd.DataFrame):
    header()
    st.subheader("Supplier Risk AI")
    st.caption("Hybrid rules + anomaly detection. This is not legal verification; it is a prioritization layer for procurement/compliance teams.")
    summary = supplier_summary(df)
    st.dataframe(summary, use_container_width=True)

    c1, c2 = st.columns([1, 1])
    with c1:
        fig = px.bar(summary, x="supplier", y="avg_risk", color="origin_country", title="Average supplier risk score")
        fig.update_layout(xaxis_tickangle=-30)
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        fig = px.scatter(df, x="document_quality_score", y="supplier_risk_score", color="emissions_source",
                         size="estimated_cbam_cost_eur", hover_name="supplier", title="Document quality vs risk")
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Anomaly watchlist")
    watch = df[df["anomaly_flag"] | (df["supplier_risk_band"] == "high")]
    st.dataframe(watch[["supplier", "product_description", "origin_country", "quantity_tonnes", "estimated_cbam_cost_eur", "supplier_risk_score", "risk_drivers", "anomaly_note"]], use_container_width=True)


def company_dictionary_page(df: pd.DataFrame):
    header()
    st.subheader("EU CBAM Importer & Supplier Dictionary")
    st.caption("For public data, this should be exposure estimation. For user-uploaded data, it becomes exact internal intelligence. Do not claim actual CBAM payments unless sourced.")
    built = build_company_dictionary(df)
    demo = load_company_dictionary()

    tab1, tab2, tab3 = st.tabs(["Generated from current data", "Seed dictionary template", "Importer–supplier edges"])
    with tab1:
        st.dataframe(built, use_container_width=True)
    with tab2:
        st.dataframe(demo, use_container_width=True)
    with tab3:
        edges = supplier_network_edges(df)
        st.dataframe(edges, use_container_width=True)
        if not edges.empty:
            fig = px.sunburst(edges, path=["importer", "supplier", "cbam_sector"], values="cbam_cost_eur", color="avg_risk", title="Importer → supplier → sector exposure graph")
            st.plotly_chart(fig, use_container_width=True)


def scenario_lab(df: pd.DataFrame, price: float):
    header()
    st.subheader("Scenario Lab")
    sc = scenario_table(df, base_price=price)
    st.dataframe(sc, use_container_width=True)
    fig = px.line(sc, x="scenario", y="total_cost_eur", markers=True, title="Carbon-price sensitivity")
    fig.update_layout(yaxis_title="Estimated CBAM cost (€)")
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Default-value penalty detector")
    penalty = default_penalty_savings(df, cbam_price=price)
    cols = ["supplier", "product_description", "emissions_source", "default_cost_eur", "actual_or_estimated_cost_eur", "potential_saving_vs_default_eur"]
    st.dataframe(penalty[cols].sort_values("potential_saving_vs_default_eur", ascending=False), use_container_width=True)

    st.subheader("Export compliance intelligence pack")
    excel_bytes = to_excel_bytes({
        "processed_imports": df,
        "supplier_summary": supplier_summary(df),
        "company_dictionary": build_company_dictionary(df),
        "scenarios": sc,
        "default_penalty": penalty[cols],
    })
    st.download_button("Download Excel intelligence report", excel_bytes, file_name="carbonborderos_cbam_report.xlsx")


def material_page(price: float):
    header()
    st.subheader("Material Substitution Advisor")
    st.caption("This is the materials-engineering angle: carbon-border cost is treated as a design-selection penalty, not just a tax line.")
    c1, c2 = st.columns(2)
    with c1:
        strength_min = st.slider("Minimum relative strength index", 0, 100, 40)
    with c2:
        max_density = st.slider("Maximum density kg/m³", 1000, 9000, 9000)
    options = material_options(price, strength_min=strength_min, max_density=max_density)
    st.dataframe(options, use_container_width=True)

    fig = px.scatter(
        options,
        x="typical_emissions_tco2e_per_t",
        y="relative_strength_index",
        size="availability_score",
        color="material",
        hover_data=["landed_material_plus_carbon_eur_per_t", "density_kg_m3", "notes"],
        title="Material performance vs carbon exposure",
    )
    fig.update_layout(xaxis_title="Typical emissions tCO₂e/t", yaxis_title="Relative strength index")
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("### What makes this different")
    st.markdown(
        "Most CBAM tools stop after cost calculation. This module asks the procurement/design question: "
        "*can we change route, recycled content, supplier, or material family to reduce carbon-border exposure without breaking engineering constraints?*"
    )


def data_sources_deploy(df: pd.DataFrame):
    header()
    st.subheader("Data sources, limitations, and deployment")
    st.markdown("""
    **Use this repo in three modes:**

    1. **Demo mode** — synthetic CSV files, no API key.
    2. **Company mode** — upload internal import ledgers, supplier templates, invoices, and declarations.
    3. **Market/live mode** — connect official CBAM prices, EUA/EU ETS market data, FX, commodity prices, Eurostat/Comext, or licensed shipment data.

    Public EU trade data can support product/country/partner analysis, but usually not exact company-level CBAM payments. Treat company-level exposure as **estimated** unless it comes from the user's private data or a licensed shipment database.
    """)
    sources = pd.DataFrame(official_sources_table())
    st.dataframe(sources, use_container_width=True)

    st.code("""# local run
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
streamlit run app.py

# GitHub upload
git init
git add .
git commit -m "Initial CarbonBorderOS Streamlit app"
git branch -M main
git remote add origin https://github.com/<your-user>/CarbonBorderOS.git
git push -u origin main

# Streamlit Cloud
# New app → pick repo → main file path: app.py
""", language="bash")

    st.markdown("### Expected import-ledger columns")
    st.dataframe(pd.DataFrame({"column": df.columns, "example_dtype": [str(t) for t in df.dtypes]}), use_container_width=True)


def main():
    page, price, phase, threshold, raw_df, data_note = sidebar_controls()
    processed = run_pipeline_cached(raw_df, price, phase, threshold)

    if page == "Situation Room":
        situation_room(processed, price)
    elif page == "Upload & Analyze":
        upload_analyze(processed, data_note)
    elif page == "Supplier Risk AI":
        supplier_risk_page(processed)
    elif page == "Company Dictionary":
        company_dictionary_page(processed)
    elif page == "Scenario Lab":
        scenario_lab(processed, price)
    elif page == "Material Substitution":
        material_page(price)
    elif page == "Data Sources & Deploy":
        data_sources_deploy(processed)

    st.divider()
    st.caption(
        "CarbonBorderOS is an estimation and intelligence prototype, not legal advice. "
        "Replace demo mappings and emission factors with official/legal datasets before compliance use."
    )


if __name__ == "__main__":
    main()
