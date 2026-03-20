"""
Download all datasets for Ask APD from HuggingFace.

Downloads 4 tables from McAuley-Lab/Amazon-Reviews-2023:
  - beauty_reviews.parquet     (701K rows, ~143 MB)
  - beauty_products.parquet    (112K rows, ~10 MB)
  - electronics_reviews.parquet (500K rows, ~110 MB)
  - electronics_products.parquet (161K rows, ~18 MB)

Run: python utils/download_sample.py
"""

import os
import io
import json
import requests
import pandas as pd

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
os.makedirs(DATA_DIR, exist_ok=True)

HF_BASE = "https://huggingface.co/datasets/McAuley-Lab/Amazon-Reviews-2023/resolve/main"


def _download_parquet(url: str, label: str) -> pd.DataFrame:
    print(f"Downloading {label}...")
    r = requests.get(url, stream=True, timeout=300)
    r.raise_for_status()
    data = b""
    total = 0
    for chunk in r.iter_content(4 * 1024 * 1024):
        data += chunk
        total += len(chunk)
        print(f"  {total / 1e6:.0f} MB", end="\r")
    print()
    return pd.read_parquet(io.BytesIO(data))


def _download_reviews_jsonl(url: str, label: str, max_rows: int) -> pd.DataFrame:
    print(f"Downloading {label} (first {max_rows:,} rows)...")
    rows = []
    buf = b""
    total_bytes = 0
    r = requests.get(url, stream=True, timeout=300)
    r.raise_for_status()
    for chunk in r.iter_content(chunk_size=4 * 1024 * 1024):
        total_bytes += len(chunk)
        buf += chunk
        lines = buf.split(b"\n")
        buf = lines[-1]
        for line in lines[:-1]:
            line = line.strip()
            if line:
                try:
                    rows.append(json.loads(line))
                except Exception:
                    pass
        print(f"  {total_bytes / 1e6:.0f} MB → {len(rows):,} rows", end="\r")
        if len(rows) >= max_rows:
            r.close()
            break
    print()
    return pd.DataFrame(rows[:max_rows])


def _clean_reviews(df: pd.DataFrame) -> pd.DataFrame:
    df["review_date"]    = pd.to_datetime(df["timestamp"], unit="ms")
    df["review_year"]    = df["review_date"].dt.year
    df["review_month"]   = df["review_date"].dt.month
    df["review_quarter"] = df["review_date"].dt.quarter
    df = df.rename(columns={
        "rating":       "star_rating",
        "title":        "review_title",
        "text":         "review_text",
        "helpful_vote": "helpful_votes",
    })
    df["review_length"] = df["review_text"].fillna("").str.len()
    df = df.drop(columns=["images", "user_id", "timestamp", "asin"], errors="ignore")
    cols = [
        "review_date", "review_year", "review_month", "review_quarter",
        "star_rating", "review_title", "review_text", "review_length",
        "helpful_votes", "verified_purchase", "parent_asin",
    ]
    return df[[c for c in cols if c in df.columns]]


def _clean_products(df: pd.DataFrame) -> pd.DataFrame:
    keep = ["parent_asin", "title", "main_category", "average_rating",
            "rating_number", "price", "store", "categories"]
    df = df[[c for c in keep if c in df.columns]].copy()
    df = df.rename(columns={"title": "product_title", "store": "brand"})
    df["price"] = df["price"].astype(str).str.replace(r"[^\d.]", "", regex=True)
    df["price"] = pd.to_numeric(df["price"], errors="coerce")
    return df.dropna(subset=["product_title"])


def download_beauty_reviews():
    out = os.path.join(DATA_DIR, "beauty_reviews.parquet")
    if os.path.exists(out):
        print(f"  beauty_reviews.parquet already exists, skipping.")
        return
    url = f"{HF_BASE}/raw/review_categories/All_Beauty.jsonl"
    df = _download_reviews_jsonl(url, "beauty_reviews", max_rows=701_528)
    df = _clean_reviews(df)
    df.to_parquet(out, index=False)
    print(f"  Saved beauty_reviews.parquet — {len(df):,} rows ({os.path.getsize(out)/1e6:.0f} MB)")


def download_beauty_products():
    out = os.path.join(DATA_DIR, "beauty_products.parquet")
    if os.path.exists(out):
        print(f"  beauty_products.parquet already exists, skipping.")
        return
    url = f"{HF_BASE}/raw_meta_All_Beauty/full-00000-of-00001.parquet"
    df = _download_parquet(url, "beauty_products")
    df = _clean_products(df)
    df.to_parquet(out, index=False)
    print(f"  Saved beauty_products.parquet — {len(df):,} rows ({os.path.getsize(out)/1e6:.0f} MB)")


def download_electronics_reviews():
    out = os.path.join(DATA_DIR, "electronics_reviews.parquet")
    if os.path.exists(out):
        print(f"  electronics_reviews.parquet already exists, skipping.")
        return
    url = f"{HF_BASE}/raw/review_categories/Electronics.jsonl"
    df = _download_reviews_jsonl(url, "electronics_reviews", max_rows=500_000)
    df = _clean_reviews(df)
    df.to_parquet(out, index=False)
    print(f"  Saved electronics_reviews.parquet — {len(df):,} rows ({os.path.getsize(out)/1e6:.0f} MB)")


def download_electronics_products():
    out = os.path.join(DATA_DIR, "electronics_products.parquet")
    if os.path.exists(out):
        print(f"  electronics_products.parquet already exists, skipping.")
        return
    url = f"{HF_BASE}/raw_meta_Electronics/full-00000-of-00010.parquet"
    df = _download_parquet(url, "electronics_products")
    df = _clean_products(df)
    df.to_parquet(out, index=False)
    print(f"  Saved electronics_products.parquet — {len(df):,} rows ({os.path.getsize(out)/1e6:.0f} MB)")


if __name__ == "__main__":
    print("=" * 55)
    print("Ask APD — Dataset Downloader")
    print("Source: McAuley-Lab/Amazon-Reviews-2023 (HuggingFace)")
    print("=" * 55)
    print()

    download_beauty_products()
    download_beauty_reviews()
    download_electronics_products()
    download_electronics_reviews()

    print()
    print("All datasets ready. Run the app with:")
    print("  streamlit run app.py")
