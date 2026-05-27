"""Quality checks for the Data Mart (gold layer)
Run this after loading `gold` to validate referential integrity, uniqueness, and key nulls.
Usage: python 04_quality_checks.py
Exits with code 0 if all critical checks pass, 1 otherwise.
"""

import os
import sys
import json
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
import pandas as pd
from sqlalchemy.engine import URL

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_PORT = int(os.getenv("SUPABASE_PORT", 5432))
SUPABASE_DB = os.getenv("SUPABASE_DB")
SUPABASE_USER = os.getenv("SUPABASE_USER")
SUPABASE_PASSWORD = os.getenv("SUPABASE_PASSWORD")


def make_engine(host, port, db, user, password, sslmode=None):
    return create_engine(URL.create("postgresql+psycopg2", username=user, password=password, host=host, port=port, database=db, query={"sslmode": sslmode} if sslmode else None))

if SUPABASE_URL and SUPABASE_DB and SUPABASE_USER and SUPABASE_PASSWORD:
    engine = make_engine(SUPABASE_URL, SUPABASE_PORT, SUPABASE_DB, SUPABASE_USER, SUPABASE_PASSWORD, sslmode="require")
else:
    print("ERROR: SUPABASE connection variables missing in .env")
    sys.exit(1)

THRESHOLD_NULL_PERCENT = 5.0  # warn if >5% nulls in critical business keys

checks = {
    "orphan_counts": {},
    "duplicates": {},
    "null_percent": {},
    "rowcount_reconciliation": {}
}

critical_failure = False

queries_orphans = [
    ("factsales.customerkey", "SELECT COUNT(*) FROM gold.factsales f WHERE f.customerkey IS NOT NULL AND f.customerkey NOT IN (SELECT customerkey FROM gold.dimcustomer WHERE date_to IS NULL)"),
    ("factsales.employeekey", "SELECT COUNT(*) FROM gold.factsales f WHERE f.employeekey IS NOT NULL AND f.employeekey NOT IN (SELECT employeekey FROM gold.dimemployee WHERE date_to IS NULL)"),
    ("factsales.productkey", "SELECT COUNT(*) FROM gold.factsales f WHERE f.productkey IS NOT NULL AND f.productkey NOT IN (SELECT productkey FROM gold.dimproduct WHERE date_to IS NULL)"),
    ("factsales.locationkey", "SELECT COUNT(*) FROM gold.factsales f WHERE f.locationkey IS NOT NULL AND f.locationkey NOT IN (SELECT locationkey FROM gold.dimlocation WHERE date_to IS NULL)"),
    ("factinvoices.customerkey", "SELECT COUNT(*) FROM gold.factinvoices f WHERE f.customerkey IS NOT NULL AND f.customerkey NOT IN (SELECT customerkey FROM gold.dimcustomer WHERE date_to IS NULL)"),
    ("factinvoices.employeekey", "SELECT COUNT(*) FROM gold.factinvoices f WHERE f.employeekey IS NOT NULL AND f.employeekey NOT IN (SELECT employeekey FROM gold.dimemployee WHERE date_to IS NULL)"),
    ("factinvoices.locationkey", "SELECT COUNT(*) FROM gold.factinvoices f WHERE f.locationkey IS NOT NULL AND f.locationkey NOT IN (SELECT locationkey FROM gold.dimlocation WHERE date_to IS NULL)"),
    ("factinvoices.deliverymethodkey", "SELECT COUNT(*) FROM gold.factinvoices f WHERE f.deliverymethodkey IS NOT NULL AND f.deliverymethodkey NOT IN (SELECT deliverymethodkey FROM gold.dimdeliverymethod WHERE date_to IS NULL)"),
]

# Detection of unmapped FKs (NULL in fact when business key was present in silver) — silent data loss check
queries_unmapped = [
    ("factsales.customerkey_unmapped", "SELECT COUNT(*) FROM silver.stg_fact_sales s LEFT JOIN gold.dimcustomer d ON s.customerid = d.customerid AND d.date_to IS NULL WHERE s.customerid IS NOT NULL AND d.customerkey IS NULL"),
    ("factsales.productkey_unmapped", "SELECT COUNT(*) FROM silver.stg_fact_sales s LEFT JOIN gold.dimproduct d ON s.stockitemid = d.stockitemid AND d.date_to IS NULL WHERE s.stockitemid IS NOT NULL AND d.productkey IS NULL"),
    ("factinvoices.deliverymethodkey_unmapped", "SELECT COUNT(*) FROM silver.stg_fact_invoices s LEFT JOIN gold.dimdeliverymethod d ON s.deliverymethodid = d.deliverymethodid AND d.date_to IS NULL WHERE s.deliverymethodid IS NOT NULL AND d.deliverymethodkey IS NULL"),
]

