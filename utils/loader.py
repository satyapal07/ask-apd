"""
Multi-table loader with Streamlit caching.
Loads all parquet files defined in catalog/tables.json.
"""

import streamlit as st
import pandas as pd
import os
import json

_BASE = os.path.dirname(os.path.dirname(__file__))
_CATALOG_PATH = os.path.join(_BASE, "catalog", "tables.json")


def _catalog() -> dict:
    with open(_CATALOG_PATH) as f:
        return json.load(f)


@st.cache_data(show_spinner="Loading datasets...")
def load_all_tables() -> dict[str, pd.DataFrame]:
    """
    Load every table defined in catalog/tables.json that has a parquet file present.
    Returns {table_name: DataFrame}.
    """
    catalog = _catalog()
    tables = {}
    for name, meta in catalog.items():
        path = os.path.join(_BASE, meta["file"])
        if os.path.exists(path):
            tables[name] = pd.read_parquet(path)
    return tables


def table_summary(tables: dict[str, pd.DataFrame]) -> list[dict]:
    """Return lightweight metadata for each loaded table (for the UI)."""
    catalog = _catalog()
    summary = []
    for name, df in tables.items():
        meta = catalog.get(name, {})
        summary.append({
            "name":        name,
            "rows":        len(df),
            "columns":     len(df.columns),
            "description": meta.get("description", ""),
            "file_mb":     round(os.path.getsize(os.path.join(_BASE, meta["file"])) / 1e6, 1)
                           if os.path.exists(os.path.join(_BASE, meta["file"])) else 0,
        })
    return summary
