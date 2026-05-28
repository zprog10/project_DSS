"""Operations — salesperson performance.

Answers Q3 (which salespersons perform best by volume and value).
"""

import streamlit as st

from dashboard.db import sidebar_filters
from dashboard.queries import salesperson_performance
from dashboard.charts import bar_top, fmt_money

st.set_page_config(page_title="Operations", page_icon="🛠", layout="wide")
st.title("🛠 Operations")
st.caption(
    "Salesperson productivity: who sells the most and who brings the most value. "
    "Audience: sales operations and management."
)

filters = sidebar_filters(include_delivery=False)

# ---- Salesperson ranking by revenue -----------------------------------------
st.subheader("Ranking de vendedores — por receita")
df_sp = salesperson_performance(filters["year_range"], filters["categories"], filters["territories"])
top_n = st.slider("Top N vendedores", 5, 50, 15, key="sp_n")
df_top = df_sp.head(top_n)

st.plotly_chart(
    bar_top(df_top, x="salesperson", y="revenue", color=None,
            title=f"Top {top_n} vendedores por receita"),
    use_container_width=True,
)

# ---- Salesperson ranking by quantity ----------------------------------------
st.subheader("Ranking de vendedores — por quantidade vendida")
st.plotly_chart(
    bar_top(df_top.sort_values("quantity", ascending=False),
            x="salesperson", y="quantity", color=None,
            title=f"Top {top_n} vendedores por quantidade"),
    use_container_width=True,
)

# ---- Detail table -----------------------------------------------------------
st.subheader("Tabela completa de vendedores")
view = df_sp.copy()
if not view.empty:
    view["revenue"] = view["revenue"].apply(fmt_money)
    view["profit"]  = view["profit"].apply(fmt_money)
st.dataframe(view, use_container_width=True, hide_index=True)
