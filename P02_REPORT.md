# Data Processing and Visualization (P02)

**Decision Support Systems, 2025-26**
**Team ###:** *First name (number), First name (number), First name (number)*

---

## 1. Introduction

The goal of P02 is to deliver a **data-processing and visualization layer** on top of the Wide World Importers (WWI) data mart built in P01. P01 produced a Medallion architecture (Bronze → Silver → Gold) on Supabase Postgres and validated a star schema with 7 dimensions and 2 facts. P02 turns that data mart into actionable decision support by:

- exposing **headline KPIs** (revenue, profit, DSO, outstanding balance, etc.) for executive use;
- letting users **drill down** into sales performance, customers, operations and finance through a multi-page interactive dashboard;
- documenting the **measures, hierarchies and chart choices** that make the dimensional model useful.

**End-user profile.** The dashboard is designed for three personas: (i) sales managers tracking revenue and quota; (ii) account managers / marketing analysts looking at customer concentration and category mix; (iii) finance / accounts-receivable users monitoring outstanding balance and payment delay.

**Tool choice — Streamlit + Plotly + SQLAlchemy.** Streamlit was chosen because it lets the team ship an interactive, reactive Python app with the same SQLAlchemy stack already used in P01, avoiding a context switch to Power BI or Tableau and keeping everything in the team's repo. Plotly Express provides publication-quality interactive charts with minimal code.

The eight business questions answered by the dashboard are:

| # | Question | Page |
|---|---|---|
| 1 | Which products generate the most revenue / profit per month / quarter / year? | Sales Performance |
| 2 | How does revenue grow by customer category over time? | Sales Performance |
| 3 | Which salespersons perform best (volume and value)? | Operations |
| 4 | How does delivery method affect payment delay and invoice value? | Operations |
| 5 | How is revenue distributed across territories and countries? | Sales Performance |
| 6 | Which customers / territories carry the highest outstanding balance? | Finance |
| 7 | What is the distribution and average of payment delay (DSO proxy)? | Finance |
| 8 | What is the customer ranking by revenue and profit, and how concentrated is it? | Customers |

---

## 2. Data acquisition and preparation

### 2.1 Source pipeline (P01 recap)

P02 does **not** re-extract from the operational source. It consumes the gold layer produced by the P01 pipeline:

```
public.* (WWI OLTP, VPN ON)
   │ CSV snapshots / incrementals
   ▼
bronze.*  (faithful copy + load metadata)
   │ DROP+CREATE staging, conform types/strings
   ▼
silver.stg_*  (project-scoped staging)
   │ SCD2 dim load + surrogate-key lookups
   ▼
gold.* (star schema — consumed by this dashboard)
```

### 2.2 Bug fix carried over from P01

During P02 setup a validation script ([validate_db.py](validate_db.py)) revealed that the P01 incremental load had been executed twice, **duplicating** `bronze.invoices` (141.020 vs. 70.510 expected) and propagating a 4× amplification to `gold.factsales` (913.060 vs. 228.265). The fix was packaged as [fix_dup.sql](fix_dup.sql): truncate the duplicated bronze/silver/gold fact tables and the affected `_load_control` rows, then re-run only the `## 9 / ## 10` cells of `01_bronze.ipynb` followed by `02_silver.ipynb` and `03_gold.ipynb`. After replay, every monetary KPI in the dashboard reflects the true source totals.

### 2.3 Dashboard-side preparation

The dashboard layer does not transform data; it only **caches** query results and **parameterises** filters:

