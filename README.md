# 🔍 Ask APD — Natural Language Data Explorer

> Ask questions about large datasets in plain English. Get instant answers + visualizations.

**[🚀 Live Demo →](https://satyapal07-ask-apd.streamlit.app)**

---

## What It Does

Type any question → the system picks the right tables, injects schema knowledge, retrieves similar past queries, and returns a chart + plain-English answer — all powered by Claude Opus 4.6.

**Example queries:**
- "Compare average star ratings: Beauty vs Electronics"
- "Which beauty brands have the most products?"
- "Show electronics review volume growth over time"
- "Which products have the most helpful votes?"
- "What's the price distribution of electronics products?"

---

## Background

This project is a public, open-source rebuild of **PayLens** — an internal natural language analytics tool I worked on as part of the Amazon Payments Data (APD) team.

At Amazon Payments, analysts across fraud, risk, merchant growth, and finance teams needed answers from **PayLake**, the payments data warehouse, which housed thousands of tables covering transactions, merchant behavior, authorization flows, and customer payment methods. The challenge was the same one Pinterest later described publicly: with hundreds of analytical tables and dozens of domain teams, simple keyword search wasn't enough. An analyst asking *"What's the authorization rate for new merchants in LATAM last quarter?"* needed the system to understand payment domain intent — not just match table names.

**PayLens** addressed this by building on top of two internal platforms:
- **DataCompass** — APD's internal data catalog, which stored table ownership, column-level metric definitions (e.g. `auth_rate`, `dispute_rate`, `gmv`), and data quality tiers. Equivalent to Pinterest's PinCat.
- **QueryForge** — the internal collaborative SQL editor where analysts wrote, ran, and shared queries. The history of analyst queries in QueryForge became the training signal for the system — the same insight Pinterest described as *"your analysts already wrote the perfect prompt."*
- **TxnMetrics** — a centralized library of payment metric definitions (e.g. *"GMV = sum of authorized transaction amounts excluding refunds"*) that was injected into prompts to ground the LLM in Amazon Payments-specific business logic.

Since internal implementation details are confidential, this repo is a from-scratch public reimplementation using the same architectural principles — applied to Amazon's public review dataset instead.

---

## Pinterest Arrived at the Same Architecture

When Pinterest Engineering published [*From Text-to-SQL to an Analytics Agent*](https://medium.com/pinterest-engineering), the architecture they described was a strong external validation of the same approach PayLens had taken internally. Pinterest faced the same core problem at larger scale — **100,000+ analytical tables**, **2,500+ analysts** across dozens of domains — and independently converged on the same solutions.

Their two key engineering choices mirror what PayLens had already built:

**1. Unified context-intent embeddings**
Pinterest transforms historical analyst queries into semantically rich representations that capture *the business question a query was designed to answer*, not raw SQL syntax. PayLens did the same using QueryForge query history: each SQL query was annotated with its analytical intent (e.g. *"authorization rate trend for high-risk merchants"*), enabling retrieval that matched meaning rather than keywords.

**2. Structural & statistical patterns with governance-aware ranking**
Pinterest extracts validated join keys, filters, and aggregation logic from query history, then ranks results by governance signals (table tiers, freshness, documentation quality). At APD, DataCompass tier tags played the same role — Tier 1 tables (production-quality, actively owned) ranked above Tier 3 staging or deprecated tables, and TxnMetrics definitions ensured metric calculations were consistent across teams.

The fact that two independent teams — one at Amazon Payments, one at Pinterest — converged on the same architecture is a testament to how well-suited this approach is for large-scale internal analytics. The result in both cases is **self-reinforcing**: every query an analyst writes enriches the knowledge base, making the combined expertise of hundreds of analysts accessible to everyone rather than siloed within individual teams.

---

## How This Project Maps to Both Systems

| Amazon Payments (PayLens) | Pinterest (Analytics Agent) | Ask APD (This Project) |
|---|---|---|
| PayLake — payments data warehouse | 100,000+ warehouse tables | 4 Amazon review/product tables |
| DataCompass — internal data catalog | PinCat (built on DataHub) | `catalog/tables.json` |
| TxnMetrics — payment metric definitions | Glossary terms (e.g. `engaged_user`) | Column-level business definitions in catalog |
| QueryForge query history | Query history as knowledge base | SQLite query memory |
| LLM routes to relevant PayLake tables | Vector search over 100K tables | Claude-powered table selector |
| DataCompass tier tags suppress deprecated tables | Governance-aware ranking | Data caveats flag unreliable columns |
| SQL generation grounded in TxnMetrics | SQL→text pipeline with domain context | pandas code with injected schema context |
| Self-reinforcing: every query teaches the system | Self-reinforcing learning cycle | Every answer saved to query history |
| Internal Redshift + Spark infrastructure | OpenSearch vector DB + Airflow | SQLite + local parquet files |

---

## Architecture

```
User Question
     │
     ▼
┌─────────────────────────────────────────────────────┐
│  STEP 1 — TABLE SELECTION                           │
│  Claude routes question to relevant table(s)        │
│  from catalog/tables.json                           │
│  (PayLens: DataCompass table routing                │
│   Pinterest: vector search over 100K tables)        │
└─────────────────────────────────────────────────────┘
     │  e.g. ["beauty_reviews", "beauty_products"]
     ▼
┌─────────────────────────────────────────────────────┐
│  STEP 2 — DOMAIN CONTEXT INJECTION                  │
│  Column definitions, data caveats, join keys        │
│  injected from catalog/tables.json                  │
│  (PayLens: TxnMetrics + DataCompass glossary        │
│   Pinterest: PinCat glossary terms + metric defs)   │
└─────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────┐
│  STEP 3 — QUERY MEMORY RETRIEVAL                    │
│  Top-K similar past Q→code pairs retrieved          │
│  and injected as few-shot examples                  │
│  (PayLens: QueryForge history                       │
│   Pinterest: unified context-intent embeddings)     │
└─────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────┐
│  STEP 4 — CODE GENERATION                           │
│  Claude Opus 4.6 (adaptive thinking)                │
│  generates pandas code + chart spec + explanation   │
└─────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────┐
│  STEP 5 — EXECUTE + RENDER                          │
│  pandas code runs against DataFrames                │
│  Plotly chart rendered in Streamlit UI              │
└─────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────┐
│  STEP 6 — SELF-REINFORCING LOOP                     │
│  Question + code saved to query history (SQLite)    │
│  Retrieved as examples for future similar questions │
│  (Pinterest: "your analysts already wrote the       │
│   perfect prompt")                                  │
└─────────────────────────────────────────────────────┘
```

---

## Datasets

1.47M rows across 4 tables, all from [McAuley-Lab/Amazon-Reviews-2023](https://huggingface.co/datasets/McAuley-Lab/Amazon-Reviews-2023).

| Table | Rows | Description |
|---|---|---|
| `beauty_reviews` | 701K | Customer reviews for Beauty products, 2000–2023 |
| `beauty_products` | 112K | Beauty product catalog — titles, ratings, prices, brands |
| `electronics_reviews` | 500K | Customer reviews for Electronics, 1998–2023 |
| `electronics_products` | 161K | Electronics product catalog — titles, ratings, prices, brands |

Tables join on `parent_asin`. Cross-table questions like *"Compare average ratings between Beauty and Electronics"* automatically join the right tables.

---

## Tech Stack

| Layer | Tech |
|---|---|
| Frontend | Streamlit |
| AI Engine | Claude Opus 4.6 (adaptive thinking) |
| Table Discovery | Claude-powered routing (`utils/table_selector.py`) |
| Schema Context | `catalog/tables.json` — column docs, caveats, join keys |
| Query Memory | SQLite + keyword scoring (`utils/query_memory.py`) |
| Visualization | Plotly Express |
| Data Format | Apache Parquet (via PyArrow) |
| Deploy | Streamlit Cloud |

---

## Run Locally

```bash
git clone https://github.com/satyapal07/ask-apd
cd ask-apd

python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Download all 4 datasets (~280 MB total, from HuggingFace)
python utils/download_sample.py

# Set your API key
cp .env.example .env
# Edit .env → ANTHROPIC_API_KEY=sk-ant-...

# Launch
streamlit run app.py
```

---

## Adding Your Own Tables

The app auto-discovers any table defined in `catalog/tables.json` that has a matching parquet file in `data/`. To add a new dataset:

**1. Drop your parquet file into `data/`**
```bash
data/my_table.parquet
```

**2. Add an entry to `catalog/tables.json`**
```json
"my_table": {
  "file": "data/my_table.parquet",
  "description": "One-sentence description shown in the sidebar.",
  "sample_questions": [
    "What is the distribution of X?",
    "Which Y has the most Z?"
  ],
  "columns": {
    "column_name": "Plain-English definition of what this column means and how to use it",
    "another_column": "Include units, value ranges, and any gotchas (e.g. null rate)"
  },
  "join_keys": {
    "other_table": "shared_column_name"
  },
  "data_caveats": [
    "Any known data quality issues Claude should know about"
  ]
}
```

**3. Restart the app** — it will pick up the new table automatically.

**Tips:**
- `columns` entries are injected verbatim into Claude's prompt — write them like you're briefing a junior analyst. The more business context, the better the queries.
- `data_caveats` suppresses bad queries before they happen (e.g. *"price has ~74% null rate — always dropna() first"*).
- `join_keys` tells Claude how to join across tables for cross-dataset questions.
- Any standard pandas-readable format works if you convert it to parquet first: `df.to_parquet("data/my_table.parquet", index=False)`.

---

## Deploy to Streamlit Cloud

1. Fork this repo on GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io) → connect the repo
3. Under **Advanced settings → Secrets**, add:
   ```
   ANTHROPIC_API_KEY = "sk-ant-..."
   ```
4. Click **Deploy**

> **Note:** Streamlit Cloud doesn't persist the `data/` folder between deploys. For a persistent cloud deployment, host the parquets on HuggingFace/S3 and fetch on startup.

---

## What Production Systems Do Beyond This

| Capability | Amazon Payments (PayLens) / Pinterest | Ask APD (This Project) |
|---|---|---|
| Scale | Thousands of tables, hundreds of analysts | 4 tables, single user |
| Retrieval | Vector embeddings over full query history | Keyword overlap over SQLite history |
| Documentation | AI-generated, propagated via join-based lineage | Hand-written `catalog/tables.json` |
| Governance | Table tiers, freshness tracking, owner metadata | Data caveats in catalog |
| Metric definitions | Centralized (TxnMetrics / PinCat glossary) | Column-level docs in catalog |
| Query output | SQL on Redshift / Spark | pandas in-memory |
| Infrastructure | Redshift, Spark, OpenSearch, Airflow | SQLite, local parquet files |

The core pipeline — intent understanding → context injection → few-shot retrieval → code generation → self-reinforcing loop — is the same. The infrastructure underneath scales differently.

---

*Pinterest Engineering independently published a similar architecture in [From Text-to-SQL to an Analytics Agent](https://medium.com/pinterest-engineering) — a useful read on how the same principles scale to 100,000+ tables.*
