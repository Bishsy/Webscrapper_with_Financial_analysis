# sector_scraper.py  ── Fixed: standardise ALL column names to Title Case

import os, sys, time, json, random, re
from datetime import datetime
from typing   import Dict, List, Optional, Tuple

import requests
from bs4 import BeautifulSoup

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
if _THIS_DIR not in sys.path:
    sys.path.insert(0, _THIS_DIR)

from config        import ScraperConfig
from logger_setup  import get_logger
from sector_data   import SECTOR_COMPANIES, get_sector_companies


class SectorScraper:
    """
    Scrapes live prices + financial metrics for sector companies.
    ALL price record keys use Title Case to match financial records.
    """

    NSE_HOME      = "https://www.nseindia.com"
    NSE_QUOTE_URL = "https://www.nseindia.com/api/quote-equity?symbol={}"

    NSE_HEADERS = {
        "User-Agent"     : "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0",
        "Accept"         : "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer"        : "https://www.nseindia.com/",
        "sec-fetch-dest" : "empty",
        "sec-fetch-mode" : "cors",
        "sec-fetch-site" : "same-origin",
    }

    def __init__(self, config: ScraperConfig):
        self.config      = config
        self.logger      = get_logger(self.__class__.__name__, config)
        self.nse_session = self._make_nse_session()

    def _make_nse_session(self) -> requests.Session:
        s = requests.Session()
        s.headers.update(self.NSE_HEADERS)
        try:
            r = s.get(self.NSE_HOME, timeout=15)
            self.logger.info(f"NSE session: {r.status_code}")
        except Exception as e:
            self.logger.warning(f"NSE session init: {e}")
        s.cookies.set("AKA_A2", "A", domain=".nseindia.com")
        time.sleep(1)
        return s

    def get_live_price(self, symbol: str) -> Optional[Dict]:
        """
        Fetch live price from NSE API.
        Returns dict with Title Case keys matching financial records.
        """
        try:
            time.sleep(random.uniform(0.5, 1.2))
            url  = self.NSE_QUOTE_URL.format(symbol)
            resp = self.nse_session.get(url, timeout=20)

            if resp.status_code != 200:
                self.logger.debug(
                    f"NSE {symbol}: status {resp.status_code}"
                )
                return None

            data       = resp.json()
            price_info = data.get("priceInfo",            {})
            meta       = data.get("metadata",              {})
            week_hl    = price_info.get("weekHighLow",     {})
            intra      = price_info.get("intraDayHighLow", {})
            trade      = (data.get("marketDeptOrderBook",  {})
                              .get("tradeInfo", {}))

            ltp = price_info.get("lastPrice", None)
            pch = price_info.get("pChange",   None)

            if ltp is None:
                return None

            # ── ALL keys use Title Case ────────────────────────────────────────
            return {
                "Symbol"         : symbol,                          # ← Title Case
                "Company"        : meta.get("companyName", symbol),
                "Price (₹)"      : ltp,
                "Open (₹)"       : price_info.get("open",          0),
                "High (₹)"       : intra.get("max",                0),
                "Low (₹)"        : intra.get("min",                0),
                "Prev Close (₹)" : price_info.get("previousClose", 0),
                "Change (₹)"     : price_info.get("change",        0),
                "Change (%)"     : pch,
                "Volume"         : trade.get("totalTradedVolume",   0),
                "52W High (₹)"   : week_hl.get("max",              0),
                "52W Low (₹)"    : week_hl.get("min",              0),
            }

        except Exception as e:
            self.logger.debug(f"NSE price error [{symbol}]: {e}")
            return None

    def scrape_financials(self, symbol: str) -> Dict:
        """Import and use the fixed financial scraper."""
        from financial_scraper import ScreenerFinancialScraper
        if not hasattr(self, "_fin_scraper"):
            self._fin_scraper = ScreenerFinancialScraper(
                self.config, self.logger
            )
        return self._fin_scraper.scrape_company(symbol)