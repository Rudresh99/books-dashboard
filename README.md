# 📚 Books ETL Pipeline & Dashboard

![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python)
![Streamlit](https://img.shields.io/badge/Streamlit-Dashboard-red?logo=streamlit)
![Pandas](https://img.shields.io/badge/Pandas-ETL-green?logo=pandas)
![SQLite](https://img.shields.io/badge/SQLite-Database-lightgrey?logo=sqlite)
![BeautifulSoup](https://img.shields.io/badge/Web%20Scraping-BeautifulSoup-yellow)

## 🚀 Project Overview
This project demonstrates an **end-to-end ETL (Extract → Transform → Load) pipeline** combined with a **data visualization dashboard**.  
It uses data from [Books to Scrape](http://books.toscrape.com), a public test website for practicing web scraping.

The project showcases:
- ✅ Web scraping using `requests` & `BeautifulSoup`
- ✅ Data transformation with `pandas`
- ✅ Storage in both **SQLite** and **Parquet**
- ✅ Interactive dashboard using **Streamlit** + **Plotly**
- ✅ Clean project structure, virtual environment, and version control (Git/GitHub)

---


## ⚙️ Tech Stack

- **Language:** Python 3.10+
- **Libraries:** 
  - Web Scraping → `requests`, `beautifulsoup4`, `lxml`
  - ETL & Storage → `pandas`, `pyarrow`, `sqlalchemy`, `sqlite3`
  - Visualization → `streamlit`, `plotly`, `altair`
- **Database:** SQLite (lightweight, file-based DB)
- **Dashboard:** Streamlit (interactive web UI)

---

## 🔄 ETL Workflow

1. **Extract (scrape.py)**
   - Scrapes book details (title, price, stock, rating, category) from multiple pages.
   - Saves raw data as JSON & CSV.

2. **Transform & Load (transform_and_load.py)**
   - Cleans data (price → numeric, rating → integer).
   - Stores data in **Parquet** format (for analytics).
   - Loads structured data into an **SQLite database**.

3. **Visualize (dashboard.py)**
   - Reads processed data.
   - Interactive dashboard with:
     - Category distribution of books
     - Top 10 most expensive books
     - Stock availability visualization

---

## ▶️ How to Run Locally (Mac/Windows/Linux)

1. **Clone Repo**
   ```bash
   git clone https://github.com/<your-username>/books-dashboard.git
   cd books-dashboard

👨‍💻 Author

Rudresh – Data Engineer Enthusiast

📧 rudreshjoshi99@gmail.com
