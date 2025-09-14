#!/usr/bin/env python3
"""
Robust scraper for http://books.toscrape.com/

Improvements over original:
 - Uses response.url as base for joining relative links (fixes ../../../ links)
 - Logs full exceptions and stack traces
 - Does not crash on single page/product failure (continues and saves partial results)
 - Exponential backoff retry for requests
 - Safe partial JSON flush so progress isn't lost
 - Helpful debug curl instructions when a page can't be fetched
"""
import requests
from bs4 import BeautifulSoup
import time
import random
import json
import csv
import logging
import traceback
from urllib.parse import urljoin
from pathlib import Path
from tqdm import tqdm

# CONFIG
BASE = "http://books.toscrape.com/"
DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)
RAW_JSON = DATA_DIR / "raw_books.json"
RAW_CSV = DATA_DIR / "raw_books.csv"

HEADERS = {
    "User-Agent": "books-scraper-bot/1.0 (+https://example.com/contact) - learning only"
}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)


def get_soup_and_url(url, max_retries=4, backoff_factor=1.0, timeout=10):
    """
    Fetch a page and return (soup, final_url) or (None, None) on failure.
    Uses exponential backoff on retries.
    """
    delay = backoff_factor
    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=timeout)
            # Note: don't .raise_for_status() immediately - some sites return 403 etc.
            if resp.status_code != 200:
                logging.warning(f"Non-200 status {resp.status_code} for {url}")
                # still try a couple more times
            else:
                soup = BeautifulSoup(resp.text, "lxml")
                return soup, resp.url  # use resp.url as the base for joins
        except Exception as e:
            logging.warning(f"Request exception for {url}: {e} (attempt {attempt}/{max_retries})")
        time.sleep(delay * (1 + random.random()))
        delay *= 2  # exponential backoff
    logging.error(f"Failed to fetch {url} after {max_retries} attempts. Try: curl -I {url}")
    return None, None


def parse_list_item(article, page_base_url):
    """Extract brief listing info and product page absolute URL using page_base_url."""
    h3 = article.find("h3")
    a = h3.find("a")
    title = a.get("title", "").strip()
    relative_link = a.get("href", "")
    product_link = urljoin(page_base_url, relative_link)
    price_tag = article.find("p", class_="price_color")
    price = price_tag.text.strip() if price_tag else ""
    availability_tag = article.find("p", class_="instock availability")
    availability = availability_tag.text.strip() if availability_tag else ""
    rating_p = article.find("p", class_="star-rating")
    rating_class = rating_p.get("class", []) if rating_p else []
    rating = [c for c in rating_class if c != "star-rating"]
    rating = rating[0] if rating else ""
    img_tag = article.find("img")
    img_src = img_tag.get("src", "") if img_tag else ""
    img_url = urljoin(page_base_url, img_src)
    return {
        "title": title,
        "product_page_url": product_link,
        "price_text": price,
        "availability_text": availability,
        "rating_text": rating,
        "image_url": img_url
    }


def parse_product_page(product_url):
    """Return dict with category, description and product info table fields."""
    soup, final_url = get_soup_and_url(product_url)
    if soup is None:
        logging.error(f"Unable to fetch product page: {product_url}")
        return {}
    try:
        # category from breadcrumb - use text of 3rd breadcrumb item if present
        category = None
        breadcrumbs = soup.select("ul.breadcrumb li a")
        if len(breadcrumbs) >= 3:
            category = breadcrumbs[2].text.strip()

        desc = ""
        desc_tag = soup.select_one("#product_description")
        if desc_tag:
            p = desc_tag.find_next_sibling("p")
            if p:
                desc = p.text.strip()

        info = {}
        table = soup.find("table", class_="table table-striped")
        if table:
            for row in table.find_all("tr"):
                th = row.find("th").text.strip()
                td = row.find("td").text.strip()
                info[th] = td

        # return final_url as well (in case of redirects)
        return {"category": category, "description": desc, **info, "fetched_url": final_url}
    except Exception as e:
        logging.error("Error parsing product page %s: %s", product_url, e)
        logging.error(traceback.format_exc())
        return {}


def safe_write_json_partial(all_books):
    """Write partial results to JSON safely (atomic write)."""
    tmp = RAW_JSON.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(all_books, f, ensure_ascii=False, indent=2)
    tmp.replace(RAW_JSON)


def safe_write_csv(all_books):
    if not all_books:
        return
    keys = sorted({k for d in all_books for k in d.keys()})
    with open(RAW_CSV, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=keys)
        writer.writeheader()
        for row in all_books:
            writer.writerow(row)


def scrape_all(max_pages=1000):
    page = 1
    all_books = []
    logging.info("Starting scrape loop...")
    # Try to load existing partial results if present so we can resume
    if RAW_JSON.exists():
        try:
            with open(RAW_JSON, "r", encoding="utf-8") as f:
                all_books = json.load(f)
            logging.info(f"Loaded {len(all_books)} previously scraped items (resuming).")
        except Exception:
            logging.warning("Failed to load existing raw json - starting fresh.")

    while page <= max_pages:
        page_url = urljoin(BASE, f"catalogue/page-{page}.html")
        logging.info(f"Fetching page {page}: {page_url}")
        soup, page_final_url = get_soup_and_url(page_url)
        if soup is None:
            logging.warning(f"Stopping: could not fetch listing page {page_url}")
            break

        articles = soup.select("article.product_pod")
        if not articles:
            logging.info("No product pods on page - finishing pagination.")
            break

        for art in articles:
            try:
                item = parse_list_item(art, page_final_url or BASE)
                # Visit product page to enrich data (category, description, UPC)
                detail = parse_product_page(item["product_page_url"])
                item.update(detail)
                all_books.append(item)
                # polite pause between product page requests
                time.sleep(random.uniform(0.4, 1.2))
            except Exception as e:
                logging.error(f"Error while processing an article on page {page}: {e}")
                logging.error(traceback.format_exc())
            # persist partial progress every N items
            if len(all_books) % 20 == 0:
                safe_write_json_partial(all_books)

        page += 1
        # polite pause between pages
        time.sleep(random.uniform(0.8, 2.5))

    # final save
    safe_write_json_partial(all_books)
    safe_write_csv(all_books)
    logging.info(f"Scrape finished. Total items: {len(all_books)}")
    logging.info(f"Files written: {RAW_JSON} , {RAW_CSV}")


if __name__ == "__main__":
    try:
        scrape_all()
    except KeyboardInterrupt:
        logging.warning("Interrupted by user, saving partial results...")
        # if interrupted, ensure partial write
        if 'all_books' in locals():
            safe_write_json_partial(all_books)
            safe_write_csv(all_books)
        raise
