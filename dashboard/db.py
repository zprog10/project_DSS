"""SQLAlchemy engine factory + shared sidebar filter widgets.

The engine factory mirrors the pattern used in validate_db.py / 04_quality_checks.py
(URL.create with sslmode=require), wrapped in @st.cache_resource so it survives
Streamlit reruns.
"""

import os
from typing import Tuple, List

import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL


def _secret(key: str, default=None):
    """Read a credential from st.secrets (Streamlit Cloud) or .env (local).

    st.secrets wins when available — that's how Streamlit Cloud injects values.
    Falls back to environment variables loaded by python-dotenv for local dev.
    """
    try:
        if key in st.secrets:
            return st.secrets[key]
    except (FileNotFoundError, KeyError, AttributeError):
        pass  # st.secrets unavailable (e.g. running outside a Streamlit context)
    return os.getenv(key, default)


@st.cache_resource(show_spinner=False)
def get_engine():
    load_dotenv(override=False)  # local-only; no-op on Streamlit Cloud
    url = URL.create(
        "postgresql+psycopg2",
        username=_secret("SUPABASE_USER"),
        password=_secret("SUPABASE_PASSWORD"),
        host=_secret("SUPABASE_URL"),
        port=int(_secret("SUPABASE_PORT", 5432)),
        database=_secret("SUPABASE_DB"),
        query={"sslmode": "require"},
    )
    return create_engine(url, pool_pre_ping=True)


@st.cache_data(ttl=3600, show_spinner=False)
def list_years() -> List[int]:
    sql = "SELECT DISTINCT d.year FROM gold.dimdate d " \
          "JOIN gold.factsales f ON f.datekey = d.datekey ORDER BY d.year"
    with get_engine().connect() as conn:
        return [int(r[0]) for r in conn.execute(text(sql))]


@st.cache_data(ttl=3600, show_spinner=False)
def list_categories() -> List[str]:
    sql = "SELECT DISTINCT category FROM gold.dimcustomer " \
          "WHERE date_to IS NULL AND category IS NOT NULL ORDER BY category"
    with get_engine().connect() as conn:
        return [r[0] for r in conn.execute(text(sql))]


@st.cache_data(ttl=3600, show_spinner=False)
def list_territories() -> List[str]:
    sql = "SELECT DISTINCT salesterritory FROM gold.dimlocation " \
          "WHERE date_to IS NULL AND salesterritory IS NOT NULL ORDER BY salesterritory"
    with get_engine().connect() as conn:
        return [r[0] for r in conn.execute(text(sql))]


@st.cache_data(ttl=3600, show_spinner=False)
def list_delivery_methods() -> List[str]:
    sql = "SELECT DISTINCT deliverymethodname FROM gold.dimdeliverymethod " \
          "WHERE date_to IS NULL AND deliverymethodname IS NOT NULL ORDER BY deliverymethodname"
    with get_engine().connect() as conn:
        return [r[0] for r in conn.execute(text(sql))]


def sidebar_filters(include_delivery: bool = False) -> dict:
    """Render the global sidebar filters and return the selected values.

    Selections are persisted in st.session_state under the same keys so they
    survive page navigation.
    """
    st.sidebar.header("Filters")

    years = list_years()
    y_min, y_max = (years[0], years[-1]) if years else (2017, 2020)
    year_range = st.sidebar.slider(
        "Year range",
        min_value=y_min, max_value=y_max,
        value=st.session_state.get("year_range", (y_min, y_max)),
        key="year_range",
    )

    categories = st.sidebar.multiselect(
        "Customer category",
        options=list_categories(),
        default=st.session_state.get("categories", []),
        key="categories",
        placeholder="All categories",
    )

    territories = st.sidebar.multiselect(
        "Sales territory",
        options=list_territories(),
        default=st.session_state.get("territories", []),
        key="territories",
        placeholder="All territories",
    )

    delivery: List[str] = []
    if include_delivery:
        delivery = st.sidebar.multiselect(
            "Delivery method",
            options=list_delivery_methods(),
            default=st.session_state.get("delivery", []),
            key="delivery",
            placeholder="All methods",
        )

    st.sidebar.caption(
        "Empty selection = no filter (all values included). "
        "Filters apply to every chart on the current page."
    )

    return {
        "year_range": year_range,
        "categories": categories or None,
        "territories": territories or None,
        "delivery": delivery or None,
    }
