"""WWI Data Mart Dashboard — Home page.

Run with:
    streamlit run app.py
"""

import streamlit as st

from dashboard.db import sidebar_filters
from dashboard.queries import kpis_sales, kpis_invoices, revenue_by_month
from dashboard.charts import (
    kpi_card, fmt_money, fmt_int, fmt_float, line_revenue,
)

st.set_page_config(
    page_title="WWI Data Mart — Home",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("Wide World Importers — Data Mart Dashboard")
st.caption(
    "Executive overview of sales, customers, operations and finance, "
    "built on the P01 Medallion data mart (Supabase Postgres, gold layer)."
)

filters = sidebar_filters(include_delivery=False)

# ---- Top KPIs ---------------------------------------------------------------
sales = kpis_sales(filters["year_range"], filters["categories"], filters["territories"])
inv = kpis_invoices(filters["year_range"], filters["categories"], filters["territories"])

st.subheader("Headline KPIs")

c1, c2, c3, c4 = st.columns(4)
with c1: kpi_card("Total revenue",  fmt_money(sales["revenue"]),  help="Σ FactSales.ExtendedPrice")
with c2: kpi_card("Total profit",   fmt_money(sales["profit"]),   help="Σ FactSales.LineProfit")
with c3: kpi_card("Invoices",       fmt_int(inv["invoices"]),     help="Count of FactInvoices rows")
with c4: kpi_card("Avg. invoice",   fmt_money(inv["avg_invoice"]),help="AVG FactInvoices.InvoiceAmount")

c5, c6, c7, c8 = st.columns(4)
with c5: kpi_card("Total quantity",      fmt_int(sales["qty"]),
                  help="Σ FactSales.Quantity")
with c6: kpi_card("Outstanding balance", fmt_money(inv["outstanding"]),
                  help="Σ FactInvoices.OutstandingBalance")
with c7: kpi_card("Active customers",    fmt_int(sales["active_customers"]),
                  help="Distinct CustomerKey in FactSales")
with c8: kpi_card("Products sold",       fmt_int(sales["products_sold"]),
                  help="Distinct ProductKey in FactSales")

# Margin derived metric
revenue = float(sales["revenue"]) if sales["revenue"] else 0
profit  = float(sales["profit"])  if sales["profit"]  else 0
margin_pct = (profit / revenue * 100) if revenue else 0
st.caption(
    f"Overall gross margin: **{margin_pct:.1f}%** · "
    f"Years: **{filters['year_range'][0]} – {filters['year_range'][1]}** · "
    f"Categories: **{', '.join(filters['categories']) if filters['categories'] else 'All'}** · "
    f"Territories: **{', '.join(filters['territories']) if filters['territories'] else 'All'}**"
)

# ---- Trend ------------------------------------------------------------------
st.subheader("Revenue trend")
df = revenue_by_month(filters["year_range"], filters["categories"], filters["territories"])
st.plotly_chart(line_revenue(df), use_container_width=True)

# ---- Navigation hints -------------------------------------------------------
st.divider()
st.subheader("Where to look next")
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.markdown("**📈 Sales Performance**  \nRevenue, profit and quantity by product, category, territory and time.")
with col2:
    st.markdown("**👥 Customers**  \nTop customers by revenue, category/brand mix.")
with col3:
    st.markdown("**🛠 Operations**  \nSalesperson ranking by revenue and volume.")
with col4:
    st.markdown("**💰 Finance**  \nOutstanding balance by customer and territory.")

st.caption(
    "Filters in the sidebar apply to every page. Use the Streamlit page menu "
    "(top-left) to navigate."
)
