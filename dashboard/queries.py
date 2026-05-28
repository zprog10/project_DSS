"""All SQL queries for the dashboard.

Conventions:
- Every public function reads only from `gold.*` (current rows for SCD2 dims).
- All filter params arrive as `year_range: tuple[int,int]`, `categories|territories|delivery: list[str] | None`.
  `None` means "no filter" (NULL in SQL → wins the OR clause).
- Decorated with @st.cache_data so reruns hit the cache; tuple/list keys are hashable.
"""

from typing import Optional, Tuple, List

import pandas as pd
import streamlit as st
from sqlalchemy import text

from dashboard.db import get_engine


# Reusable SQL fragments
_BASE_SALES = """
FROM gold.factsales f
JOIN gold.dimdate     d ON f.datekey     = d.datekey
JOIN gold.dimcustomer c ON f.customerkey = c.customerkey AND c.date_to IS NULL
JOIN gold.dimlocation l ON f.locationkey = l.locationkey AND l.date_to IS NULL
JOIN gold.dimproduct  p ON f.productkey  = p.productkey  AND p.date_to IS NULL
JOIN gold.dimemployee e ON f.employeekey = e.employeekey AND e.date_to IS NULL
WHERE d.year BETWEEN :y0 AND :y1
  AND (CAST(:cats  AS text) IS NULL OR c.category       = ANY(string_to_array(:cats,  '|')))
  AND (CAST(:terrs AS text) IS NULL OR l.salesterritory = ANY(string_to_array(:terrs, '|')))
"""

_BASE_INVOICES = """
FROM gold.factinvoices f
JOIN gold.dimdate     d ON f.datekey     = d.datekey
JOIN gold.dimcustomer c ON f.customerkey = c.customerkey AND c.date_to IS NULL
JOIN gold.dimlocation l ON f.locationkey = l.locationkey AND l.date_to IS NULL
LEFT JOIN gold.dimdeliverymethod dm ON f.deliverymethodkey = dm.deliverymethodkey AND dm.date_to IS NULL
LEFT JOIN gold.dimemployee e ON f.employeekey = e.employeekey AND e.date_to IS NULL
WHERE d.year BETWEEN :y0 AND :y1
  AND (CAST(:cats  AS text) IS NULL OR c.category       = ANY(string_to_array(:cats,  '|')))
  AND (CAST(:terrs AS text) IS NULL OR l.salesterritory = ANY(string_to_array(:terrs, '|')))
  AND (CAST(:dms   AS text) IS NULL OR dm.deliverymethodname = ANY(string_to_array(:dms, '|')))
"""


def _params(year_range, categories=None, territories=None, delivery=None):
    return {
        "y0": int(year_range[0]),
        "y1": int(year_range[1]),
        "cats":  "|".join(categories)  if categories  else None,
        "terrs": "|".join(territories) if territories else None,
        "dms":   "|".join(delivery)    if delivery    else None,
    }


def _run(sql: str, params: dict) -> pd.DataFrame:
    with get_engine().connect() as conn:
        return pd.read_sql(text(sql), conn, params=params)


# =============================================================================
# HOME — global KPIs
# =============================================================================

@st.cache_data(ttl=600, show_spinner=False)
def kpis_sales(year_range, categories=None, territories=None) -> pd.Series:
    sql = f"""
    SELECT COALESCE(SUM(f.extendedprice), 0)::numeric AS revenue,
           COALESCE(SUM(f.lineprofit),    0)::numeric AS profit,
           COALESCE(SUM(f.quantity),      0)::bigint  AS qty,
           COUNT(DISTINCT f.customerkey)              AS active_customers,
           COUNT(DISTINCT f.productkey)               AS products_sold,
           COUNT(*)                                   AS lines
    {_BASE_SALES}
    """
    df = _run(sql, _params(year_range, categories, territories))
    return df.iloc[0]


