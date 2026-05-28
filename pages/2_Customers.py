"""Customers — ranking by revenue/profit + category/brand mix.

Answers Q8 (customer ranking) and the complementary category mix question.
"""

import streamlit as st

from dashboard.db import sidebar_filters
from dashboard.queries import customers_ranking, category_brand_mix
from dashboard.charts import bar_top, treemap_category_brand, fmt_money

st.set_page_config(page_title="Customers", page_icon="👥", layout="wide")
st.title("👥 Customers")
st.caption(
    "Which customers drive most of the revenue, and how revenue distributes "
    "across categories and brands. Audience: account managers and marketing."
)

filters = sidebar_filters(include_delivery=False)

# ---- Top customers bar -------------------------------------------------------
st.subheader("Principais clientes por receita")
n = st.slider("Top N clientes", 10, 100, 30, key="customers_n")
df = customers_ranking(filters["year_range"], filters["categories"], filters["territories"], n=n)

st.plotly_chart(
    bar_top(df, x="customer", y="revenue", color="category",
            title=f"Top {n} clientes por receita"),
    use_container_width=True,
)

# ---- Detail table ------------------------------------------------------------
st.subheader("Detalhe dos principais clientes")
view = df.copy()
if not view.empty:
    view["revenue"] = view["revenue"].apply(fmt_money)
    view["profit"]  = view["profit"].apply(fmt_money)
st.dataframe(view, use_container_width=True, hide_index=True)

# ---- Category mix ------------------------------------------------------------
st.subheader("Mix de receita: categoria de cliente × marca do produto")
df_mix = category_brand_mix(filters["year_range"], filters["categories"], filters["territories"])
st.plotly_chart(treemap_category_brand(df_mix, title="Receita por categoria e marca"), use_container_width=True)
