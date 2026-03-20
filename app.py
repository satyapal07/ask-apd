import streamlit as st
import pandas as pd
from utils.query_engine import ask_data
from utils.loader import load_all_tables, table_summary
from utils.query_memory import get_stats

st.set_page_config(page_title="Ask APD", page_icon="🔍", layout="wide")

# ── Header ───────────────────────────────────────────────────────────────────
st.title("🔍 Ask APD")
st.caption("Natural language → data insights · Powered by Claude Opus 4.6")

# ── Load all tables ──────────────────────────────────────────────────────────
tables = load_all_tables()

if not tables:
    st.error("No datasets found in `data/`. Run `python utils/download_sample.py` first.")
    st.stop()

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("Data Catalog")
    st.caption(f"{len(tables)} tables loaded")

    TABLE_COLORS = {
        "beauty_reviews":      "#FF6B9D",
        "beauty_products":     "#C44B8A",
        "electronics_reviews": "#4B9FFF",
        "electronics_products":"#1B6FCC",
    }

    for info in table_summary(tables):
        color = TABLE_COLORS.get(info["name"], "#888")
        st.markdown(
            f'<div style="border-left:4px solid {color};padding:6px 10px;margin:4px 0;border-radius:4px">'
            f'<b>{info["name"]}</b><br>'
            f'<small>{info["rows"]:,} rows · {info["columns"]} cols · {info["file_mb"]} MB</small><br>'
            f'<small style="color:#aaa">{info["description"][:80]}...</small>'
            f'</div>',
            unsafe_allow_html=True,
        )

    st.divider()

    # Query history stats
    stats = get_stats()
    st.metric("Queries answered", stats["successful"])
    st.caption("Every answer teaches the system (Pinterest-style query memory)")

    st.divider()
    if st.button("Clear chat history"):
        st.session_state.messages = []
        st.rerun()

    st.divider()
    st.caption("Stack: Claude Opus 4.6 · Streamlit · Plotly · pandas")

# ── Data preview ─────────────────────────────────────────────────────────────
with st.expander("📊 Table Previews", expanded=False):
    tab_names = list(tables.keys())
    tabs = st.tabs(tab_names)
    for tab, name in zip(tabs, tab_names):
        with tab:
            df = tables[name]
            c1, c2, c3 = st.columns(3)
            c1.metric("Rows", f"{len(df):,}")
            c2.metric("Columns", len(df.columns))
            c3.metric("Memory", f"{df.memory_usage(deep=True).sum()/1e6:.0f} MB")
            st.dataframe(df.head(50), use_container_width=True)

# ── Sample questions ─────────────────────────────────────────────────────────
SAMPLE_QUESTIONS = [
    "Show beauty review volume by year",
    "Compare average star ratings: Beauty vs Electronics",
    "Which beauty brands have the most products?",
    "What's the price distribution of electronics products?",
    "Which products have the most helpful votes in beauty?",
    "Show Electronics review growth over time",
]

st.subheader("Try a question")
cols = st.columns(3)
for i, q in enumerate(SAMPLE_QUESTIONS):
    if cols[i % 3].button(q, key=f"sample_{i}", use_container_width=True):
        st.session_state.pending_prompt = q

# ── Chat interface ────────────────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        if msg["role"] == "assistant":
            # Show which tables were used (Pinterest-style provenance)
            if msg.get("tables_used"):
                badges = " ".join(
                    f'<span style="background:{TABLE_COLORS.get(t,"#555")};color:white;'
                    f'padding:2px 8px;border-radius:12px;font-size:0.75em;margin-right:4px">{t}</span>'
                    for t in msg["tables_used"]
                )
                st.markdown(f"**Tables used:** {badges}", unsafe_allow_html=True)

            st.write(msg["content"])

            if msg.get("chart") is not None:
                st.plotly_chart(msg["chart"], use_container_width=True)

            if msg.get("data") is not None and not msg["data"].empty:
                with st.expander("View result data"):
                    st.dataframe(msg["data"], use_container_width=True)

            if msg.get("pandas_code"):
                with st.expander("View generated code"):
                    st.code(msg["pandas_code"], language="python")
        else:
            st.write(msg["content"])

# ── Input ─────────────────────────────────────────────────────────────────────
prompt = st.chat_input("Ask anything about the data...")
if not prompt and "pending_prompt" in st.session_state:
    prompt = st.session_state.pop("pending_prompt")

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)

    with st.chat_message("assistant"):
        # Step 1 indicator
        with st.spinner("Selecting relevant tables..."):
            from utils.table_selector import select_tables, load_catalog
            catalog = load_catalog()
            selected = select_tables(prompt, catalog)
            selected = [t for t in selected if t in tables]

        if selected:
            badges = " ".join(
                f'<span style="background:{TABLE_COLORS.get(t,"#555")};color:white;'
                f'padding:2px 8px;border-radius:12px;font-size:0.75em;margin-right:4px">{t}</span>'
                for t in selected
            )
            st.markdown(f"**Tables selected:** {badges}", unsafe_allow_html=True)

        with st.spinner("Analyzing..."):
            result = ask_data(tables, prompt)

        if result.get("error"):
            st.error(result["error"])
            st.session_state.messages.append({
                "role": "assistant", "content": result["error"],
                "tables_used": result.get("tables_used", []),
            })
        else:
            st.write(result["answer"])

            if result.get("chart") is not None:
                st.plotly_chart(result["chart"], use_container_width=True)

            if result.get("data") is not None and not result["data"].empty:
                with st.expander("View result data"):
                    st.dataframe(result["data"], use_container_width=True)

            if result.get("pandas_code"):
                with st.expander("View generated code"):
                    st.code(result["pandas_code"], language="python")

            st.session_state.messages.append({
                "role":        "assistant",
                "content":     result["answer"],
                "chart":       result.get("chart"),
                "data":        result.get("data"),
                "tables_used": result.get("tables_used", []),
                "pandas_code": result.get("pandas_code", ""),
            })
