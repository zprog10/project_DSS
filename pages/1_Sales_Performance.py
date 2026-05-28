"""Sales Performance — revenue, profit and quantity over time, by product, category and territory.

Answers business questions Q1 (revenue/profit per product, category, year),
Q2 (customer-category growth) and Q5 (revenue by territory/country).
"""

import streamlit as st

from dashboard.db import sidebar_filters
from dashboard.queries import (
    revenue_by_month, revenue_by_category_year, top_products, revenue_by_country,
)
from dashboard.charts import line_revenue, area_category_year, bar_top, bar_country

st.set_page_config(page_title="Sales Performance", page_icon="📈", layout="wide")
st.title("📈 Sales Performance")
st.caption(
    "How sales evolve over time and where the revenue comes from. "
    "Audience: sales managers and category leads."
)

filters = sidebar_filters(include_delivery=False)

# ---- Revenue & profit over time ---------------------------------------------
st.subheader("Receita e lucro ao longo do tempo")
df = revenue_by_month(filters["year_range"], filters["categories"], filters["territories"])
st.plotly_chart(line_revenue(df, title="Receita e lucro mensal"), use_container_width=True)

# ---- Category growth --------------------------------------------------------
st.subheader("Crescimento por categoria de cliente")
df_cat = revenue_by_category_year(filters["year_range"], filters["categories"], filters["territories"])
st.plotly_chart(area_category_year(df_cat, title="Receita por categoria ao longo do tempo"), use_container_width=True)

# ---- Top products + Top countries (side by side) ----------------------------
left, right = st.columns([3, 2])
with left:
    st.subheader("Principais produtos")
    top_n = st.slider("Top N produtos", 5, 50, 20, key="top_products_n")
    df_top = top_products(filters["year_range"], filters["categories"], filters["territories"], n=top_n)
    st.plotly_chart(
        bar_top(df_top, x="product", y="revenue", color="brand",
                title=f"Top {top_n} produtos por receita"),
        use_container_width=True,
    )
    with st.expander("Tabela detalhada"):
        st.dataframe(df_top, use_container_width=True, hide_index=True)

with right:
    st.subheader("Receita por país")
    df_geo = revenue_by_country(filters["year_range"], filters["categories"], filters["territories"])
    st.plotly_chart(bar_country(df_geo, top=25, title="Receita por país"), use_container_width=True)
