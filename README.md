# 🔍 Ask APD — Natural Language Data Explorer

> Ask questions about large datasets in plain English. Get instant answers + visualizations.

**[🚀 Live Demo →](https://satyapal07-ask-apd.streamlit.app)** *(coming soon)*

## What It Does

Type any question → Claude picks the right tables → runs pandas → returns a chart + plain-English answer.

**Example queries:**
- "Compare average star ratings: Beauty vs Electronics"
- "Which beauty brands have the most products?"
- "Show electronics review volume growth over time"
- "Which products have the most helpful votes?"
- "What's the price distribution of electronics products?"

## Architecture

Inspired by [how Pinterest built their Analytics Agent](https://medium.com/pinterest-engineering) — evolved from basic Text-to-SQL to a multi-table pipeline with table discovery, schema-grounded context, and a self-reinforcing query memory.

```
User Question
     ↓
Table Selector  — Claude routes to relevant table(s) from the catalog
     ↓
Schema Context  — column docs, data caveats, join keys injected (catalog/tables.json)
     ↓
Query Memory    — similar past Q→code pairs injected as few-shot examples
     ↓
Claude Opus 4.6 (adaptive thinking) — generates pandas code + chart spec
     ↓
Execute → Plotly chart + plain-English answer
     ↓
Save to query history  — self-reinforcing loop, every answer improves the next
```

## Datasets

| Table | Rows | Source |
|---|---|---|
| `beauty_reviews` | 701K | Amazon Beauty reviews 2000–2023 |
| `beauty_products` | 112K | Amazon Beauty product catalog |
| `electronics_reviews` | 500K | Amazon Electronics reviews 1998–2023 |
| `electronics_products` | 161K | Amazon Electronics product catalog |

All data from [McAuley-Lab/Amazon-Reviews-2023](https://huggingface.co/datasets/McAuley-Lab/Amazon-Reviews-2023) on HuggingFace.

## Tech Stack

| Layer | Tech |
|---|---|
| Frontend | Streamlit |
| AI Engine | Claude Opus 4.6 (adaptive thinking) |
| Table Discovery | Claude-powered routing + `catalog/tables.json` |
| Query Memory | SQLite (few-shot self-reinforcing loop) |
| Viz | Plotly Express |
| Deploy | Streamlit Cloud |

## Run Locally

```bash
git clone https://github.com/satyapal07/ask-apd
cd ask-apd

python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Download all 4 datasets (~280 MB total)
python utils/download_sample.py

# Set your API key
cp .env.example .env
# Edit .env → add ANTHROPIC_API_KEY=sk-ant-...

# Launch
streamlit run app.py
```

## Deploy to Streamlit Cloud

1. Fork this repo on GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io) → connect the repo
3. Under **Advanced settings → Secrets**, add:
   ```
   ANTHROPIC_API_KEY = "sk-ant-..."
   ```
4. Click **Deploy**

> Note: Streamlit Cloud doesn't persist the `data/` folder between deploys. Add a startup script or host the parquets on HuggingFace/S3 for production use.

## Background

Inspired by internal data tooling from Amazon's APD team.
Rebuilt as an open-source, publicly deployable version using real Amazon review data.
