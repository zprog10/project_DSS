# Wide World Importers (WWI) — Medallion ETL Pipeline (DSS P01)

**Project Report:** A complete project report has been created as `REPORT.md`. Open [REPORT.md](REPORT.md) for the full P01-style writeup (objectives, profiling Table 1, dimensional model, ETL runbook, verification outputs and appendices).

Implements a Medallion Architecture data mart (Bronze → Silver → Gold) for the Wide World Importers (WWI) sample database, on a Supabase Postgres DWH.

The notebooks are split so that **source extraction** (VPN ON to reach `postgres2.ipca.pt`) and **DWH loading** (VPN OFF to reach Supabase) happen in different cells — you toggle VPN between them.

---

## Architecture

```
public.* (WWI source — VPN ON)
        │  save → CSV + schema JSON in tmp_snapshots/, tmp_increments/
        ▼
bronze.* (full-fidelity copy — VPN OFF)
        │  read active snapshot, clean, conform
        ▼
silver.stg_* (staging, project-only columns — VPN OFF)
        │  SCD Type 2 for dims, surrogate-key lookups for facts
        ▼
gold.* (star schema — VPN OFF)
```

---

## Files

| File | Layer | What it does |
|---|---|---|
| `00_setup.ipynb` | meta | Connections, schema creation, `bronze._load_control` DDL, gold DDL. |
| `01_bronze.ipynb` | bronze | Two-phase extract (save CSVs and schema JSONs with VPN ON; apply with VPN OFF). |
| `02_silver.ipynb` | silver | DROP+CREATE staging tables, transform from `bronze.*` (DWH only). |
| `03_gold.ipynb` | gold | DimDate snapshot, SCD2 dims, fact loads with surrogate-key lookups. |
| `04_quality_checks.py` | gold | Orphan-FK / unmapped-FK / duplicate / null checks; writes `quality_report.json`. |
| `99_verification.py` | gold | Per-table counts, FK orphan check, constraints/indexes listing, runs `04_quality_checks.py`. |
| `scripts/dw_script.sql` | reference | Consolidated DDL + indexes for **Appendix B** of the report. |
| `scripts/data_profiling.py` | reference | Generates **Table 1** of the report (run with VPN ON). |
| `scripts/data_description_maps.md` | reference | **Appendix A** — Data Description Maps for DimCustomer and DimProduct. |
| `scripts/create_indexes_and_constraints.sql` | gold | Indexes + partial-unique constraints for SCD2 current rows. |
| `scripts/_patch_notebooks.py` | dev | One-shot generator that rebuilt the notebooks. Re-run if you want to reset. |

---

## Prerequisites

```bash
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt
```

`.env` (in this folder):

```
SRC_HOST=postgres2.ipca.pt
SRC_PORT=5432
SRC_DB=wwi
SRC_USER=...
SRC_PASSWORD=...

SUPABASE_URL=...pooler.supabase.com
SUPABASE_PORT=6543
SUPABASE_DB=postgres
SUPABASE_USER=...
SUPABASE_PASSWORD=...
```

---

## Run order with VPN toggling

| Step | Notebook / cell | VPN | Notes |
|---|---|---|---|
| 0 | Open `00_setup.ipynb` | OFF | Skip cell `## 4. Source engine` and `## 5b` and `## 10` if you don't have VPN. |
| 0a | Run cells `## 1` → `## 9` of `00_setup` | OFF | Creates schemas, `bronze._load_control`, gold DDL, and validates. |
| 0b | Run cell `## 4` and `## 5b` and `## 10` | ON | Optional source connectivity check + table inventory. |
| 1 | `01_bronze.ipynb` cell `## 2` (engine_src) | ON | Source engine. |
| 2 | `01_bronze.ipynb` cell `## 7` (save snapshots) | ON | Writes CSVs and `tmp_snapshots/_schema/*.json`. |
| 3 | `01_bronze.ipynb` cell `## 9` (save incremental) | ON | Reads watermark from DWH if available, then dumps invoices/invoicelines since the watermark. |
| 4 | Switch VPN OFF |  | |
| 5 | `01_bronze.ipynb` cells `## 3, ## 5, ## 6, ## 8, ## 10` | OFF | Engine_dwh, _load_control, helpers, apply snapshots, apply incrementals. |
| 6 | `02_silver.ipynb` (all cells) | OFF | Builds 9 silver staging tables. |
| 7 | `03_gold.ipynb` (all cells) | OFF | Builds DimDate, SCD2 dims, facts; runs indexes + quality checks. |
| 8 | `python 99_verification.py` | OFF | Cross-layer verification. |

