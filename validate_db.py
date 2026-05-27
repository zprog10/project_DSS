"""
validate_db.py — Validação completa do DWH no Supabase.

Executa:
  1. Contagens por camada (bronze / silver / gold).
  2. Reconciliação silver -> gold (current rows).
  3. Checks de FK órfã (fact -> dim_current).
  4. Checks de FK não-mapeada (silver -> dim_current) — TODAS as 9, incluindo as
     6 que faltavam em 04_quality_checks.py (employee/location em ambas as facts,
     accountsemployee, etc.).
  5. Duplicatas em linhas correntes (date_to IS NULL) das dimensões SCD2.
  6. Null % em business keys.
  7. Cobertura de DimDate vs. datekey das facts.
  8. _load_control: últimas cargas e linhas com status='ERROR'.

Sai com código 0 se tudo passar, 1 caso contrário.
"""

import os
import sys
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL
import pandas as pd

load_dotenv(override=True)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_PORT = int(os.getenv("SUPABASE_PORT", 5432))
SUPABASE_DB = os.getenv("SUPABASE_DB")
SUPABASE_USER = os.getenv("SUPABASE_USER")
SUPABASE_PASSWORD = os.getenv("SUPABASE_PASSWORD")

if not all([SUPABASE_URL, SUPABASE_DB, SUPABASE_USER, SUPABASE_PASSWORD]):
    print("ERRO: variáveis SUPABASE_* faltando no .env")
    sys.exit(1)

engine = create_engine(URL.create(
    "postgresql+psycopg2",
    username=SUPABASE_USER, password=SUPABASE_PASSWORD,
    host=SUPABASE_URL, port=SUPABASE_PORT, database=SUPABASE_DB,
    query={"sslmode": "require"},
))

NULL_THRESHOLD_PCT = 5.0
failures = []
warnings = []

def hr(title):
    print("\n" + "=" * 78)
    print(title)
    print("=" * 78)

def scalar(conn, sql, params=None):
    return conn.execute(text(sql), params or {}).scalar()

# -----------------------------------------------------------------------------
# Tabelas esperadas em cada camada
# -----------------------------------------------------------------------------
EXPECTED = {
    "bronze": ["people", "customercategories", "customers", "countries",
               "stateprovinces", "cities", "stockitems", "customertransactions",
               "invoices", "invoicelines", "deliverymethods", "paymentmethods",
               "transactiontypes", "_load_control"],
    "silver": ["stg_employees", "stg_customers", "stg_products", "stg_locations",
               "stg_deliverymethods", "stg_paymentmethods", "stg_transactiontypes",
               "stg_fact_sales", "stg_fact_invoices"],
    "gold":   ["dimemployee", "dimcustomer", "dimlocation", "dimproduct", "dimdate",
               "dimdeliverymethod", "dimpaymentmethod", "factsales", "factinvoices"],
}

