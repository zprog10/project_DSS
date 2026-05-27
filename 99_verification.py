"""
99_verification.py
Run basic verification checks against the Supabase DWH to confirm loads and integrity.
Usage: python 99_verification.py
"""
import os
import subprocess
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL
import pandas as pd

load_dotenv()

SUPABASE_URL  = os.getenv("SUPABASE_URL")
SUPABASE_PORT = int(os.getenv("SUPABASE_PORT", 5432))
SUPABASE_DB   = os.getenv("SUPABASE_DB")
SUPABASE_USER = os.getenv("SUPABASE_USER")
SUPABASE_PASSWORD = os.getenv("SUPABASE_PASSWORD")

if not all([SUPABASE_URL, SUPABASE_DB, SUPABASE_USER, SUPABASE_PASSWORD]):
    raise SystemExit("Missing Supabase env vars. Set SUPABASE_URL, SUPABASE_DB, SUPABASE_USER, SUPABASE_PASSWORD in .env")

def make_engine(host, port, db, user, password, sslmode=None):
    return create_engine(URL.create("postgresql+psycopg2", username=user, password=password, host=host, port=port, database=db, query={"sslmode": sslmode} if sslmode else None))

engine_dwh = make_engine(SUPABASE_URL, SUPABASE_PORT, SUPABASE_DB, SUPABASE_USER, SUPABASE_PASSWORD, sslmode="require")

# Configure the tables to check — adapt if your project differs
tables_map = {
    "bronze": [
        "people","customercategories","customers","countries","stateprovinces","cities",
        "stockitems","customertransactions","invoices","invoicelines",
        "deliverymethods","paymentmethods","transactiontypes"
    ],
    "silver": [
        "stg_employees","stg_customers","stg_products","stg_locations",
        "stg_deliverymethods","stg_paymentmethods","stg_transactiontypes",
        "stg_fact_sales","stg_fact_invoices"
    ],
    "gold": [
        "dimemployee","dimcustomer","dimlocation","dimproduct","dimdate",
        "dimdeliverymethod","dimpaymentmethod",
        "factsales","factinvoices"
    ]
}

def q(sql):
    with engine_dwh.connect() as conn:
        return pd.read_sql(text(sql), conn)

def main():
    print("=== Recent load control (bronze._load_control) ===")
    try:
        df_lc = q("SELECT table_name, strategy, snapshot_id, loaded_at, rows_total, rows_inserted, rows_updated, rows_deleted, status FROM bronze._load_control ORDER BY loaded_at DESC LIMIT 50")
        print(df_lc.to_string(index=False))
    except Exception as e:
        print("Could not read bronze._load_control:", e)

    for schema, tbls in tables_map.items():
        print(f"\n=== Counts in {schema} ===")
        for t in tbls:
            try:
                cnt = q(f"SELECT COUNT(*) AS cnt FROM {schema}.{t}").iloc[0]['cnt']
            except Exception as e:
                cnt = f'ERROR: {e}'
            print(f"{schema}.{t}: {cnt}")

    print("\n=== Sample FK orphan checks ===")
    try:
        res = q("SELECT COUNT(*) AS orphan_sales_customers FROM silver.stg_fact_sales s WHERE s.customerid IS NOT NULL AND NOT EXISTS (SELECT 1 FROM silver.stg_customers c WHERE c.customerid = s.customerid)")
        print(res.to_string(index=False))
    except Exception as e:
        print("FK orphan check error:", e)

    print("\n=== Structural checks: constraints and indexes (gold/silver) ===")
    try:
        cons = q("SELECT table_schema, table_name, constraint_name, constraint_type FROM information_schema.table_constraints WHERE table_schema IN ('silver','gold','bronze') ORDER BY table_schema, table_name")
        print(cons.head(50).to_string(index=False))
    except Exception as e:
        print("Constraints query error:", e)

    try:
        idx = q("SELECT schemaname, tablename, indexname FROM pg_indexes WHERE schemaname IN ('silver','gold','bronze') ORDER BY schemaname, tablename")
        print(idx.head(50).to_string(index=False))
    except Exception as e:
        print("Indexes query error:", e)

    print('\n=== Run quality checks script (04_quality_checks.py) and capture output ===')
    qc_path = Path(__file__).parent / '04_quality_checks.py'
    if qc_path.exists():
        try:
            proc = subprocess.run([os.sys.executable, str(qc_path)], capture_output=True, text=True)
            print('Return code:', proc.returncode)
            print('\n--- stdout ---')
            print(proc.stdout or '<no output>')
            print('\n--- stderr ---')
            print(proc.stderr or '<no stderr>')
        except Exception as e:
            print('Error running quality checks:', e)
    else:
        print('Quality checks script not found:', qc_path)

if __name__ == '__main__':
    main()
