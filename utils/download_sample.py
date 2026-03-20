"""
Download a small sample dataset for Ask APD.

Options:
  A) Amazon Reviews via HuggingFace (requires: pip install datasets)
  B) Brazilian E-Commerce via Kaggle (requires: pip install kaggle + kaggle.json)
  C) Built-in synthetic sample (no dependencies)

Run: python utils/download_sample.py
"""

import os
import pandas as pd
import numpy as np

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
os.makedirs(DATA_DIR, exist_ok=True)


def generate_synthetic_sample(n: int = 5000) -> pd.DataFrame:
    """Generate a realistic synthetic e-commerce review dataset."""
    rng = np.random.default_rng(42)

    categories = [
        "Electronics", "Books", "Clothing", "Home & Kitchen",
        "Sports", "Beauty", "Toys", "Automotive", "Music", "Health",
    ]
    products = {
        "Electronics": ["Laptop", "Phone", "Headphones", "Camera", "Tablet"],
        "Books": ["Fiction Novel", "Cookbook", "Self-Help", "Biography", "Textbook"],
        "Clothing": ["T-Shirt", "Jeans", "Jacket", "Sneakers", "Dress"],
        "Home & Kitchen": ["Coffee Maker", "Blender", "Pan Set", "Knife Set", "Vacuum"],
        "Sports": ["Yoga Mat", "Dumbbells", "Running Shoes", "Bike Helmet", "Tennis Racket"],
        "Beauty": ["Moisturizer", "Lipstick", "Shampoo", "Perfume", "Foundation"],
        "Toys": ["LEGO Set", "Board Game", "Action Figure", "Puzzle", "Remote Car"],
        "Automotive": ["Car Cover", "Phone Mount", "Dash Cam", "Floor Mats", "Jump Starter"],
        "Music": ["Guitar", "Ukulele", "Keyboard", "Drum Pad", "Microphone"],
        "Health": ["Vitamins", "Protein Powder", "Blood Pressure Monitor", "Scale", "Thermometer"],
    }

    rows = []
    start_date = pd.Timestamp("2020-01-01")
    end_date = pd.Timestamp("2024-12-31")
    date_range = int((end_date - start_date).days)

    for _ in range(n):
        category = rng.choice(categories)
        product = rng.choice(products[category])
        rating = rng.choice([1, 2, 3, 4, 5], p=[0.05, 0.08, 0.12, 0.30, 0.45])
        helpful_votes = int(rng.exponential(5))
        total_votes = helpful_votes + int(rng.exponential(2))
        review_date = start_date + pd.Timedelta(days=int(rng.integers(0, date_range)))

        rows.append({
            "product_id": f"B{rng.integers(1000000, 9999999):07d}",
            "product_name": product,
            "category": category,
            "rating": rating,
            "helpful_votes": helpful_votes,
            "total_votes": total_votes,
            "verified_purchase": rng.choice([True, False], p=[0.75, 0.25]),
            "review_date": review_date,
            "review_year": review_date.year,
            "review_month": review_date.month,
            "review_length": int(rng.integers(20, 800)),
            "price": round(float(rng.uniform(5, 500)), 2),
        })

    df = pd.DataFrame(rows)
    df["review_date"] = pd.to_datetime(df["review_date"])
    return df


if __name__ == "__main__":
    out_path = os.path.join(DATA_DIR, "sample.parquet")

    print("Generating synthetic e-commerce dataset (5,000 rows)...")
    df = generate_synthetic_sample(5000)
    df.to_parquet(out_path, index=False)
    print(f"Saved to {out_path}")
    print(f"Shape: {df.shape}")
    print(f"Columns: {list(df.columns)}")
    print("\nSample:")
    print(df.head(3))

    print("\nTo use Amazon Reviews instead (2M+ rows), run:")
    print("  pip install datasets")
    print("  python -c \"")
    print("  from datasets import load_dataset")
    print("  ds = load_dataset('McAuley-Lab/Amazon-Reviews-2023',")
    print("                    'raw_review_All_Beauty', trust_remote_code=True)")
    print(f"  ds['full'].to_parquet('{out_path}')")
    print("  \"")
