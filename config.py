# config.py

import os
import sys
from dataclasses import dataclass, field
from typing import List, Dict

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
if _THIS_DIR not in sys.path:
    sys.path.insert(0, _THIS_DIR)


@dataclass
class ScraperConfig:

    PROJECT_ROOT: str = field(
        default_factory=lambda: os.path.dirname(os.path.abspath(__file__))
    )

    # ── Verified working URLs ─────────────────────────────────────────────────
    BASE_URLS: Dict[str, str] = field(default_factory=lambda: {
        # NSE API endpoints (confirmed working from diagnosis)
        "nse_indices" : "https://www.nseindia.com/api/allIndices",
        "nse_gainers" : "https://www.nseindia.com/api/live-analysis-variations?index=gainers",
        "nse_losers"  : "https://www.nseindia.com/api/live-analysis-variations?index=loosers",
        "nse_quote"   : "https://www.nseindia.com/api/quote-equity?symbol={}",

        # Yahoo Finance (confirmed working, use data-value attribute)
        "yahoo_quote" : "https://finance.yahoo.com/quote/{}",

        # Stooq (^SNX confirmed working, others need correct symbols)
        "stooq_quote" : "https://stooq.com/q/l/?s={}&f=sd2t2ohlcv&h&e=csv",
        "stooq_hist"  : "https://stooq.com/q/d/l/?s={}&i=d",
    })

    # ── Yahoo Finance symbols (verified from diagnosis) ───────────────────────
    # Diagnosis showed data-symbol values on the page
    YAHOO_INDICES: Dict[str, str] = field(default_factory=lambda: {
        "^NSEI"   : "NIFTY 50",       # confirmed exists
        "^BSESN"  : "BSE SENSEX",     # confirmed exists
        "^NSEBANK": "NIFTY BANK",
        "^CNXIT"  : "NIFTY IT",
        "^CNXPHARMA": "NIFTY PHARMA",
    })

    # ── Stooq symbols (^SNX confirmed, others mapped correctly) ──────────────
    STOOQ_INDICES: Dict[str, str] = field(default_factory=lambda: {
        "^SNX"   : "BSE SENSEX",      # confirmed working from diagnosis
        "^NF50"  : "NIFTY 50",        # returns N/D but try alternate
        "inx.in" : "NIFTY 50 ALT",    # alternate Stooq format
    })

    # ── HTTP Settings ─────────────────────────────────────────────────────────
    REQUEST_TIMEOUT : int   = 30
    MAX_RETRIES     : int   = 3
    RETRY_DELAY     : float = 2.0
    RATE_LIMIT_DELAY: float = 1.5
    USE_PROXY       : bool  = False
    PROXY_URL       : str   = ""

    # ── Headers ───────────────────────────────────────────────────────────────
    HEADERS: Dict[str, str] = field(default_factory=lambda: {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept"         : "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Connection"     : "keep-alive",
    })

    # ── NSE API Headers (different from browser headers) ─────────────────────
    NSE_HEADERS: Dict[str, str] = field(default_factory=lambda: {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept"          : "application/json, text/plain, */*",
        "Accept-Language" : "en-US,en;q=0.9",
        "Accept-Encoding" : "gzip, deflate, br",
        "Referer"         : "https://www.nseindia.com/",
        "Origin"          : "https://www.nseindia.com",
        "sec-ch-ua"       : '"Not_A Brand";v="8", "Chromium";v="120"',
        "sec-fetch-dest"  : "empty",
        "sec-fetch-mode"  : "cors",
        "sec-fetch-site"  : "same-origin",
        "Cache-Control"   : "no-cache",
        "Pragma"          : "no-cache",
    })

    # ── Output ────────────────────────────────────────────────────────────────
    OUTPUT_FOLDER  : str = "output"
    EXCEL_FILENAME : str = "indian_stocks_data.xlsx"
    LOG_FOLDER     : str = "logs"
    LOG_FILE       : str = "scraper.log"

    # ── Options ───────────────────────────────────────────────────────────────
    USE_SELENIUM   : bool = False
    HEADLESS       : bool = True
    APPEND_MODE    : bool = True
    MAX_STOCKS     : int  = 50

    # ── Watchlist ─────────────────────────────────────────────────────────────
    WATCHLIST: List[str] = field(default_factory=lambda: [
        "RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK",
        "HINDUNILVR", "ITC", "SBIN", "BAJFINANCE", "ADANIENT",
        "WIPRO", "LT", "AXISBANK", "ASIANPAINT", "MARUTI",
        "TATAMOTORS", "SUNPHARMA", "ULTRACEMCO", "NESTLEIND", "POWERGRID",
    ])

    # ── Sector Map ────────────────────────────────────────────────────────────
    SECTOR_MAP: Dict[str, str] = field(default_factory=lambda: {
        "RELIANCE"   : "Energy",
        "TCS"        : "IT",
        "INFY"       : "IT",
        "HDFCBANK"   : "Banking",
        "ICICIBANK"  : "Banking",
        "HINDUNILVR" : "FMCG",
        "ITC"        : "FMCG",
        "SBIN"       : "Banking",
        "BAJFINANCE" : "Finance",
        "ADANIENT"   : "Conglomerate",
        "WIPRO"      : "IT",
        "LT"         : "Infrastructure",
        "AXISBANK"   : "Banking",
        "ASIANPAINT" : "Consumer Goods",
        "MARUTI"     : "Auto",
        "TATAMOTORS" : "Auto",
        "SUNPHARMA"  : "Pharma",
        "ULTRACEMCO" : "Cement",
        "NESTLEIND"  : "FMCG",
        "POWERGRID"  : "Utilities",
    })

    def __post_init__(self):
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.log_dir,   exist_ok=True)

    @property
    def output_dir(self)  -> str:
        return os.path.join(self.PROJECT_ROOT, self.OUTPUT_FOLDER)

    @property
    def log_dir(self) -> str:
        return os.path.join(self.PROJECT_ROOT, self.LOG_FOLDER)

    @property
    def excel_path(self) -> str:
        return os.path.join(self.output_dir, self.EXCEL_FILENAME)

    @property
    def log_path(self) -> str:
        return os.path.join(self.log_dir, self.LOG_FILE)

    @property
    def presets_path(self) -> str:
        return os.path.join(self.output_dir, "filter_presets.json")


if __name__ == "__main__":
    c = ScraperConfig()
    print(f"Excel : {c.excel_path}")
    print(f"Logs  : {c.log_path}")
    print("✅ Config OK")