with engine.connect() as conn:

    # ---- 1. Existência e contagens por camada ----------------------------
    hr("1. Contagens por camada")
    for schema, tables in EXPECTED.items():
        print(f"\n[{schema}]")
        for t in tables:
            try:
                n = scalar(conn, f"SELECT COUNT(*) FROM {schema}.{t}")
                flag = "" if n > 0 or t == "_load_control" else "  ⚠ vazia"
                print(f"  {schema}.{t:<25} {n:>10}{flag}")
                if n == 0 and t != "_load_control":
                    warnings.append(f"{schema}.{t} vazia")
            except Exception as e:
                print(f"  {schema}.{t:<25}    MISSING ({e.__class__.__name__})")
                failures.append(f"{schema}.{t} inexistente")

    # ---- 2. Reconciliação silver -> gold ---------------------------------
    hr("2. Reconciliação silver -> gold (current)")
    recon = [
        ("silver.stg_employees",       "gold.dimemployee"),
        ("silver.stg_customers",       "gold.dimcustomer"),
        ("silver.stg_products",        "gold.dimproduct"),
        ("silver.stg_locations",       "gold.dimlocation"),
        ("silver.stg_deliverymethods", "gold.dimdeliverymethod"),
        ("silver.stg_paymentmethods",  "gold.dimpaymentmethod"),
    ]
    for stg, gold in recon:
        s = scalar(conn, f"SELECT COUNT(*) FROM {stg}")
        g = scalar(conn, f"SELECT COUNT(*) FROM {gold} WHERE date_to IS NULL")
        status = "OK" if s == g else "MISMATCH"
        print(f"  {stg:<32} {s:>8}  ->  {gold:<28} {g:>8}  [{status}]")
        if s != g:
            failures.append(f"reconciliação {stg} != {gold}")

    # ---- 3. FK órfãs (fact -> dim_current) -------------------------------
    hr("3. FK órfãs (fact aponta para chave inexistente no dim current)")
    orphans = [
        ("factsales.customerkey",           "gold.factsales",    "customerkey",        "gold.dimcustomer",       "customerkey"),
        ("factsales.employeekey",           "gold.factsales",    "employeekey",        "gold.dimemployee",       "employeekey"),
        ("factsales.productkey",            "gold.factsales",    "productkey",         "gold.dimproduct",        "productkey"),
        ("factsales.locationkey",           "gold.factsales",    "locationkey",        "gold.dimlocation",       "locationkey"),
        ("factsales.datekey",               "gold.factsales",    "datekey",            "gold.dimdate",           "datekey"),
        ("factinvoices.customerkey",        "gold.factinvoices", "customerkey",        "gold.dimcustomer",       "customerkey"),
        ("factinvoices.employeekey",        "gold.factinvoices", "employeekey",        "gold.dimemployee",       "employeekey"),
        ("factinvoices.accountsemployeekey","gold.factinvoices", "accountsemployeekey","gold.dimemployee",       "employeekey"),
        ("factinvoices.locationkey",        "gold.factinvoices", "locationkey",        "gold.dimlocation",       "locationkey"),
        ("factinvoices.deliverymethodkey",  "gold.factinvoices", "deliverymethodkey",  "gold.dimdeliverymethod", "deliverymethodkey"),
        ("factinvoices.datekey",            "gold.factinvoices", "datekey",            "gold.dimdate",           "datekey"),
    ]
    for name, fact, fk, dim, sk in orphans:
        if dim == "gold.dimdate":
            sql = f"SELECT COUNT(*) FROM {fact} f WHERE f.{fk} IS NOT NULL AND f.{fk} NOT IN (SELECT {sk} FROM {dim})"
        else:
            sql = f"SELECT COUNT(*) FROM {fact} f WHERE f.{fk} IS NOT NULL AND f.{fk} NOT IN (SELECT {sk} FROM {dim} WHERE date_to IS NULL)"
        n = scalar(conn, sql)
        print(f"  {name:<38} {n:>6}")
        if n > 0:
            failures.append(f"FK órfã: {name} = {n}")

    # ---- 4. FK não-mapeada (silver business key -> dim_current) ----------
    hr("4. FK não-mapeada (silent data loss)")
    unmapped = [
        ("factsales.customerkey",         "silver.stg_fact_sales",    "customerid",          "gold.dimcustomer",       "customerid",       "customerkey"),
        ("factsales.productkey",          "silver.stg_fact_sales",    "stockitemid",         "gold.dimproduct",        "stockitemid",      "productkey"),
        ("factsales.employeekey",         "silver.stg_fact_sales",    "salespersonpersonid", "gold.dimemployee",       "personid",         "employeekey"),
        ("factsales.locationkey",         "silver.stg_fact_sales",    "deliverycityid",      "gold.dimlocation",       "locationid",       "locationkey"),
        ("factinvoices.customerkey",      "silver.stg_fact_invoices", "customerid",          "gold.dimcustomer",       "customerid",       "customerkey"),
        ("factinvoices.employeekey",      "silver.stg_fact_invoices", "salespersonpersonid", "gold.dimemployee",       "personid",         "employeekey"),
        ("factinvoices.accountsemployee", "silver.stg_fact_invoices", "accountspersonid",    "gold.dimemployee",       "personid",         "employeekey"),
        ("factinvoices.locationkey",      "silver.stg_fact_invoices", "deliverycityid",      "gold.dimlocation",       "locationid",       "locationkey"),
        ("factinvoices.deliverymethodkey","silver.stg_fact_invoices", "deliverymethodid",    "gold.dimdeliverymethod", "deliverymethodid", "deliverymethodkey"),
    ]
    for name, stg, biz, dim, dim_biz, dim_sk in unmapped:
        sql = (f"SELECT COUNT(*) FROM {stg} s LEFT JOIN {dim} d "
               f"ON s.{biz} = d.{dim_biz} AND d.date_to IS NULL "
               f"WHERE s.{biz} IS NOT NULL AND d.{dim_sk} IS NULL")
        n = scalar(conn, sql)
        print(f"  {name:<32} {n:>6}")
        if n > 0:
            failures.append(f"FK não-mapeada: {name} = {n}")

    # ---- 5. Duplicatas em linhas correntes -------------------------------
    hr("5. Duplicatas em current rows (date_to IS NULL)")
    dups = [
        ("gold.dimemployee",       "personid"),
        ("gold.dimcustomer",       "customerid"),
        ("gold.dimlocation",       "locationid"),
        ("gold.dimproduct",        "stockitemid"),
        ("gold.dimdeliverymethod", "deliverymethodid"),
        ("gold.dimpaymentmethod",  "paymentmethodid"),
    ]
    for tbl, key in dups:
        sql = (f"SELECT COUNT(*) FROM (SELECT {key} FROM {tbl} "
               f"WHERE date_to IS NULL GROUP BY {key} HAVING COUNT(*) > 1) x")
        n = scalar(conn, sql)
        print(f"  {tbl + '.' + key:<48} {n:>4} chaves duplicadas")
        if n > 0:
            failures.append(f"duplicata em {tbl}.{key}")

    # ---- 6. Null % em business keys --------------------------------------
    hr("6. Null % em business keys")
    nulls = [
        ("gold.dimemployee",       "personid"),
        ("gold.dimcustomer",       "customerid"),
        ("gold.dimlocation",       "locationid"),
        ("gold.dimproduct",        "stockitemid"),
        ("gold.dimdeliverymethod", "deliverymethodid"),
        ("gold.dimpaymentmethod",  "paymentmethodid"),
    ]
    for tbl, col in nulls:
        total = scalar(conn, f"SELECT COUNT(*) FROM {tbl}")
        n = scalar(conn, f"SELECT COUNT(*) FROM {tbl} WHERE {col} IS NULL")
        pct = (100.0 * n / total) if total else 0.0
        flag = ""
        if pct > NULL_THRESHOLD_PCT:
            flag = "  ✗ acima do limite"
            failures.append(f"null% alto em {tbl}.{col} ({pct:.2f}%)")
        print(f"  {tbl + '.' + col:<48} {n}/{total} ({pct:.2f}%){flag}")

    # ---- 7. Cobertura de DimDate -----------------------------------------
    hr("7. Cobertura de DimDate vs. datekey das facts")
    dd_min = scalar(conn, "SELECT MIN(date) FROM gold.dimdate")
    dd_max = scalar(conn, "SELECT MAX(date) FROM gold.dimdate")
    dd_count = scalar(conn, "SELECT COUNT(*) FROM gold.dimdate")
    print(f"  dimdate: {dd_count} dias, de {dd_min} até {dd_max}")
    for fact in ["gold.factsales", "gold.factinvoices"]:
        missing = scalar(conn,
            f"SELECT COUNT(*) FROM {fact} f WHERE f.datekey IS NOT NULL "
            f"AND f.datekey NOT IN (SELECT datekey FROM gold.dimdate)")
        print(f"  {fact}.datekey fora de dimdate: {missing}")
        if missing > 0:
            failures.append(f"{fact}.datekey fora de dimdate = {missing}")

    # ---- 8. _load_control: últimas cargas / erros ------------------------
    hr("8. bronze._load_control — status das cargas")
    df_lc = pd.read_sql(text(
        "SELECT table_name, strategy, status, COUNT(*) AS n, MAX(loaded_at) AS last_load "
        "FROM bronze._load_control GROUP BY table_name, strategy, status "
        "ORDER BY table_name, last_load DESC"), conn)
    print(df_lc.to_string(index=False))
    err = scalar(conn, "SELECT COUNT(*) FROM bronze._load_control WHERE status = 'ERROR'")
    if err > 0:
        failures.append(f"_load_control tem {err} linha(s) com status='ERROR'")
        print(f"\n  ✗ {err} cargas com ERROR — investigar.")

# -----------------------------------------------------------------------------
# Resumo final
# -----------------------------------------------------------------------------
hr("RESUMO")
if not failures and not warnings:
    print("✓ Tudo OK — DWH consistente.")
    sys.exit(0)
if warnings:
    print(f"\n⚠ {len(warnings)} aviso(s):")
    for w in warnings:
        print(f"  - {w}")
if failures:
    print(f"\n✗ {len(failures)} falha(s) crítica(s):")
    for f in failures:
        print(f"  - {f}")
    sys.exit(1)
print("\n✓ Sem falhas críticas (apenas avisos).")
sys.exit(0)