> **Tip.** You can run cell `## 1. Imports and env` of any notebook freely; it only loads `.env`. Engines are created lazily in dedicated cells.

### Helper scripts

| Script | VPN | Purpose |
|---|---|---|
| `scripts/data_profiling.py` | ON | Produces `scripts/data_profiling.json` and `scripts/data_profiling.md` (Table 1 of the report). |
| `scripts/dw_script.sql` | OFF | Reference DDL — paste into Appendix B. Already executed by `00_setup.ipynb`. |

---

## What lives in each layer

### Bronze (faithful copy of source)

13 tables. Snapshots: `people, customercategories, customers, countries, stateprovinces, cities, stockitems, customertransactions, deliverymethods, paymentmethods, transactiontypes`. Incremental: `invoices, invoicelines`. Plus `bronze._load_control` for ELT metadata.

Each row carries metadata: `_loaded_at`, `_source` and (for snapshots) `_snapshot_id`, `_change_op` (INSERT/UPDATE/DELETE).

### Silver (project-scoped staging)

9 tables. `stg_employees, stg_customers, stg_locations, stg_products, stg_deliverymethods, stg_paymentmethods, stg_transactiontypes, stg_fact_sales, stg_fact_invoices`. DROP+CREATE on every run — idempotent.

### Gold (star schema)

Dimensions (SCD Type 2 except `DimDate`): `DimEmployee, DimCustomer, DimLocation, DimProduct, DimDeliveryMethod, DimPaymentMethod, DimDate`.

Facts: `FactSales` (grain = invoice line), `FactInvoices` (grain = invoice header, with `DeliveryMethodKey`).

---

## What `ERROR` rows in `bronze._load_control` mean

`status = 'ERROR'` is written by the apply cells when an exception escapes the `try/except`. Common causes:

- Schema mismatch (CSV has columns the bronze table doesn't). Mitigated since `01_bronze` now derives DDL from the saved schema JSON.
- Connection issues (engine created with VPN ON, used with VPN OFF or vice versa).
- Type coercion errors (rare — Postgres is permissive).

Diagnose with:

```sql
SELECT * FROM bronze._load_control ORDER BY loaded_at DESC LIMIT 50;
```

---

## Quick SQLs

```sql
-- Recent loads
SELECT table_name, strategy, snapshot_id, loaded_at, rows_total, rows_inserted, rows_updated, rows_deleted, status
FROM bronze._load_control ORDER BY loaded_at DESC LIMIT 50;

-- Counts in silver/gold
SELECT 'silver.stg_customers' AS t, COUNT(*) FROM silver.stg_customers
UNION ALL SELECT 'gold.dimcustomer', COUNT(*) FROM gold.dimcustomer WHERE date_to IS NULL;

-- Orphan FK
SELECT COUNT(*) FROM gold.factsales f
WHERE f.customerkey IS NOT NULL
  AND f.customerkey NOT IN (SELECT customerkey FROM gold.dimcustomer WHERE date_to IS NULL);
```

---

## Quality reports

`04_quality_checks.py` writes `quality_report.json` covering:
- Orphan FKs (`factsales.*`, `factinvoices.*`).
- **Unmapped FKs** (silver business key without a current dim key) — silent data-loss detection.
- Duplicate current dim rows.
- Null percentages on business keys (vs. `THRESHOLD_NULL_PERCENT=5.0`).
- Row count reconciliation `silver → gold (current)`.

Exit code 0 if everything passed.

---

## Troubleshooting

- **"engine_src is not defined"** — you skipped the `## 2. engine_src` cell or VPN is off.
- **"server closed the connection unexpectedly"** — engine was created in a different VPN state. Re-run the engine cell.
- **`bronze.<table>` empty after apply** — verify the CSV exists in `tmp_snapshots/` and the schema JSON exists in `tmp_snapshots/_schema/`. Both are required since bronze DDL is now derived from the JSON.
- **Quality report flags `unmapped_fks`** — there are silver rows whose business key has no matching current dim row. Re-run `02_silver` and `03_gold` in order, or check if the dim source table is populated.
