"""Reusable Plotly chart helpers + KPI card formatters."""

from typing import Optional

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

PALETTE = px.colors.qualitative.Set2
TEMPLATE = "plotly_white"


def fmt_money(v) -> str:
    if pd.isna(v):
        return "—"
    v = float(v)
    if abs(v) >= 1_000_000:
        return f"${v/1_000_000:,.2f}M"
    if abs(v) >= 1_000:
        return f"${v/1_000:,.1f}K"
    return f"${v:,.0f}"


def fmt_int(v) -> str:
    if pd.isna(v):
        return "—"
    return f"{int(v):,}"


def fmt_float(v, decimals=1) -> str:
    if pd.isna(v):
        return "—"
    return f"{float(v):,.{decimals}f}"


def kpi_card(label: str, value: str, help: Optional[str] = None, delta: Optional[str] = None):
    st.metric(label=label, value=value, delta=delta, help=help)


def line_revenue(df: pd.DataFrame, title: str = "Monthly revenue and profit") -> go.Figure:
    if df.empty:
        return _empty(title)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["period"], y=df["revenue"], name="Revenue",
                             mode="lines+markers", line=dict(color=PALETTE[0], width=2)))
    fig.add_trace(go.Scatter(x=df["period"], y=df["profit"], name="Profit",
                             mode="lines+markers", line=dict(color=PALETTE[1], width=2)))
    fig.update_layout(template=TEMPLATE, title=title, hovermode="x unified",
                      xaxis_title="Month", yaxis_title="USD",
                      legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    return fig


def area_category_year(df: pd.DataFrame, title: str = "Revenue by customer category over time") -> go.Figure:
    if df.empty:
        return _empty(title)
    fig = px.area(df, x="year", y="revenue", color="category",
                  template=TEMPLATE, title=title, color_discrete_sequence=PALETTE)
    fig.update_layout(yaxis_title="Revenue (USD)", xaxis_title="Year",
                      legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    return fig


def bar_top(df: pd.DataFrame, x: str, y: str, title: str, color: Optional[str] = None,
            orientation: str = "h") -> go.Figure:
    if df.empty:
        return _empty(title)
    if orientation == "h":
        df = df.iloc[::-1]
        fig = px.bar(df, x=y, y=x, color=color, template=TEMPLATE, title=title,
                     color_discrete_sequence=PALETTE, orientation="h")
        fig.update_layout(yaxis_title="", xaxis_title=y.replace("_", " ").title())
    else:
        fig = px.bar(df, x=x, y=y, color=color, template=TEMPLATE, title=title,
                     color_discrete_sequence=PALETTE)
        fig.update_layout(xaxis_title="", yaxis_title=y.replace("_", " ").title())
    return fig


def bar_country(df: pd.DataFrame, top: int = 25,
                title: str = "Revenue by country") -> go.Figure:
    if df.empty:
        return _empty(title)
    d = df.nlargest(top, "revenue").iloc[::-1]
    fig = px.bar(d, x="revenue", y="country", color="salesterritory",
                 template=TEMPLATE, title=title, orientation="h",
                 color_discrete_sequence=PALETTE,
                 hover_data={"profit": ":,.0f"})
    fig.update_layout(yaxis_title="", xaxis_title="Revenue (USD)")
    return fig


def treemap_category_brand(df: pd.DataFrame,
                           title: str = "Category → Brand revenue mix") -> go.Figure:
    if df.empty:
        return _empty(title)
    fig = px.treemap(df, path=["category", "brand"], values="revenue",
                     template=TEMPLATE, title=title,
                     color="revenue", color_continuous_scale="Blues")
    return fig


def pareto(df: pd.DataFrame, value_col: str, label_col: str,
           title: str = "Pareto") -> go.Figure:
    if df.empty:
        return _empty(title)
    d = df.sort_values(value_col, ascending=False).reset_index(drop=True)
    d["cum_pct"] = d[value_col].cumsum() / d[value_col].sum() * 100
    fig = go.Figure()
    fig.add_trace(go.Bar(x=d[label_col], y=d[value_col], name=value_col,
                         marker_color=PALETTE[0]))
    fig.add_trace(go.Scatter(x=d[label_col], y=d["cum_pct"], name="Cumulative %",
                             yaxis="y2", mode="lines+markers",
                             line=dict(color=PALETTE[2], width=2)))
    fig.update_layout(template=TEMPLATE, title=title,
                      xaxis_title="", yaxis_title=value_col.title(),
                      yaxis2=dict(title="Cumulative %", overlaying="y", side="right",
                                  range=[0, 100], ticksuffix="%"),
                      legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    fig.update_xaxes(tickangle=-45)
    return fig


def box_delivery_delay(df: pd.DataFrame,
                       title: str = "Payment delay distribution by delivery method") -> go.Figure:
    if df.empty:
        return _empty(title)
    fig = px.box(df, x="delivery_method", y="paymentdelay_days",
                 template=TEMPLATE, title=title, color="delivery_method",
                 color_discrete_sequence=PALETTE, points=False)
    fig.update_layout(xaxis_title="", yaxis_title="Payment delay (days)", showlegend=False)
    fig.update_xaxes(tickangle=-30)
    return fig


def hist_delay(df: pd.DataFrame, title: str = "Payment delay distribution (days)") -> go.Figure:
    if df.empty:
        return _empty(title)
    fig = px.histogram(df, x="paymentdelay_days", nbins=40, template=TEMPLATE, title=title,
                       color_discrete_sequence=[PALETTE[0]])
    fig.update_layout(xaxis_title="Payment delay (days)", yaxis_title="Invoices",
                      bargap=0.05)
    return fig


def scatter_outstanding(df: pd.DataFrame,
                        title: str = "Outstanding balance vs. invoiced (per customer)") -> go.Figure:
    if df.empty:
        return _empty(title)
    fig = px.scatter(df, x="invoiced", y="outstanding", color="category",
                     hover_data=["customer", "salesterritory", "avg_delay"],
                     template=TEMPLATE, title=title, color_discrete_sequence=PALETTE)
    fig.update_layout(xaxis_title="Invoiced (USD)", yaxis_title="Outstanding (USD)")
    return fig


def _empty(title: str) -> go.Figure:
    fig = go.Figure()
    fig.update_layout(template=TEMPLATE, title=title,
                      annotations=[dict(text="No data for the selected filters.",
                                        showarrow=False, font=dict(size=14, color="gray"))])
    return fig
