"""
Streamlit dashboard to explore the cleaned books dataset.
Run: streamlit run dashboard.py
"""
import pathlib
import streamlit as st
import pandas as pd
import sqlite3
import altair as alt
from pathlib import Path

DATA_DIR = Path("data")
PARQUET_FILE = DATA_DIR / "books_clean.parquet"
DB_PATH = DATA_DIR / "books.db"

st.set_page_config(layout="wide", page_title="Books Dashboard")
@st.cache_data(ttl=600)

def load_data():
    """Load cleaned data from Parquet or SQLite database."""
    # Prefer parquet if available, else read from sqlite
    if PARQUET_FILE.exists():
        df = pd.read_parquet(PARQUET_FILE)
    elif DB_PATH.exists():
        conn = sqlite3.connect(DB_PATH)
        df = pd.read_sql("SELECT * FROM books", conn)
        conn.close()
    
    df["category"] = df['category'].fillna("Unknown")
    df['price'] = pd.to_numeric(df['price'], errors='coerce')
    df['rating'] = pd.to_numeric(df['rating'], errors='coerce')
    return df

df = load_data()

# Sidebar - filters
st.sidebar.header("Filters")
categories = sorted(df["category"].dropna().unique())
selected_cats = st.sidebar.multiselect("Category", categories, default=categories[:6])
min_price, max_price = float(df["price"].min()), float(df["price"].max())
price_range = st.sidebar.slider("Price range", min_price, max_price, (min_price, max_price))
min_rating = int(df["rating"].min()) if df["rating"].notnull().any() else 0
max_rating = int(df["rating"].max()) if df["rating"].notnull().any() else 5
rating_select = st.sidebar.slider("Min rating", min_rating, max_rating, min_rating)

# Apply filters
filtered = df[
    (df["category"].isin(selected_cats)) &
    (df["price"].between(price_range[0], price_range[1])) &
    (df["rating"] >= rating_select)
].copy()

# Top metrics
col1, col2, col3 = st.columns(3)
col1.metric("Books in view", len(filtered))
col2.metric("Avg price", f"£{filtered['price'].mean():.2f}" if not filtered.empty else "N/A")
col3.metric("Avg rating", f"{filtered['rating'].mean():.2f}" if not filtered.empty else "N/A")

# Charts
st.markdown("### Average price by category")
avg_by_cat = filtered.groupby("category", as_index=False)["price"].mean().sort_values("price", ascending=False)
bar = alt.Chart(avg_by_cat).mark_bar().encode(
    x=alt.X("price:Q", title="Average Price"),
    y=alt.Y("category:N", sort="-x", title="Category"),
    tooltip=["category", alt.Tooltip("price", format=".2f")]
).properties(height=400)
st.altair_chart(bar, use_container_width=True)

st.markdown("### Price distribution")
hist = alt.Chart(filtered).mark_bar().encode(
    alt.X("price:Q", bin=alt.Bin(maxbins=40)),
    y='count()',
    tooltip=[alt.Tooltip("count()", title="Count")]
).properties(height=250)
st.altair_chart(hist, use_container_width=True)

st.markdown("### Books table (first 200 rows)")
st.dataframe(filtered.head(200))

# Option: show book images and links for first N items
st.markdown("### Sample books")
for idx, row in filtered.head(10).iterrows():
    cols = st.columns([1, 6])
    with cols[0]:
        if pd.notna(row.get("image_url")):
            st.image(row["image_url"], width=80)
    with cols[1]:
        st.write(f"**{row['title']}**")
        st.write(f"Category: {row.get('category','')}, Price: £{row.get('price')}, Rating: {row.get('rating')}")
        st.write(f"[Product page]({row.get('product_page_url')})")

st.markdown("---")
st.caption("Data source: books.toscrape.com (practice site).")
