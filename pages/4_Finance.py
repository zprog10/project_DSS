"""Finance — outstanding balance analysis.

Answers Q6 (outstanding balance per customer/territory).
"""

import streamlit as st

from dashboard.db import sidebar_filters
from dashboard.queries import outstanding_by_customer, outstanding_by_territory
from dashboard.charts import bar_top, scatter_outstanding, kpi_card, fmt_money

st.set_page_config(page_title="Finance", page_icon="💰", layout="wide")
st.title("💰 Finance")
st.caption(
    "Receivables health: who owes how much and where. "
    "Audience: finance / accounts receivable."
)

filters = sidebar_filters(include_delivery=False)

# ---- Headline finance KPIs --------------------------------------------------
df_t = outstanding_by_territory(filters["year_range"], filters["categories"],
                                filters["territories"])

total_outstanding = float(df_t["outstanding"].sum()) if not df_t.empty else 0.0
total_invoiced    = float(df_t["invoiced"].sum())    if not df_t.empty else 0.0
ar_ratio = (total_outstanding / total_invoiced * 100) if total_invoiced else 0

c1, c2, c3 = st.columns(3)
with c1: kpi_card("Outstanding balance", fmt_money(total_outstanding))
with c2: kpi_card("Total invoiced",      fmt_money(total_invoiced))
with c3: kpi_card("Outstanding ratio",   f"{ar_ratio:.1f}%",
                  help="Outstanding / Invoiced")

# ---- By territory -----------------------------------------------------------
st.subheader("Outstanding balance by sales territory")
st.plotly_chart(
    bar_top(df_t, x="salesterritory", y="outstanding", color=None,
            title="Outstanding by territory"),
    use_container_width=True,
)

# ---- By customer (scatter + top table) --------------------------------------
st.subheader("Outstanding by customer")
n = st.slider("Top N customers (outstanding)", 10, 100, 30, key="fin_n")
df_c = outstanding_by_customer(filters["year_range"], filters["categories"],
                               filters["territories"], n=n)

st.plotly_chart(scatter_outstanding(df_c), use_container_width=True)

with st.expander("Top customers — detail"):
    view = df_c.copy()
    if not view.empty:
        view["outstanding"] = view["outstanding"].apply(fmt_money)
        view["invoiced"]    = view["invoiced"].apply(fmt_money)
    st.dataframe(view, use_container_width=True, hide_index=True)