@st.cache_data(ttl=600, show_spinner=False)
def kpis_invoices(year_range, categories=None, territories=None, delivery=None) -> pd.Series:
    sql = f"""
    SELECT COUNT(*)                                    AS invoices,
           COALESCE(AVG(f.invoiceamount),       0)::numeric AS avg_invoice,
           COALESCE(AVG(f.paymentdelay_days),   0)::numeric AS avg_delay,
           COALESCE(SUM(f.outstandingbalance),  0)::numeric AS outstanding
    {_BASE_INVOICES}
    """
    df = _run(sql, _params(year_range, categories, territories, delivery))
    return df.iloc[0]


# =============================================================================
# SALES PERFORMANCE
# =============================================================================

@st.cache_data(ttl=600, show_spinner=False)
def revenue_by_month(year_range, categories=None, territories=None) -> pd.DataFrame:
    sql = f"""
    SELECT d.year, d.month,
           SUM(f.extendedprice) AS revenue,
           SUM(f.lineprofit)    AS profit
    {_BASE_SALES}
    GROUP BY d.year, d.month
    ORDER BY d.year, d.month
    """
    df = _run(sql, _params(year_range, categories, territories))
    if not df.empty:
        df["period"] = pd.to_datetime(dict(year=df.year, month=df.month, day=1))
    return df


@st.cache_data(ttl=600, show_spinner=False)
def revenue_by_category_year(year_range, categories=None, territories=None) -> pd.DataFrame:
    sql = f"""
    SELECT d.year, c.category, SUM(f.extendedprice) AS revenue
    {_BASE_SALES}
    GROUP BY d.year, c.category
    ORDER BY d.year, c.category
    """
    return _run(sql, _params(year_range, categories, territories))


@st.cache_data(ttl=600, show_spinner=False)
def top_products(year_range, categories=None, territories=None, n=20) -> pd.DataFrame:
    sql = f"""
    SELECT p.stockitemname AS product, p.brand,
           SUM(f.extendedprice) AS revenue,
           SUM(f.lineprofit)    AS profit,
           SUM(f.quantity)      AS quantity
    {_BASE_SALES}
    GROUP BY p.stockitemname, p.brand
    ORDER BY revenue DESC
    LIMIT :n
    """
    p = _params(year_range, categories, territories); p["n"] = int(n)
    return _run(sql, p)


@st.cache_data(ttl=600, show_spinner=False)
def revenue_by_country(year_range, categories=None, territories=None) -> pd.DataFrame:
    sql = f"""
    SELECT l.country, l.salesterritory,
           SUM(f.extendedprice) AS revenue,
           SUM(f.lineprofit)    AS profit
    {_BASE_SALES}
    GROUP BY l.country, l.salesterritory
    ORDER BY revenue DESC
    """
    return _run(sql, _params(year_range, categories, territories))


@st.cache_data(ttl=600, show_spinner=False)
def revenue_by_territory(year_range, categories=None, territories=None) -> pd.DataFrame:
    sql = f"""
    SELECT l.salesterritory,
           SUM(f.extendedprice) AS revenue,
           SUM(f.lineprofit)    AS profit
    {_BASE_SALES}
    GROUP BY l.salesterritory
    ORDER BY revenue DESC
    """
    return _run(sql, _params(year_range, categories, territories))


# =============================================================================
# CUSTOMERS
# =============================================================================

@st.cache_data(ttl=600, show_spinner=False)
def customers_ranking(year_range, categories=None, territories=None, n=50) -> pd.DataFrame:
    sql = f"""
    SELECT c.customername AS customer, c.category,
           SUM(f.extendedprice) AS revenue,
           SUM(f.lineprofit)    AS profit,
           COUNT(DISTINCT f.invoiceid) AS invoices
    {_BASE_SALES}
    GROUP BY c.customername, c.category
    ORDER BY revenue DESC
    LIMIT :n
    """
    p = _params(year_range, categories, territories); p["n"] = int(n)
    return _run(sql, p)


