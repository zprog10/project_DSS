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
st.subheader("Salesperson ranking — by revenue")
df_sp = salesperson_performance(filters["year_range"], filters["categories"], filters["territories"])
top_n = st.slider("Show top N salespersons", 5, 50, 15, key="sp_n")
df_top = df_sp.head(top_n)

st.plotly_chart(
    bar_top(df_top, x="salesperson", y="revenue", color=None,
            title=f"Top {top_n} salespersons by revenue"),
    use_container_width=True,
)

# ---- Salesperson ranking by quantity ----------------------------------------
st.subheader("Salesperson ranking — by quantity sold")
st.plotly_chart(
    bar_top(df_top.sort_values("quantity", ascending=False),
            x="salesperson", y="quantity", color=None,
            title=f"Top {top_n} salespersons by quantity"),
    use_container_width=True,
)

# ---- Detail table -----------------------------------------------------------
st.subheader("Full salesperson detail")
view = df_sp.copy()
if not view.empty:
    view["revenue"] = view["revenue"].apply(fmt_money)
    view["profit"]  = view["profit"].apply(fmt_money)
st.dataframe(view, use_container_width=True, hide_index=True)
