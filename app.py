import streamlit as st
import pandas as pd
from utils.query_engine import ask_data
from utils.loader import load_all_tables, table_summary
from utils.query_memory import get_stats

st.set_page_config(page_title="Ask APD", page_icon="🔍", layout="wide")

# ── Design system ─────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* Buttons — pill shape, warm border, orange primary */
.stButton > button {
    border-radius: 24px;
    border: 1.5px solid #E0D8CF;
    background: #FFFFFF;
    color: #1C1917;
    font-weight: 500;
    transition: border-color 0.15s, color 0.15s, background 0.15s;
}
.stButton > button:hover {
    border-color: #DF5830;
    color: #DF5830;
    background: #FFF5F2;
}
/* Primary button (Download, etc.) */
div[data-testid="stButton"] > button[kind="primary"],
.stButton > button[kind="primary"] {
    background: #DF5830 !important;
    color: #FFFFFF !important;
    border: none !important;
}
div[data-testid="stButton"] > button[kind="primary"]:hover {
    background: #C94A24 !important;
}

/* Chat input — rounded */
.stChatInput textarea, .stChatInput > div {
    border-radius: 24px !important;
    border: 1.5px solid #E0D8CF !important;
}

/* Sidebar */
[data-testid="stSidebar"] {
    border-right: 1px solid #E0D8CF;
}

/* Metric cards */
[data-testid="metric-container"] {
    background: #FFFFFF;
    border: 1px solid #E0D8CF;
    border-radius: 12px;
    padding: 12px 16px;
}

/* Expanders */
[data-testid="stExpander"] {
    border: 1px solid #E0D8CF;
    border-radius: 10px;
    overflow: hidden;
}

/* Dataframe */
[data-testid="stDataFrame"] {
    border-radius: 8px;
    overflow: hidden;
    border: 1px solid #E0D8CF;
}

/* Tabs — underline style */
.stTabs [data-baseweb="tab-list"] {
    border-bottom: 1.5px solid #E0D8CF;
    gap: 8px;
}
.stTabs [data-baseweb="tab"] {
    border-radius: 0;
    font-weight: 500;
}
.stTabs [data-baseweb="tab"][aria-selected="true"] {
    border-bottom: 2px solid #DF5830;
    color: #DF5830;
}

/* Alerts */
[data-testid="stAlert"] {
    border-radius: 10px;
}

/* Progress bar */
.stProgress > div > div {
    background: #DF5830;
    border-radius: 4px;
}

/* Divider */
hr {
    border-color: #E0D8CF;
}
</style>
""", unsafe_allow_html=True)

# ── Header ───────────────────────────────────────────────────────────────────
st.title("🔍 Ask APD")
st.caption("Natural language → data insights · Powered by Claude Opus 4.6")

# ── Load all tables ──────────────────────────────────────────────────────────
tables = load_all_tables()

if not tables:
    st.info("No datasets loaded yet. Download the sample Amazon review datasets to get started.")
    st.markdown("""
    **4 tables · 1.47M rows · ~280 MB total**
    - `beauty_reviews` — 701K customer reviews for Beauty products
    - `beauty_products` — 112K Beauty product catalog entries
    - `electronics_reviews` — 500K customer reviews for Electronics
    - `electronics_products` — 161K Electronics product catalog entries
    """)
    if st.button("⬇️ Download Sample Data", type="primary"):
        from utils.download_sample import (
            download_beauty_products, download_beauty_reviews,
            download_electronics_products, download_electronics_reviews,
        )
        progress = st.progress(0, text="Starting download...")
        download_beauty_products();  progress.progress(25, text="Downloading beauty products... ✓  Fetching beauty reviews (large)...")
        download_beauty_reviews();   progress.progress(50, text="Beauty reviews ✓  Fetching electronics products...")
        download_electronics_products(); progress.progress(75, text="Electronics products ✓  Fetching electronics reviews (large)...")
        download_electronics_reviews();  progress.progress(100, text="All datasets ready!")
        st.success("Download complete! Reloading...")
        st.rerun()
    st.stop()

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("Data Catalog")
    st.caption(f"{len(tables)} tables loaded")

    TABLE_COLORS = {
        "beauty_reviews":      "#DF5830",
        "beauty_products":     "#A83A1A",
        "electronics_reviews": "#4A7FA5",
        "electronics_products":"#2D5F80",
    }

    for info in table_summary(tables):
        color = TABLE_COLORS.get(info["name"], "#888")
        st.markdown(
            f'<div style="border-left:4px solid {color};padding:8px 12px;margin:6px 0;'
            f'border-radius:8px;background:#FFFFFF;border:1px solid #E0D8CF;border-left:4px solid {color}">'
            f'<b style="color:#1C1917">{info["name"]}</b><br>'
            f'<small style="color:#6B6560">{info["rows"]:,} rows · {info["columns"]} cols · {info["file_mb"]} MB</small><br>'
            f'<small style="color:#9C948E">{info["description"][:80]}...</small>'
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
