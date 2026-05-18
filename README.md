# CarbonBorderOS — Live CBAM Intelligence Platform

**Not another CBAM calculator.** CarbonBorderOS is an open-source Streamlit application for **EU CBAM exposure intelligence**: scope detection, carbon-cost simulation, supplier-risk scoring, importer/supplier dictionary building, and materials-substitution advice.

The product idea is simple:

> Turn messy import data into CBAM scope, embedded-emissions exposure, supplier risk, company dictionary profiles, and procurement/design actions.

---

## Why this is different

Most CBAM tools answer only one question: *what is my carbon cost?*

CarbonBorderOS answers the full chain:

1. **Is the import line CBAM-relevant?**
2. **Which sector and CN/HS pattern does it match?**
3. **Is the importer above the mass threshold in the uploaded ledger?**
4. **Are supplier emissions missing, unverified, or suspicious?**
5. **What is the cost under official/manual CBAM price assumptions?**
6. **What is the supplier-risk score and why?**
7. **Which companies/importers look exposed?**
8. **How does exposure change under price scenarios?**
9. **What is the saving from replacing defaults with verified supplier data?**
10. **Can procurement or materials engineering reduce exposure?**

---

## Current app modules

### 1. Situation Room
- Estimated CBAM exposure KPI
- Embedded emissions KPI
- CBAM-covered tonnage KPI
- High-risk import-line count
- Sector and origin-country exposure charts
- Live/manual price-signal panel
- Action feed for supplier and document priorities

### 2. Upload & Analyze
Upload a CSV/XLSX import ledger and get:
- CBAM sector detection
- CN/HS prefix matching
- scope confidence
- threshold note
- emissions source used
- estimated CBAM cost
- supplier risk score
- anomaly flags

### 3. Supplier Risk AI
A hybrid risk layer using:
- missing emissions checks
- verification checks
- origin-risk signals
- document-quality signal
- emissions-intensity comparison
- IsolationForest anomaly detection

### 4. Company Dictionary
Builds an importer profile from the ledger:
- products
- CN codes
- sectors
- main origins
- suppliers
- estimated CBAM exposure
- embedded emissions
- average supplier risk

This is designed as the base for a future **EU CBAM Importer & Supplier Dictionary**. Public data should be treated as exposure estimation; exact company-level CBAM payments require private/company data or licensed shipment datasets.

### 5. Scenario Lab
- Carbon-price sensitivity scenarios
- Default-value penalty detector
- Excel export report

### 6. Material Substitution Advisor
A materials-engineering layer that treats carbon-border cost as a design-selection penalty:
- primary aluminium vs recycled aluminium
- carbon steel vs EAF recycled steel
- stainless steel
- composites and polymers
- strength, density, cost, emissions, availability, recyclability

---

## Quickstart

```bash
# 1. Clone or download the repo
cd CarbonBorderOS

# 2. Create environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run
streamlit run app.py
```

The app runs immediately using `data/sample_imports.csv`.

---

## Deploy on Streamlit Community Cloud

1. Upload this folder to a GitHub repository.
2. Go to Streamlit Community Cloud.
3. Create a new app.
4. Select your repository.
5. Set the main file path to:

```text
app.py
```

6. Deploy.

---

## Upload data format

Minimum columns:

```text
date
importer
supplier
product_description
cn_code
origin_country
destination_country
quantity_tonnes
customs_value_eur
```

Recommended optional columns:

```text
supplier_emissions_tco2e_per_t
verified
foreign_carbon_price_eur_per_t
recycled_content_percent
production_route
document_quality_score
```

---

## Live-data design

The app works without API keys, but it is designed to accept live feeds.

Set environment variables in Streamlit Cloud secrets or local environment:

```bash
EUA_PRICE_API_URL="https://your-api.example.com/eua-price"
EURUSD_API_URL="https://your-api.example.com/eurusd"
```

Expected JSON examples:

```json
{"price": 75.36}
```

or

```json
{"rates": {"USD": 1.08}}
```

Recommended real integrations:
- European Commission CBAM certificate prices
- EEX / ICE / other EUA market data providers
- Eurostat international trade in goods / Comext
- UN Comtrade
- TARIC / Access2Markets
- World Bank carbon pricing data
- licensed shipment data: Panjiva, Datamyne, ImportGenius, etc.

---

## Important limitations

This repository is a prototype and intelligence engine, not legal advice.

- The included CN/HS mappings are simplified demo prefix mappings.
- The included emission factors are illustrative placeholders.
- Replace demo factors with official European Commission default values and sector-specific methods before using for compliance.
- Public trade data usually supports country/product/partner analysis, not exact company-level CBAM payments.
- Company-level exact shipment/payment intelligence requires private user uploads or licensed data.

Use the wording:

> estimated CBAM exposure with source confidence

not:

> exact CBAM paid by company X

unless you have auditable source data.

---

## Suggested GitHub repo description

```text
Open-source Streamlit platform for EU CBAM scope detection, carbon-cost simulation, supplier-risk scoring, importer/supplier dictionary building, and materials-substitution intelligence.
```

---

## Roadmap

### v0.2
- official CBAM CN8 scope table import
- official default-value Excel loader
- supplier document template checker
- richer anomaly explanations

### v0.3
- Eurostat / Comext connector
- country/product trade-flow radar
- company dictionary enrichment from public sources
- news/regulation watch feed

### v0.4
- FastAPI backend
- Postgres database
- auth and multi-company workspaces
- scheduled alerts

### v1.0
- live market data integrations
- procurement recommender
- supplier portal
- verified data workflow
- audit-ready report pack

---

## Official reference links

- European Commission CBAM: https://taxation-customs.ec.europa.eu/carbon-border-adjustment-mechanism_en
- CBAM certificate prices: https://taxation-customs.ec.europa.eu/carbon-border-adjustment-mechanism/price-cbam-certificates_en
- CBAM legislation and guidance: https://taxation-customs.ec.europa.eu/carbon-border-adjustment-mechanism/cbam-legislation-and-guidance_en
- Eurostat international trade in goods / Comext: https://ec.europa.eu/eurostat/web/international-trade-in-goods/database
- EEX EU ETS markets: https://www.eex.com/en/markets/environmental-markets/eu-ets-spot-futures-options

---

## License

MIT

## GitHub Actions CI

This repository includes a GitHub Actions workflow at:

```text
.github/workflows/ci.yml
```

It runs automatically on every push or pull request to `main`/`master`, and it can also be started manually from the **Actions** tab using **Run workflow**.

If the Actions tab looks empty, check that this file exists in the repository root. GitHub Actions only appears when at least one workflow file is present under `.github/workflows/`.