with engine.connect() as conn:
    print("Running orphan key checks...")
    for name, sql in queries_orphans:
        try:
            cnt = conn.execute(text(sql)).scalar()
            checks["orphan_counts"][name] = int(cnt)
            print(f"{name}: {cnt}")
            if cnt > 0:
                critical_failure = True
        except Exception as e:
            checks["orphan_counts"][name] = f"ERROR: {e}"
            print(f"{name}: ERROR {e}")

    print("\nRunning unmapped FK checks (silent data loss)...")
    checks["unmapped_fks"] = {}
    for name, sql in queries_unmapped:
        try:
            cnt = conn.execute(text(sql)).scalar()
            checks["unmapped_fks"][name] = int(cnt)
            print(f"{name}: {cnt}")
            if cnt > 0:
                critical_failure = True
        except Exception as e:
            checks["unmapped_fks"][name] = f"ERROR: {e}"
            print(f"{name}: ERROR {e}")

    print("\nChecking duplicate current dimension rows (date_to IS NULL)...")
    dup_queries = [
        ("dimemployee", "personid"),
        ("dimcustomer", "customerid"),
        ("dimlocation", "locationid"),
        ("dimproduct", "stockitemid"),
        ("dimdeliverymethod", "deliverymethodid"),
        ("dimpaymentmethod", "paymentmethodid"),
    ]
    for table, key in dup_queries:
        try:
            sql = f"SELECT {key}, COUNT(*) AS c FROM gold.{table} WHERE date_to IS NULL GROUP BY {key} HAVING COUNT(*)>1"
            df = pd.read_sql(text(sql), conn)
            checks["duplicates"][table] = int(len(df))
            print(f"{table}: {len(df)} duplicate current keys")
            if len(df) > 0:
                critical_failure = True
        except Exception as e:
            checks["duplicates"][table] = f"ERROR: {e}"
            print(f"{table}: ERROR {e}")

    print("\nChecking null percentages for critical columns...")
    null_checks = [
        ("gold.dimemployee", "personid"),
        ("gold.dimcustomer", "customerid"),
        ("gold.dimproduct", "stockitemid"),
        ("gold.dimlocation", "locationid"),
        ("gold.dimdeliverymethod", "deliverymethodid"),
        ("gold.dimpaymentmethod", "paymentmethodid"),
    ]
    for tbl, col in null_checks:
        try:
            total = conn.execute(text(f"SELECT COUNT(*) FROM {tbl}")).scalar()
            nulls = conn.execute(text(f"SELECT COUNT(*) FROM {tbl} WHERE {col} IS NULL")).scalar()
            pct = 100.0 * nulls / total if total else 0.0
            checks["null_percent"][f"{tbl}.{col}"] = pct
            print(f"{tbl}.{col}: {nulls}/{total} nulls ({pct:.2f}%)")
            if pct > THRESHOLD_NULL_PERCENT:
                critical_failure = True
        except Exception as e:
            checks["null_percent"][f"{tbl}.{col}"] = f"ERROR: {e}"
            print(f"{tbl}.{col}: ERROR {e}")

    print("\nRow count reconciliation (silver vs gold current rows)...")
    recon_pairs = [
        ("silver.stg_employees", "gold.dimemployee", "personid"),
        ("silver.stg_customers", "gold.dimcustomer", "customerid"),
        ("silver.stg_products", "gold.dimproduct", "stockitemid"),
        ("silver.stg_locations", "gold.dimlocation", "locationid"),
        ("silver.stg_deliverymethods", "gold.dimdeliverymethod", "deliverymethodid"),
        ("silver.stg_paymentmethods", "gold.dimpaymentmethod", "paymentmethodid"),
    ]
    for stg, gold, key in recon_pairs:
        try:
            stg_cnt = conn.execute(text(f"SELECT COUNT(*) FROM {stg}")).scalar()
            gold_cnt = conn.execute(text(f"SELECT COUNT(*) FROM {gold} WHERE date_to IS NULL")).scalar()
            checks["rowcount_reconciliation"][f"{stg} -> {gold}"] = {"stg": int(stg_cnt), "gold_current": int(gold_cnt)}
            print(f"{stg} -> {gold}: stg={stg_cnt}, gold_current={gold_cnt}")
            if stg_cnt and abs(stg_cnt - gold_cnt) / stg_cnt > 0.01:
                print(f"WARNING: rowcount mismatch >1% for {stg} -> {gold}")
        except Exception as e:
            checks["rowcount_reconciliation"][f"{stg} -> {gold}"] = f"ERROR: {e}"
            print(f"{stg} -> {gold}: ERROR {e}")

report_path = os.path.join(os.path.dirname(__file__), "quality_report.json")
with open(report_path, "w", encoding="utf-8") as f:
    json.dump(checks, f, indent=2, default=str)

print(f"\nQuality checks finished. Report saved to {report_path}")
if critical_failure:
    print("CRITICAL CHECKS FAILED: investigate orphan keys / duplicates / null business keys / unmapped FKs.")
    sys.exit(1)
else:
    print("All critical checks passed.")
    sys.exit(0)
