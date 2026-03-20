"""
Table selector — Pinterest's "table discovery" step.

Given a user question, asks Claude which tables from the catalog are
needed to answer it, then returns their schemas + column docs as a
single context string to inject into the query engine prompt.
"""

import json
import os
import anthropic
from dotenv import load_dotenv

load_dotenv()

_CATALOG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "catalog", "tables.json")

def _get_api_key() -> str:
    try:
        import streamlit as st
        return st.secrets["ANTHROPIC_API_KEY"]
    except Exception:
        return os.environ.get("ANTHROPIC_API_KEY", "")


def load_catalog() -> dict:
    with open(_CATALOG_PATH) as f:
        return json.load(f)


def select_tables(question: str, catalog: dict) -> list[str]:
    """
    Ask Claude which tables are relevant to the question.
    Returns a list of table names (keys in catalog).
    Falls back to all tables if parsing fails.
    """
    client = anthropic.Anthropic(api_key=_get_api_key())

    summaries = "\n".join(
        f'- "{name}": {meta["description"]}'
        for name, meta in catalog.items()
    )

    prompt = f"""You are a data warehouse routing agent.

Available tables:
{summaries}

User question: "{question}"

Which tables are needed to answer this question?
Rules:
- Return only tables that are directly needed
- If comparing Beauty vs Electronics, include both review tables
- If the question needs product metadata (brand, price, subcategory), include the products table
- If only review stats are needed, the reviews table is sufficient
- Cross-category comparisons need both beauty_reviews AND electronics_reviews

Return ONLY a valid JSON array of table names. Example: ["beauty_reviews"]
No explanation, no markdown."""

    response = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=200,
        messages=[{"role": "user", "content": prompt}],
    )

    text = response.content[0].text.strip()
    # Strip markdown fences if present
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]

    try:
        selected = json.loads(text)
        # Validate all names exist
        valid = [t for t in selected if t in catalog]
        return valid if valid else list(catalog.keys())[:2]
    except (json.JSONDecodeError, TypeError):
        # Fallback: return beauty_reviews as default single table
        return ["beauty_reviews"]


def build_schema_context(table_names: list[str], dataframes: dict, catalog: dict) -> str:
    """
    Build the schema context string injected into the query engine prompt.
    Includes: column docs, data caveats, join keys, and actual dtypes from the df.
    This is Pinterest's "domain context injection" step.
    """
    parts = []
    for name in table_names:
        if name not in dataframes or name not in catalog:
            continue
        df = dataframes[name]
        meta = catalog[name]

        section = [f"### Table: `{name}` (variable name in code: `{name}`)"]
        section.append(f"Description: {meta['description']}")
        section.append(f"Shape: {len(df):,} rows × {len(df.columns)} columns")

        # Actual dtypes (ground truth)
        section.append("\nColumn types (from actual data):")
        for col, dtype in df.dtypes.items():
            section.append(f"  {col}: {dtype}")

        # Business definitions from catalog
        if meta.get("columns"):
            section.append("\nColumn definitions:")
            for col, doc in meta["columns"].items():
                section.append(f"  {col}: {doc}")

        # Data caveats — this is the "domain expertise" layer
        if meta.get("data_caveats"):
            section.append("\nIMPORTANT data caveats:")
            for caveat in meta["data_caveats"]:
                section.append(f"  ⚠️  {caveat}")

        # Join keys
        if meta.get("join_keys"):
            section.append("\nJoin keys:")
            for other_table, key in meta["join_keys"].items():
                if other_table in table_names:
                    section.append(f"  {name} ↔ {other_table} on `{key}`")

        # Sample values for key categorical columns
        section.append("\nSample values (first 3 unique per key column):")
        for col in df.columns:
            if df[col].dtype == object and col not in ('review_text', 'review_title', 'product_title', 'parent_asin'):
                vals = df[col].dropna().unique()[:3].tolist()
                section.append(f"  {col}: {vals}")

        parts.append("\n".join(section))

    return "\n\n" + "─" * 60 + "\n\n".join(parts) + "\n" + "─" * 60
