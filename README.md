# 🔍 Ask APD — Natural Language Data Explorer

> Ask questions about large datasets in plain English. Get instant answers + visualizations.

**[🚀 Live Demo →](https://satyapal07-ask-apd.streamlit.app)** *(coming soon)*

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

## Inspired by Pinterest's Analytics Agent

This project is a portable, open-source implementation of the architecture Pinterest Engineering described in [*From Text-to-SQL to an Analytics Agent*](https://medium.com/pinterest-engineering).

Pinterest's production system serves **2,500+ analysts** across **100,000+ analytical tables**. Their key insight: simple keyword matching and table summaries aren't enough at scale. When an analyst asks *"What's the engagement rate for organic content by country?"*, they need the system to understand **analytical intent** — the business question behind the query — not just surface tables with similar names.

They solved this with two engineering choices:

1. **Unified context-intent embeddings** — Transform historical analyst queries into semantically rich representations that capture *what business question a query was designed to answer*, not raw SQL syntax. This enables retrieval that understands meaning, not keywords.
2. **Structural & statistical patterns with governance-aware ranking** — Extract validated join keys, filters, and aggregation logic from query history, combined with governance metadata (table tiers, freshness, documentation quality) to surface not just relevant tables, but *trustworthy* ones.

The result is **self-reinforcing**: every query an analyst writes enriches the knowledge base, making the system better for the next analyst. In effect, the combined expertise of 2,500 analysts becomes accessible to everyone rather than siloed within teams.

---

## How This Project Maps to Pinterest's Architecture

| Pinterest (Production) | Ask APD (This Project) |
|---|---|
| 100,000+ warehouse tables | 4 Amazon dataset tables |
| PinCat data catalog (built on DataHub) | `catalog/tables.json` — column docs, caveats, join keys |
| Table discovery via vector embeddings over query history | Claude-powered table selector routing questions to relevant tables |
| Domain context injection (glossary terms, metric definitions) | Column-level business definitions + data caveats injected per query |
| SQL→text pipeline: summary + analytical questions + breakdown | Claude generates pandas code + chart spec + plain-English explanation |
| Query history as few-shot knowledge base | SQLite query memory — past Q→code pairs injected as examples |
| Governance-aware ranking (table tiers, freshness) | `catalog/tables.json` data caveats flag unreliable columns |
| Self-reinforcing learning cycle | Every successful answer saved to query history |
| Vector DB as a Service (OpenSearch + Airflow) | SQLite + keyword scoring (swap in ChromaDB/FAISS to scale) |
| AI-generated table & column documentation | Column docs written once in `catalog/tables.json` |

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
│  (Pinterest: vector search over 100K tables)        │
└─────────────────────────────────────────────────────┘
     │  selected tables: e.g. ["beauty_reviews",
     │                          "beauty_products"]
     ▼
┌─────────────────────────────────────────────────────┐
│  STEP 2 — DOMAIN CONTEXT INJECTION                  │
│  Column definitions, data caveats, join keys        │
│  injected from catalog/tables.json                  │
│  (Pinterest: PinCat glossary terms, metric defs)    │
└─────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────┐
│  STEP 3 — QUERY MEMORY RETRIEVAL                    │
│  Top-K similar past Q→code pairs retrieved          │
│  and injected as few-shot examples                  │
│  (Pinterest: unified context-intent embeddings)     │
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

## What Pinterest's Production System Does Beyond This

| Capability | Pinterest | This Project |
|---|---|---|
| Scale | 100K tables, 2,500 analysts | 4 tables, single user |
| Retrieval | Vector embeddings (OpenSearch) over 400K+ indexed queries | Keyword overlap over SQLite history |
| Documentation | AI-generated, propagated via join-based lineage (40% manual effort saved) | Hand-written `catalog/tables.json` |
| Governance | Table tiers, freshness tracking, owner metadata | Data caveats in catalog |
| Query output | SQL (runs on data warehouse) | pandas (runs in-memory) |
| Infrastructure | OpenSearch vector DB, Airflow DAGs, PinCat | SQLite, local files |

The core pipeline — intent understanding → context injection → few-shot retrieval → code generation → self-reinforcing loop — is the same. The infrastructure underneath scales differently.

---

## Background

Inspired by internal data tooling from Amazon's APD team.
Rebuilt as an open-source implementation of the Pinterest Analytics Agent architecture, using real Amazon review data.

Architecture reference: [*From Text-to-SQL to an Analytics Agent*](https://medium.com/pinterest-engineering), Pinterest Engineering Blog.
