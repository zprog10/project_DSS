"""Operations — salesperson performance and delivery-method impact on payment delay.

Answers Q3 (salesperson performance) and Q4 (delivery method × payment delay).
"""

import streamlit as st

from dashboard.db import sidebar_filters
from dashboard.queries import salesperson_performance, delivery_vs_delay, delivery_summary
from dashboard.charts import bar_top, box_delivery_delay, fmt_money, fmt_float

st.set_page_config(page_title="Operations", page_icon="🛠", layout="wide")
st.title("🛠 Operations")
st.caption(
    "Salesperson productivity and operational impact of delivery methods. "
    "Audience: sales operations and logistics."
)

filters = sidebar_filters(include_delivery=True)

# ---- Salesperson ------------------------------------------------------------
st.subheader("Salesperson ranking")
df_sp = salesperson_performance(filters["year_range"], filters["categories"], filters["territories"])
top_n = st.slider("Show top N salespersons", 5, 50, 15, key="sp_n")
df_top_sp = df_sp.head(top_n)

st.plotly_chart(
    bar_top(df_top_sp, x="salesperson", y="revenue", color=None,
            title=f"Top {top_n} salespersons by revenue"),
    use_container_width=True,
)

with st.expander("Detail table"):
    view = df_sp.copy()
    if not view.empty:
        view["revenue"] = view["revenue"].apply(fmt_money)
        view["profit"]  = view["profit"].apply(fmt_money)
    st.dataframe(view, use_container_width=True, hide_index=True)

# ---- Delivery vs delay ------------------------------------------------------
st.subheader("Delivery method × payment delay")

df_summary = delivery_summary(filters["year_range"], filters["categories"],
                              filters["territories"], filters["delivery"])
st.dataframe(df_summary, use_container_width=True, hide_index=True)

df_box = delivery_vs_delay(filters["year_range"], filters["categories"],
                           filters["territories"], filters["delivery"])
st.plotly_chart(box_delivery_delay(df_box), use_container_width=True)

if not df_summary.empty and len(df_summary) == 1:
    st.info(
        "ℹ️ The WWI source assigns **a single delivery method** (`Delivery Van`) "
        "to every invoice, so the chart shows only one distribution. "
        "The delivery-method filter is kept for completeness but acts as a no-op here."
    )

st.caption(
    "Box shows the distribution of `FactInvoices.PaymentDelay_Days` per delivery method "
    "(median + IQR + whiskers). Outliers hidden to keep the chart readable."
)