- **Engine** ([dashboard/db.py](dashboard/db.py)) — `@st.cache_resource` wrapping `SQLAlchemy.create_engine(URL.create(... sslmode=require ...))`, identical to the pattern used in [validate_db.py:36-43](validate_db.py#L36-L43), [04_quality_checks.py:25](04_quality_checks.py#L25) and [99_verification.py:25](99_verification.py#L25). Credentials come from the same `.env` consumed by the notebooks.
- **Query cache** ([dashboard/queries.py](dashboard/queries.py)) — every query function is wrapped with `@st.cache_data(ttl=600)`. The cache key is the tuple of filter arguments, so changing the year slider or a multiselect transparently invalidates the right entries while leaving unrelated charts cached.
- **Filter widgets** ([dashboard/db.py#sidebar_filters](dashboard/db.py)) — a single helper renders Year-range slider + Customer-category, Sales-territory and (optionally) Delivery-method multiselects. Selections are stored in `st.session_state` so they persist across page navigation. Empty multiselect = no filter (NULL in SQL, OR-ed out).

### 2.4 Validation evidence

`validate_db.py` (P02-built validator) runs 8 checks and after the fix returns:

- **0 orphan FKs** across 11 fact-to-dim references (incl. `datekey`, `accountsemployeekey`).
- **0 unmapped FKs** across 9 silver-to-gold business-key lookups.
- **0 duplicates** in current rows of all 6 SCD2 dimensions.
- **0% NULL** in every business key.
- **100% DimDate coverage** of `datekey` for both facts (1.461 days, 2017-01-01 → 2020-12-31).
- Silver → Gold row reconciliation exact on the 6 dimensions.
- `bronze._load_control`: 13 loads, all `SUCCESS`, no `ERROR`.

---

## 3. Data modelling and processing

### 3.1 Star schema (consumed)

Dimensions (SCD Type 2 except `DimDate`):
`DimEmployee, DimCustomer, DimLocation, DimProduct, DimDate, DimDeliveryMethod, DimPaymentMethod`.

Facts:
- `FactSales` — grain *invoice line* — measures: `Quantity`, `UnitPrice`, `TaxAmount`, `ExtendedPrice`, `LineProfit`.
- `FactInvoices` — grain *invoice header* — measures: `InvoiceAmount`, `PaymentDelay_Days`, `OutstandingBalance`.

Full DDL and indexes are in [scripts/dw_script.sql](scripts/dw_script.sql) and the ER diagram is reproduced in the P01 report ([REPORT.md](REPORT.md)).

### 3.2 Hierarchies used in the dashboard

| Hierarchy | Levels | Used by |
|---|---|---|
| Date | Year → Month → Day | All time-series charts; Year-range slider |
| Location | Sales Territory → Country → State → City | Country bar, territory KPIs |
| Product | Category (customer-side) → Brand → Product | Treemap, Top-N bar |

Note: `Category` lives on `DimCustomer.Category` (i.e. customer segment), not on the product side; the WWI source has no product category column. We use customer category × product brand as the closest analogue.

### 3.3 Measures and calculated columns

All measures are computed **in SQL on the fly** (no calculated columns persisted in gold), to keep the model immutable and let filters compose naturally.

| Measure | SQL | Where shown |
|---|---|---|
| Total revenue | `SUM(factsales.extendedprice)` | Home, Sales, Customers |
| Total profit | `SUM(factsales.lineprofit)` | Home, Sales, Customers |
| Gross margin % | `SUM(lineprofit) / NULLIF(SUM(extendedprice), 0) * 100` | Home (caption) |
| Quantity sold | `SUM(factsales.quantity)` | KPIs, sales detail |
| Invoices count | `COUNT(factinvoices)` | Home, Finance |
| Avg invoice | `AVG(factinvoices.invoiceamount)` | Home |
| Avg payment delay (days) | `AVG(factinvoices.paymentdelay_days)` | Home, Finance |
| Median payment delay | `PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY paymentdelay_days)` | Finance |
| Outstanding balance | `SUM(factinvoices.outstandingbalance)` | Home, Finance |
| Outstanding ratio | `SUM(outstandingbalance) / SUM(invoiceamount) * 100` | Finance |
| Active customers | `COUNT(DISTINCT factsales.customerkey)` | Home |
| Products sold | `COUNT(DISTINCT factsales.productkey)` | Home |
| Pareto cumulative % | `SUM(revenue) OVER (ORDER BY revenue DESC) / SUM(revenue) OVER ()` | Customers |

### 3.4 Joins (current-row semantics for SCD2)

Every fact-to-dim join filters dimensions with `dim.date_to IS NULL` so we always show the latest dimensional attributes. The pattern is encapsulated in two reusable SQL fragments inside [dashboard/queries.py](dashboard/queries.py) (`_BASE_SALES`, `_BASE_INVOICES`), guaranteeing consistent semantics across every chart.

---

## 4. Data visualization

### 4.1 Goals

The dashboard supports two flows: (a) **scan**, via the Home headline KPIs and the revenue trend; (b) **drill**, via four thematic pages that take the user from "what" to "why".

### 4.2 Global controls

- **Year range** slider (auto-populated from `DimDate`).
- **Customer category** multiselect.
- **Sales territory** multiselect.
- **Delivery method** multiselect (Operations and Finance only).

Selections persist across pages via `st.session_state`. Empty multiselect = "all values".

### 4.3 Pages

#### Home — `app.py`
- **Goal:** one-glance executive summary.
- **KPIs (8):** Total revenue, Total profit, Invoices, Avg invoice, Avg payment delay, Outstanding balance, Active customers, Products sold + Gross margin % caption.
- **Chart:** monthly revenue & profit line.
- **Screenshot:** `assets/01_home.png`

#### Sales Performance — `pages/1_Sales_Performance.py`
- **Goal:** answer Q1, Q2, Q5.
- **Charts:** monthly revenue/profit line; stacked area of revenue by customer category over time; Top-N products bar (slider 5–50); Top-25 countries bar coloured by sales territory.
- **Audience:** sales managers and category leads.
- **Screenshot:** `assets/02_sales.png`

#### Customers — `pages/2_Customers.py`
- **Goal:** answer Q8 + category/brand mix.
- **Charts:** Pareto of top-N customers (bar + cumulative % line); customer detail table with monetary formatting; treemap of customer category → product brand revenue.
- **Audience:** account management and marketing.
- **Screenshot:** `assets/03_customers.png`

#### Operations — `pages/3_Operations.py`
- **Goal:** answer Q3, Q4.
- **Charts:** Top-N salesperson bar (filter `IsSalesperson = 1`); delivery summary table (count, avg delay, avg invoice); box plot of payment delay by delivery method.
- **Audience:** sales operations and logistics.
- **Screenshot:** `assets/04_operations.png`

#### Finance — `pages/4_Finance.py`
- **Goal:** answer Q6, Q7.
- **KPIs (4):** Outstanding balance, Total invoiced, Outstanding ratio, Avg/median delay.
- **Charts:** outstanding by sales territory bar; scatter outstanding × invoiced per customer (coloured by category); payment-delay histogram.
- **Audience:** finance / accounts-receivable.
- **Screenshot:** `assets/05_finance.png`

### 4.4 Design notes

- Single Plotly template (`plotly_white`) and one qualitative palette (`Set2`) across the app for visual consistency.
- Monetary values formatted with `K` / `M` abbreviations in KPI cards; full numbers in hover and tables.
- All charts gracefully degrade to a "No data for the selected filters" message when filters return an empty result set (helper `_empty` in [dashboard/charts.py](dashboard/charts.py)).

---

## 5. Conclusion

P02 delivers a small but complete decision-support layer over the P01 data mart: a Streamlit app with 5 pages and ~25 charts answering 8 business questions, plus a validator that proves the underlying data is consistent (0 orphans, 0 duplicates, reconciliation exact).

**Process.** Effort split was roughly: 25 % validating and fixing the data warehouse (catching and correcting the duplicate-load bug), 35 % building the data access and chart library, 25 % laying out pages, 15 % writing the report.

**Tooling pros.** Streamlit + Plotly let us go from data mart to interactive dashboard with no front-end work and full reuse of the Python stack from P01. `@st.cache_resource` for the engine and `@st.cache_data` for queries keep the app snappy without a separate caching layer; Supabase Postgres serves all queries in <500 ms for the 228 K-row fact table.

**Limitations.** (i) Choropleth/geo maps were skipped; the WWI sample lacks geometry. (ii) Authentication isn't required (local-only deployment). (iii) Calculated columns are not persisted in gold — every measure is computed at query time. Acceptable at this scale; would need to be materialised for >10 M rows. (iv) The `.env` file was committed in the original P01 repo (see P01 review); credentials should be rotated and the file untracked. This is out of scope for P02 but worth flagging.

**Next steps.** Materialise pre-aggregated monthly tables for faster drill-downs; add a "Forecast" page with a small time-series model; deploy to Streamlit Community Cloud once `.env` secrets are migrated.

---

## Appendix — How to run

```powershell
# 1. Install
.\.venv\Scripts\python.exe -m pip install -r requirements.txt

# 2. Verify the DWH (should print "✓ Tudo OK")
.\.venv\Scripts\python.exe validate_db.py

# 3. Launch the dashboard
.\.venv\Scripts\streamlit.exe run app.py
```

The app opens at `http://localhost:8501`. The sidebar lists Home + 4 pages.

### Cross-check expected after a fresh load

| Metric | Expected |
|---|---|
| `bronze.invoices` | 70.510 |
| `bronze.invoicelines` | 228.265 |
| `gold.factsales` | 228.265 |
| `gold.factinvoices` | 70.510 |
| Home → Total Invoices (no filter) | 70.510 |
