"""
Load data/raw_books.json, clean it, write:
 - data/books_clean.parquet
 - data/books.db (sqlite) with table 'books'
"""
import json
import re
from pathlib import Path
import pandas as pd
import sqlite3
import logging

DATA_DIR = Path("data")
RAW_JSON = DATA_DIR / "raw_books.json"
PARQUET_FILE = DATA_DIR / "books_clean.parquet"
DB_PATH = DATA_DIR / "books.db"

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

RATING_MAP = {
    "One": 1,
    "Two": 2,
    "Three": 3,
    "Four": 4,
    "Five": 5,
    "Zero": 0,
    "": None
}

def parse_price(price_text):
    """Convert price string like '£51.77' to float 51.77, or None if invalid."""
    if not price_text:
        return None
    m = re.search(r"[\d\.,]+", price_text)
    if not m:
        return None
    # Replace comma with empty (if any) then float
    return float(m.group(0).replace(",", ""))

def parse_availability(avail_text):
    """Extract number of available items from string like 'In stock (22 available)'."""
    if not avail_text:
        return None
    m = re.search(r"(\d+)", avail_text)
    if m:
        return int(m.group(1))
    return 0  # Assume 0 if not found

def rating_word_to_int(rating_word):
    """Convert rating word like 'Three' to integer 3."""
    return RATING_MAP.get(rating_word, None)

def clean_data(df):
    """Clean and transform the DataFrame."""
    logging.info("Cleaning data...")

    # Price
    df['price'] = df['price_text'].apply(parse_price)

    # Availability
    df['availability'] = df["availability_text"].apply(parse_availability)

    # Rating
    df['rating'] = df['rating_text'].apply(rating_word_to_int)

    # Lowercase title, strip whitespace
    df['title'] = df['title'].astype(str).str.strip().str.lower()

    # Ensure product_page_url exists
    df = df.dropna(subset=['product_page_url'])

    # Deduplicate by product_page_url
    df = df.drop_duplicates(subset=['product_page_url'])

    # Rearrange columns and fill missing category
    cols = ["title", "product_page_url", "category", "price", "availability", "rating", "description", "image_url"]
    existing_cols = [col for col in cols if col in df.columns]
    df = df[existing_cols].reset_index(drop=True)
    return df

def main():
    logging.info("Loading raw JSON data...")
    with open(RAW_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)

    df = pd.DataFrame(data)
    logging.info(f"Loaded {len(df)} records.")

    df_clean = clean_data(df)
    logging.info(f"Cleaned data has {len(df_clean)} records.")

    try:
        logging.info(f"Saving cleaned data to {PARQUET_FILE}...")
        df_clean.to_parquet(PARQUET_FILE, index=False)
        logging.info(f"Wrote cleaned parquet to {PARQUET_FILE}")
    except Exception as e:
        logging.warning(f"Error saving parquet file: ({e}), Saving as CSV instead.")
        df_clean.to_csv(DATA_DIR / "books_clean.csv", index=False)

    #Write to SQLite
    logging.info(f"Writing data to SQLite database at {DB_PATH}...")
    conn = sqlite3.connect(DB_PATH)
    df_clean.to_sql("books", conn, if_exists="replace", index=False)

    cur = conn.cursor()
    cur.execute("CREATE INDEX IF NOT EXISTS idx_category ON books(category)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_price ON books(price)")
    conn.commit()
    conn.close()
    logging.info("DataLoad complete.")

if __name__ == "__main__":
    main()
    