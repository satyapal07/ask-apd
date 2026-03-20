# 🔍 Ask APD — Natural Language Data Explorer

> Ask questions about large datasets in plain English. Get instant answers + visualizations.

**[🚀 Live Demo →](https://your-app.streamlit.app)** *(add after deploying)*

## What It Does

Type any question → get a data-driven answer with auto-generated charts.

**Example queries:**
- "What are the top 10 highest-rated product categories?"
- "Show me review volume trends over time"
- "Which products have the most helpful reviews?"
- "What is the average rating by category?"
- "Show the distribution of star ratings"

## Tech Stack

| Layer | Tech |
|---|---|
| Frontend | Streamlit |
| AI Engine | Claude Opus 4.6 (Anthropic API) |
| Data | Amazon Reviews 2023 / synthetic sample |
| Viz | Plotly Express |
| Deploy | Streamlit Cloud |

## Architecture

```
User Question
     ↓
Claude Opus 4.6 (adaptive thinking)
     ↓ generates pandas code + chart spec
Execute pandas code against DataFrame
     ↓
Plotly chart + plain-English answer
```

## Run Locally

```bash
git clone https://github.com/yourname/ask-apd
cd ask-apd

python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Set your API key
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY

# Generate the sample dataset
python utils/download_sample.py

# Launch
streamlit run app.py
```

## Using Real Amazon Data (2M+ rows)

```bash
pip install datasets
python -c "
from datasets import load_dataset
ds = load_dataset('McAuley-Lab/Amazon-Reviews-2023',
                  'raw_review_All_Beauty',
                  trust_remote_code=True)
ds['full'].to_parquet('data/sample.parquet')
"
```

## Deploy to Streamlit Cloud

1. Push repo to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io) → Connect repo
3. Add `ANTHROPIC_API_KEY` in Streamlit's Secrets manager
4. Click Deploy → get a `yourname-ask-apd.streamlit.app` URL

## Background

Inspired by internal data tooling from Amazon's APD team.
Rebuilt as an open-source, publicly deployable version using real e-commerce data.