@st.cache_data(ttl=600, show_spinner=False)
def category_brand_mix(year_range, categories=None, territories=None) -> pd.DataFrame:
    sql = f"""
    SELECT c.category, COALESCE(p.brand, '(no brand)') AS brand,
           SUM(f.extendedprice) AS revenue
    {_BASE_SALES}
    GROUP BY c.category, p.brand
    HAVING SUM(f.extendedprice) > 0
    ORDER BY revenue DESC
    """
    return _run(sql, _params(year_range, categories, territories))


# =============================================================================
# OPERATIONS
# =============================================================================

@st.cache_data(ttl=600, show_spinner=False)
def salesperson_performance(year_range, categories=None, territories=None) -> pd.DataFrame:
    sql = f"""
    SELECT e.fullname AS salesperson,
           SUM(f.extendedprice) AS revenue,
           SUM(f.lineprofit)    AS profit,
           COUNT(DISTINCT f.invoiceid) AS invoices,
           SUM(f.quantity) AS quantity
    {_BASE_SALES}
      AND e.issalesperson = 1
    GROUP BY e.fullname
    ORDER BY revenue DESC
    """
    return _run(sql, _params(year_range, categories, territories))


@st.cache_data(ttl=600, show_spinner=False)
def delivery_vs_delay(year_range, categories=None, territories=None, delivery=None) -> pd.DataFrame:
    sql = f"""
    SELECT COALESCE(dm.deliverymethodname, '(none)') AS delivery_method,
           f.paymentdelay_days,
           f.invoiceamount
    {_BASE_INVOICES}
      AND f.paymentdelay_days IS NOT NULL
    """
    return _run(sql, _params(year_range, categories, territories, delivery))


@st.cache_data(ttl=600, show_spinner=False)
def delivery_summary(year_range, categories=None, territories=None, delivery=None) -> pd.DataFrame:
    sql = f"""
    SELECT COALESCE(dm.deliverymethodname, '(none)') AS delivery_method,
           COUNT(*) AS invoices,
           AVG(f.paymentdelay_days)::numeric(10,2) AS avg_delay_days,
           AVG(f.invoiceamount)::numeric(10,2)    AS avg_invoice
    {_BASE_INVOICES}
    GROUP BY dm.deliverymethodname
    ORDER BY invoices DESC
    """
    return _run(sql, _params(year_range, categories, territories, delivery))


# =============================================================================
# FINANCE
# =============================================================================

@st.cache_data(ttl=600, show_spinner=False)
def outstanding_by_customer(year_range, categories=None, territories=None, delivery=None, n=30) -> pd.DataFrame:
    sql = f"""
    SELECT c.customername AS customer, c.category, l.salesterritory,
           SUM(f.outstandingbalance) AS outstanding,
           SUM(f.invoiceamount)      AS invoiced,
           AVG(f.paymentdelay_days)::numeric(10,2) AS avg_delay
    {_BASE_INVOICES}
    GROUP BY c.customername, c.category, l.salesterritory
    HAVING SUM(f.outstandingbalance) > 0
    ORDER BY outstanding DESC
    LIMIT :n
    """
    p = _params(year_range, categories, territories, delivery); p["n"] = int(n)
    return _run(sql, p)


@st.cache_data(ttl=600, show_spinner=False)
def outstanding_by_territory(year_range, categories=None, territories=None, delivery=None) -> pd.DataFrame:
    sql = f"""
    SELECT l.salesterritory,
           SUM(f.outstandingbalance) AS outstanding,
           SUM(f.invoiceamount)      AS invoiced
    {_BASE_INVOICES}
    GROUP BY l.salesterritory
    ORDER BY outstanding DESC
    """
    return _run(sql, _params(year_range, categories, territories, delivery))


@st.cache_data(ttl=600, show_spinner=False)
def payment_delay_distribution(year_range, categories=None, territories=None, delivery=None) -> pd.DataFrame:
    sql = f"""
    SELECT f.paymentdelay_days
    {_BASE_INVOICES}
      AND f.paymentdelay_days IS NOT NULL
    """
    return _run(sql, _params(year_range, categories, territories, delivery))
