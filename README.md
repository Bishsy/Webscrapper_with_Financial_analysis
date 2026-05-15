"# Webscrapper_with_Financial_analysis" 
# 🇮🇳 Indian Stock Market Scraper & Sector Analyzer

<div align="center">

![Python](https://img.shields.io/badge/Python-3.9%2B-blue?style=for-the-badge&logo=python)
![Pandas](https://img.shields.io/badge/Pandas-2.0%2B-150458?style=for-the-badge&logo=pandas)
![Rich](https://img.shields.io/badge/Rich-Terminal-green?style=for-the-badge)
![License](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)
![Status](https://img.shields.io/badge/Status-Active-brightgreen?style=for-the-badge)

**A comprehensive Python-based stock market data platform for Indian equity markets.**  
Scrapes, analyses, filters, and visualises data across all 11 GICS sectors  
with 13 financial metrics and benchmark ratings.

[Features](#features) • [Installation](#installation) • [Usage](#usage) •
[Architecture](#architecture) • [Screenshots](#screenshots) •
[Contributing](#contributing)

</div>

---

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Project Structure](#project-structure)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Usage Guide](#usage-guide)
- [Data Sources](#data-sources)
- [Financial Metrics](#financial-metrics)
- [Sector Coverage](#sector-coverage)
- [Output Files](#output-files)
- [Configuration](#configuration)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
  

---

## 🌐 Overview

The **Indian Stock Market Scraper** is a fully-featured terminal application
that collects live and historical financial data for Indian stocks listed on
**NSE (National Stock Exchange)** and **BSE (Bombay Stock Exchange)**.

It covers **147 companies** across **11 GICS sectors**, scrapes
**13 key financial metrics** from Screener.in, applies intelligent
benchmark ratings, and exports colour-coded Excel reports.

### What makes this different?

| Feature | This Tool |
|---|---|
| Data Sources | NSE API + Yahoo Finance + Screener.in |
| Sectors | All 11 GICS sectors |
| Companies | 147 pre-loaded + custom symbols |
| Metrics | 13 financial KPIs with benchmarks |
| Filters | 16 filter types (price, sector, date, custom) |
| Charts | 18 chart types (bar, pie, DMA, heatmap, scatter) |
| Export | Multi-sheet colour-coded Excel |
| Interface | Rich terminal UI (no web browser needed) |

---

## ✨ Features

### 📊 Data Collection
- ✅ **Live prices** from NSE India official API
- ✅ **Financial statements** from Screener.in (P&L, Balance Sheet, Cash Flow)
- ✅ **Index data** — NIFTY 50, SENSEX, NIFTY BANK, and 130+ indices
- ✅ **Top Gainers & Losers** from NSE
- ✅ **robots.txt compliance** and polite rate limiting
- ✅ **Automatic retry** on network failures

### 🏭 Sector Analysis
- ✅ **11 GICS Sectors** with 50 top companies each
- ✅ **Price range filters** — Top High 50 / Top Low 50 / Custom Range
- ✅ **13 financial metrics** with sector-specific benchmarks
- ✅ **3 years of historical** Revenue, EBITDA, PAT, FCF
- ✅ **Side-by-side sector comparison**
- ✅ **Sector leaderboards** (best company per metric)

### 🔍 Filter Studio (16 Filters)
| # | Filter | Description |
|---|---|---|
| 1 | Price Range | ₹min ≤ price ≤ ₹max |
| 2 | % Change | Filter by daily change |
| 3 | Volume | Filter by traded volume |
| 4 | Category | Index / Gainer / Loser / Watchlist |
| 5 | Source | Yahoo / NSE / MoneyControl |
| 6 | Symbol Search | Partial text or regex |
| 7 | Sector | IT / Banking / FMCG etc. |
| 8 | Date Range | Today / 7d / 30d / Custom |
| 9 | Top N | Top N by any column |
| 10 | Bottom N | Bottom N by any column |
| 11 | Positive Change | Gainers only |
| 12 | Negative Change | Losers only |
| 13 | Near 52W High | Within X% of yearly high |
| 14 | Near 52W Low | Within X% of yearly low |
| 15 | Custom Expression | Pandas query string |
| 16 | Multi-Column Sort | Sort by 1–N columns |

### 📈 Visualisation (18 Charts)
- Bar charts (gainers/losers, sector avg, revenue vs PAT)
- Pie & Donut charts (sector distribution, market breadth)
- Heatmaps (sector-stock change, correlation matrix)
- Scatter plots (price vs change, revenue vs PAT)
- DMA charts (5/10/20-day moving averages + crossover signals)
- Waterfall chart (PAT contribution)
- Full market dashboard (6-panel overview)

### 💾 Excel Export
- Multi-sheet workbook with colour-coded cells
- Green/Yellow/Red benchmark colour coding
- Auto-filter and freeze panes on all sheets
- Benchmark legend sheet included
- Append mode for continuous data tracking

---

## 📁 Project Structure

```
indian_stock_scraper/
│
├── 📄 main.py                  # Application entry point
├── 📄 config.py                # Central configuration
├── 📄 logger_setup.py          # Rotating file + console logger
│
├── 📄 scraper.py               # Multi-source price scraper
│   ├── NSEScraper              # NSE India official API
│   ├── YahooScraper            # Yahoo Finance (indices + stocks)
│   └── StooqScraper            # Stooq CSV fallback
│
├── 📄 financial_scraper.py     # Screener.in financial data
│   ├── ScreenerSession         # Session + cookie management
│   ├── ScreenerTableParser     # HTML table parser
│   ├── ScreenerRatioParser     # top-ratios extractor
│   └── ScreenerFinancialScraper # Master scraper (13 metrics)
│
├── 📄 sector_data.py           # 11 sectors × 50 companies database
│   ├── SECTOR_COMPANIES        # 147 companies with metadata
│   ├── METRIC_BENCHMARKS       # Benchmark thresholds (13 metrics)
│   └── SECTOR_PE_BENCHMARKS    # Sector-specific P/E benchmarks
│
├── 📄 sector_scraper.py        # Sector-level scraping orchestrator
├── 📄 sector_analyzer.py       # Metrics computation + display + Excel
├── 📄 sector_ui.py             # Interactive sector analysis UI
│
├── 📄 company_data.py          # Nifty50 / Midcap / Smallcap lists
├── 📄 company_selector.py      # Interactive company picker UI
│
├── 📄 filters.py               # 16 filter classes + FilterPipeline
├── 📄 filter_ui.py             # Interactive filter studio UI
│
├── 📄 data_manager.py          # DataFrame ↔ Excel I/O
├── 📄 visualizer.py            # 18 chart types (matplotlib + seaborn)
│
├── 📄 diagnose.py              # Network diagnostic tool
├── 📄 diagnose_screener.py     # Screener.in diagnostic tool
│
├── 📄 requirements.txt
├── 📄 README.md
│
├── 📁 output/
│   ├── indian_stocks_data.xlsx
│   ├── filter_presets.json
│   ├── 📁 sectors/
│   │   └── Financials_20240115.xlsx
│   └── 📁 charts/
│       ├── 01_dashboard_20240115.png
│       └── ...
│
└── 📁 logs/
    └── scraper.log
```

---

## 🛠 Installation

### Prerequisites
- Python 3.9 or higher
- Windows / macOS / Linux
- Internet connection

### Step 1 — Clone or Download

```bash
# Option A: Git clone
git clone https://github.com/yourname/indian-stock-scraper.git
cd indian-stock-scraper

# Option B: Download ZIP and extract
cd "Indian Stock Market Scraper"
```

### Step 2 — Create Virtual Environment

```bash
# Windows CMD (recommended — avoids PowerShell policy issues)
python -m venv venv
venv\Scripts\activate.bat

# Windows PowerShell (if needed)
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
venv\Scripts\Activate.ps1

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

### Step 3 — Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### Step 4 — Verify Installation

```bash
python -c "import requests, pandas, rich, bs4, openpyxl; print('All OK!')"
python config.py
```

---

## 🚀 Quick Start

```bash
# Run the application
python main.py
```

```
╔══════════════════════════════════════════════════════╗
║   🇮🇳  Indian Stock Market Scraper  📈               ║
║   Sources: Yahoo Finance · NSE API · MoneyControl    ║
║   Sectors: 11 GICS | Companies: 147 | Metrics: 13   ║
╚══════════════════════════════════════════════════════╝

Main Menu
  1  🏢 Select companies & Scrape data
  2  📂 Load existing data from Excel
  3  🔍 Open Filter Studio
  4  📋 View data table
  5  📊 View statistics
  6  💾 Save all data to Excel
  7  📈 Visualization Studio
  S  🏭 Sector Analysis Studio
  Q  🚪 Quit
```

---

## 📖 Usage Guide

### Basic Workflow

```
1. Start app     → python main.py
2. Scrape data   → Option 1 → Select companies → Choose data type
3. Filter data   → Option 3 → Filter Studio → Build pipeline
4. View charts   → Option 7 → Visualization Studio
5. Sector deep dive → Option S → Sector Analysis Studio
6. Save Excel    → Option 6
```

### Sector Analysis Studio

```
S → Sector Studio
│
├── 1. Select sector (1-11)
│   └── 7 = Financials (HDFCBANK, ICICIBANK, BAJFINANCE...)
│
├── 2. Select how many companies
│   └── e.g., 20 (sorted by market cap)
│
├── 3. Price filter
│   ├── 1 = Top 50 by highest price
│   ├── 2 = Top 50 by lowest price
│   ├── 3 = Custom range (₹500 – ₹5000)
│   └── 6 = No filter
│
├── 4. Data to fetch
│   ├── 1 = Live prices only (~1 min)
│   ├── 2 = Financial data only (~10 min)
│   └── 3 = Both (recommended)
│
└── Output: Terminal display + Excel file
```

### Filter Studio

```python
# Example filter pipeline:
Category    → Watchlist          (87 → 20 rows)
% Change    → ≥ 1%               (20 → 8 rows)
Top N       → Top 5 by Change%   (8 → 5 rows)
→ Save preset as "top_watchlist_gainers"
→ Export to Excel
```

---

## 📡 Data Sources

| Source | Data | Method | Rate Limit |
|---|---|---|---|
| NSE India API | Live prices, indices, gainers/losers | REST JSON | ~1 req/sec |
| Yahoo Finance | Index quotes, individual stocks | HTML scraping | ~1 req/2sec |
| Screener.in | Revenue, PAT, EBITDA, all ratios | HTML scraping | ~1 req/3sec |
| Stooq | CSV price data (fallback) | CSV download | ~1 req/sec |

### robots.txt Compliance
All scrapers check `robots.txt` before fetching and include polite delays.

---

## 📊 Financial Metrics

| Category | Metric | Benchmark | Source |
|---|---|---|---|
| **Growth** | Revenue Growth (%) | > 10% YoY | Screener.in |
| **Profitability** | EBITDA (₹ Cr) | Positive & growing | Screener.in |
| **Profitability** | EBITDA Margin (%) | > 15% | Screener.in |
| **Profitability** | Net Profit / PAT (₹ Cr) | Positive & growing | Screener.in |
| **Profitability** | PAT Margin (%) | > 10% | Screener.in |
| **Returns** | ROE (%) | > 15% excellent | Screener.in |
| **Returns** | ROCE (%) | > 12% | Screener.in |
| **Returns** | ROA (%) | > 5% | Screener.in |
| **Valuation** | EPS (₹) | Rising trend | Screener.in |
| **Valuation** | P/E Ratio | Sector-specific | Screener.in |
| **Health** | Debt to Equity | < 1 safe | Screener.in |
| **Liquidity** | Current Ratio | 1.5 – 2.0 | Screener.in |
| **Cash Flow** | Free Cash Flow (₹ Cr) | Positive & growing | Screener.in |

---

## 🏭 Sector Coverage

| # | Sector | Companies | Key Stocks |
|---|---|---|---|
| 1 | Energy | 50 | RELIANCE, NTPC, ONGC |
| 2 | Materials | 50 | TATASTEEL, ULTRACEMCO |
| 3 | Industrials | 50 | LT, SIEMENS, HAL |
| 4 | Consumer Discretionary | 50 | MARUTI, TITAN, ZOMATO |
| 5 | Consumer Staples | 50 | HINDUNILVR, ITC, NESTLEIND |
| 6 | Healthcare | 50 | SUNPHARMA, DRREDDY, CIPLA |
| 7 | Financials | 50 | HDFCBANK, ICICIBANK, BAJFINANCE |
| 8 | Information Technology | 50 | TCS, INFY, WIPRO |
| 9 | Communication Services | 50 | BHARTIARTL, ZOMATO |
| 10 | Utilities | 50 | NTPC, POWERGRID, ADANIGREEN |
| 11 | Real Estate | 50 | DLF, GODREJPROP, PHOENIXLTD |

---

## 📤 Output Files

### Excel Workbook Structure
```
indian_stocks_data.xlsx
├── 📋 All Data          ← complete dataset
├── 📈 Indices           ← NIFTY, SENSEX, sector indices
├── 🚀 Gainers           ← top % gainers
├── 📉 Losers            ← top % losers
├── 👁 Watchlist         ← custom watchlist
├── 💰 Financials        ← 13 metrics + 3yr history
├── 🔍 Filtered          ← results after filter pipeline
└── 📊 Summary           ← overview statistics

sectors/Financials_20240115.xlsx
├── Financials Analysis  ← colour-coded benchmark table
├── 📊 Sector Summary    ← averages + leaders per metric
└── 📖 Benchmarks        ← metric reference guide
```

### Chart Files
```
output/charts/
├── 01_dashboard.png       ← 6-panel market overview
├── 02_fin_dashboard.png   ← financial analysis
├── 03_gainers_losers.png  ← horizontal bar chart
├── 04_sector_pie.png      ← donut + bar
├── 05_breadth.png         ← A/D ratio gauge
├── 06_sector_heatmap.png  ← red/green grid
├── 07_corr_heatmap.png    ← correlation matrix
├── 08_market_heatmap.png  ← treemap-style grid
├── 09_scatter.png         ← price vs change
├── 10_rev_pat_scatter.png ← revenue vs PAT
├── 11_dma.png             ← price + DMA 5/10/20
├── 12_crossover.png       ← buy/sell signals
├── 13_rev_pat_bar.png     ← 3-year grouped bar
├── 14_waterfall.png       ← PAT waterfall
├── 15_trend_TCS.png       ← single company trend
├── 16_sector_bar.png      ← sector avg change
├── 17_price_bar.png       ← price comparison
└── 18_index_pie.png       ← index distribution
```

---

## ⚙ Configuration

Edit `config.py` to customise:

```python
# Watchlist — stocks to always track
WATCHLIST = ["RELIANCE", "TCS", "INFY", "HDFCBANK", ...]

# How many stocks per scrape
MAX_STOCKS = 50

# Delay between requests (be polite!)
RATE_LIMIT_DELAY = 1.5   # seconds

# Append to existing Excel (True) or overwrite (False)
APPEND_MODE = True

# Output file location
EXCEL_FILENAME = "indian_stocks_data.xlsx"
```

---

## 🔧 Troubleshooting

| Problem | Solution |
|---|---|
| `ModuleNotFoundError: config` | Run from project root: `cd "Indian Stock Market Scraper"` |
| PowerShell activation blocked | Use CMD: `venv\Scripts\activate.bat` |
| NSE returns 403 | Normal — API still works. Cookies auto-set. |
| Screener returns empty | Add delay: increase `RATE_LIMIT_DELAY` to 4.0 |
| Excel permission denied | Close the file in Excel, then retry |
| `KeyError: 'Symbol'` | Column normalisation applied automatically |
| `ValueError: DataFrame truth` | Use `df.empty` not `if df` |

### Run Diagnostics

```bash
python diagnose.py           # Test all price data sources
python diagnose_screener.py  # Test Screener.in connectivity
python financial_scraper.py  # Test financial data for RELIANCE, TCS
python sector_analyzer.py    # Test analysis engine
python sector_ui.py          # Verify all imports
```

---

## 📦 Requirements

```
requests==2.31.0
httpx==0.25.0
beautifulsoup4==4.12.2
lxml==4.9.3
pandas==2.1.0
openpyxl==3.1.2
rich==13.6.0
numpy==1.26.0
matplotlib==3.8.0
seaborn==0.13.0
selenium==4.15.0
urllib3==2.0.7
python-dotenv==1.0.0
schedule==1.2.1
tabulate==0.9.0
colorama==0.4.6
scipy==1.11.0
```

---

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch: `git checkout -b feature/new-chart`
3. Commit changes: `git commit -m "Add candlestick chart"`
4. Push to branch: `git push origin feature/new-chart`
5. Open a Pull Request

---



---

## 🙏 Acknowledgements

- **NSE India** — official market data API
- **Screener.in** — free financial data for Indian stocks
- **Yahoo Finance** — index and stock quotes
- **Rich** — beautiful terminal UI library
- **pandas** — data manipulation
- **openpyxl** — Excel export

---

<div align="center">

Made with ❤️ for Indian retail investors

⭐ Star this repo if it helped you!

</div>
