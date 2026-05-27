"""Finance — outstanding balance and payment-delay analysis.

Answers Q6 (outstanding per customer/territory) and Q7 (payment delay distribution).
"""

import streamlit as st

from dashboard.db import sidebar_filters
from dashboard.queries import (
    outstanding_by_customer, outstanding_by_territory, payment_delay_distribution,
)
from dashboard.charts import (
    bar_top, scatter_outstanding, hist_delay, kpi_card, fmt_money, fmt_float,
)

st.set_page_config(page_title="Finance", page_icon="💰", layout="wide")
st.title("💰 Finance")
st.caption(
    "Receivables health: who owes how much, where, and how late payments arrive. "
    "Audience: finance / accounts receivable."
)

filters = sidebar_filters(include_delivery=True)

# ---- Headline finance KPIs --------------------------------------------------
df_t = outstanding_by_territory(filters["year_range"], filters["categories"],
                                filters["territories"], filters["delivery"])
df_d = payment_delay_distribution(filters["year_range"], filters["categories"],
                                  filters["territories"], filters["delivery"])

total_outstanding = float(df_t["outstanding"].sum()) if not df_t.empty else 0.0
total_invoiced    = float(df_t["invoiced"].sum())    if not df_t.empty else 0.0
ar_ratio = (total_outstanding / total_invoiced * 100) if total_invoiced else 0
avg_delay = float(df_d["paymentdelay_days"].mean()) if not df_d.empty else 0
med_delay = float(df_d["paymentdelay_days"].median()) if not df_d.empty else 0

c1, c2, c3, c4 = st.columns(4)
with c1: kpi_card("Outstanding balance", fmt_money(total_outstanding))
with c2: kpi_card("Total invoiced",      fmt_money(total_invoiced))
with c3: kpi_card("Outstanding ratio",   f"{ar_ratio:.1f}%",
                  help="Outstanding / Invoiced")
with c4: kpi_card("Avg / median delay",  f"{fmt_float(avg_delay,1)} / {fmt_float(med_delay,1)} d")

# ---- By territory ------------------------------------------------------------
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
                               filters["territories"], filters["delivery"], n=n)

st.plotly_chart(scatter_outstanding(df_c), use_container_width=True)

with st.expander("Top customers — detail"):
    view = df_c.copy()
    if not view.empty:
        view["outstanding"] = view["outstanding"].apply(fmt_money)
        view["invoiced"]    = view["invoiced"].apply(fmt_money)
    st.dataframe(view, use_container_width=True, hide_index=True)

# ---- Delay distribution -----------------------------------------------------
st.subheader("Payment delay distribution")
st.plotly_chart(hist_delay(df_d), use_container_width=True)
