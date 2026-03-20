"""
Query engine — the core LLM call.

Pinterest-like pipeline:
  1. Table selection   (table_selector.py)
  2. Schema context    (catalog/tables.json column docs + caveats)
  3. Few-shot examples (query_memory.py — past successful queries)
  4. Claude generates pandas code + chart spec
  5. Execute code, build chart
  6. Save to query history (self-reinforcing loop)
"""

import anthropic
import pandas as pd
import plotly.express as px
import json
import traceback
import os
from dotenv import load_dotenv

from utils.table_selector import select_tables, build_schema_context, load_catalog
from utils.query_memory import find_similar, build_few_shot_context, save_query

load_dotenv()

CHART_BUILDERS = {
    "bar":       px.bar,
    "line":      px.line,
    "scatter":   px.scatter,
    "histogram": px.histogram,
    "pie":       px.pie,
}


def _get_api_key() -> str:
    try:
        import streamlit as st
        return st.secrets["ANTHROPIC_API_KEY"]
    except Exception:
        return os.environ.get("ANTHROPIC_API_KEY", "")


def ask_data(dataframes: dict, question: str) -> dict:
    """
    Full Pinterest-style pipeline:
      dataframes: dict of {table_name: pd.DataFrame}
      question:   user's natural language question
    Returns: {answer, chart, data, tables_used, pandas_code, error}
    """
    client = anthropic.Anthropic(api_key=_get_api_key())
    catalog = load_catalog()

    # ── Step 1: Table selection ──────────────────────────────────────────────
    selected_tables = select_tables(question, catalog)
    # Filter to only tables we actually have loaded
    selected_tables = [t for t in selected_tables if t in dataframes]
    if not selected_tables:
        selected_tables = list(dataframes.keys())[:1]

    # ── Step 2: Schema context (column docs + caveats) ───────────────────────
    schema_context = build_schema_context(selected_tables, dataframes, catalog)

    # ── Step 3: Few-shot examples from query history ─────────────────────────
    similar = find_similar(question, top_k=3)
    few_shot = build_few_shot_context(similar)

    # ── Step 4: Build prompt ─────────────────────────────────────────────────
    table_vars = "\n".join(
        f"  {name}: pd.DataFrame  # {len(dataframes[name]):,} rows"
        for name in selected_tables
    )

    prompt = f"""You are a data analyst. Answer the user's question by writing pandas code.

AVAILABLE DATAFRAMES (already loaded as variables):
{table_vars}

SCHEMA & COLUMN DOCUMENTATION:
{schema_context}

{few_shot}

USER QUESTION: {question}

Instructions:
- Write pandas code using the variable names above (e.g. `beauty_reviews`, `electronics_products`)
- Store the final result in a variable called `result` (must be a DataFrame or Series)
- For single scalar values, wrap them: result = pd.DataFrame({{"value": [computed_value]}})
- If joining tables, use the join keys documented in the schema
- Apply data caveats (e.g. dropna() for price columns)
- Limit results to top 20 rows for readability
- Use `pd` for pandas operations

Respond with ONLY a valid JSON object (no markdown):
{{
  "pandas_code": "result = ...",
  "chart_type": "bar|line|scatter|histogram|pie|none",
  "chart_x": "column_name_or_null",
  "chart_y": "column_name_or_null",
  "explanation": "Plain English answer including key numbers from the result."
}}"""

    try:
        response = client.messages.create(
            model="claude-opus-4-6",
            max_tokens=2000,
            thinking={"type": "adaptive"},
            messages=[{"role": "user", "content": prompt}],
        )

        text = next((b.text for b in response.content if b.type == "text"), "")
        text = text.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]

        data = json.loads(text)
        pandas_code = data["pandas_code"]

        # ── Step 5: Execute ──────────────────────────────────────────────────
        local_vars = {name: dataframes[name] for name in selected_tables}
        local_vars["pd"] = pd
        exec(pandas_code, {"pd": pd, "__builtins__": {}}, local_vars)
        result = local_vars.get("result", pd.DataFrame())

        if isinstance(result, pd.Series):
            result = result.reset_index()
            result.columns = [str(c) for c in result.columns]

        # ── Build chart ──────────────────────────────────────────────────────
        chart = None
        chart_type = data.get("chart_type", "none")
        chart_x    = data.get("chart_x")
        chart_y    = data.get("chart_y")

        if chart_type != "none" and isinstance(result, pd.DataFrame) and not result.empty:
            fn = CHART_BUILDERS.get(chart_type, px.bar)
            try:
                if chart_type == "histogram":
                    chart = fn(result, x=chart_x)
                elif chart_type == "pie":
                    chart = fn(result, names=chart_x, values=chart_y)
                elif chart_x and chart_y:
                    chart = fn(result, x=chart_x, y=chart_y)
            except Exception:
                chart = None

        # ── Step 6: Save to query history ────────────────────────────────────
        save_query(
            question=question,
            tables_used=selected_tables,
            pandas_code=pandas_code,
            chart_type=chart_type,
            explanation=data.get("explanation", ""),
            success=True,
        )

        return {
            "answer":       data.get("explanation", "Done."),
            "chart":        chart,
            "data":         result if isinstance(result, pd.DataFrame) else pd.DataFrame(),
            "tables_used":  selected_tables,
            "pandas_code":  pandas_code,
            "error":        None,
        }

    except json.JSONDecodeError as e:
        save_query(question, selected_tables, "", success=False)
        return {"error": f"Claude returned invalid JSON. Try rephrasing. ({e})", "tables_used": selected_tables}
    except KeyError as e:
        save_query(question, selected_tables, "", success=False)
        return {"error": f"Column not found: {e}. Check the schema in the sidebar.", "tables_used": selected_tables}
    except Exception as e:
        save_query(question, selected_tables, "", success=False)
        return {"error": f"Error: {e}\n\n{traceback.format_exc()}", "tables_used": selected_tables}
