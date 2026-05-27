"""Customers — ranking by revenue/profit + category/brand mix.

Answers Q8 (customer ranking) and the complementary category mix question.
"""

import streamlit as st

from dashboard.db import sidebar_filters
from dashboard.queries import customers_ranking, category_brand_mix
from dashboard.charts import pareto, treemap_category_brand, fmt_money

st.set_page_config(page_title="Customers", page_icon="👥", layout="wide")
st.title("👥 Customers")
st.caption(
    "Which customers drive most of the revenue, and how revenue distributes "
    "across categories and brands. Audience: account managers and marketing."
)

filters = sidebar_filters(include_delivery=False)

# ---- Pareto -----------------------------------------------------------------
st.subheader("Customer Pareto (revenue concentration)")
n = st.slider("Top N customers", 10, 100, 30, key="customers_n")
df = customers_ranking(filters["year_range"], filters["categories"], filters["territories"], n=n)

st.plotly_chart(
    pareto(df, value_col="revenue", label_col="customer",
           title=f"Top {n} customers by revenue (with cumulative share)"),
    use_container_width=True,
)

# ---- Top table --------------------------------------------------------------
st.subheader("Top customers — detail")
view = df.copy()
if not view.empty:
    view["revenue"] = view["revenue"].apply(fmt_money)
    view["profit"]  = view["profit"].apply(fmt_money)
st.dataframe(view, use_container_width=True, hide_index=True)

# ---- Treemap ----------------------------------------------------------------
st.subheader("Revenue mix: customer category × product brand")
df_mix = category_brand_mix(filters["year_range"], filters["categories"], filters["territories"])
st.plotly_chart(treemap_category_brand(df_mix), use_container_width=True)
