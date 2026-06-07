# scraper.py
# Fixed based on actual diagnostic results:
#   - Yahoo  : use data-value attribute (not data-symbol lookup)
#   - NSE API: skip homepage (403), call API directly with cookies
#   - Stooq  : use ^SNX (confirmed), fix other symbols

import os
import sys
import csv
import io
import json
import time
import random
import re
from datetime import datetime
from typing  import Dict, List, Optional, Tuple

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
if _THIS_DIR not in sys.path:
    sys.path.insert(0, _THIS_DIR)

from config       import ScraperConfig
from logger_setup import get_logger


# ─────────────────────────────────────────────────────────────────────────────
# Shared utilities
# ─────────────────────────────────────────────────────────────────────────────

def make_session(headers: dict, config: ScraperConfig) -> requests.Session:
    s = requests.Session()
    s.headers.update(headers)
    retry = Retry(
        total            = config.MAX_RETRIES,
        backoff_factor   = 1.5,
        status_forcelist = [429, 500, 502, 503, 504],
        allowed_methods  = ["GET"],
    )
    adapter = HTTPAdapter(max_retries=retry)
    s.mount("https://", adapter)
    s.mount("http://",  adapter)
    return s


def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def safe_get(session: requests.Session, url: str,
             timeout: int = 30, extra_headers: dict = None,
             logger=None) -> Optional[requests.Response]:
    """GET with error handling."""
    try:
        hdrs = {}
        if extra_headers:
            hdrs.update(extra_headers)
        time.sleep(random.uniform(0.8, 1.5))
        resp = session.get(url, headers=hdrs, timeout=timeout)
        if logger:
            logger.info(f"  [{resp.status_code}] {url[:80]}")
        resp.raise_for_status()
        return resp
    except requests.exceptions.HTTPError as e:
        if logger:
            logger.error(f"  HTTP {e.response.status_code}: {url[:60]}")
    except requests.exceptions.ConnectionError:
        if logger:
            logger.error(f"  Connection error: {url[:60]}")
    except requests.exceptions.Timeout:
        if logger:
            logger.error(f"  Timeout: {url[:60]}")
    except Exception as e:
        if logger:
            logger.error(f"  Error: {e}")
    return None


def empty_row(overrides: dict = None) -> dict:
    """Return a row dict with all N/A defaults."""
    base = {
        "Date"           : now_str(),
        "Source"         : "N/A",
        "Category"       : "N/A",
        "Symbol"         : "N/A",
        "Title"          : "N/A",
        "Sector"         : "N/A",
        "Price (₹)"      : "N/A",
        "Open"           : "N/A",
        "High"           : "N/A",
        "Low"            : "N/A",
        "Prev Close"     : "N/A",
        "Change"         : "N/A",
        "Change (%)"     : "N/A",
        "Volume"         : "N/A",
        "Market Cap (Cr)": "N/A",
        "52W High"       : "N/A",
        "52W Low"        : "N/A",
        "URL"            : "N/A",
    }
    if overrides:
        base.update(overrides)
    return base


# ─────────────────────────────────────────────────────────────────────────────
# Source 1 ── NSE India API (CONFIRMED WORKING from diagnosis)
# ─────────────────────────────────────────────────────────────────────────────

class NSEScraper:
    """
    NSE India official API.
    Diagnosis confirmed:
      - Homepage returns 403 (skip it)
      - API /allIndices returns 200 with 135 records ✅
      - Only AKA_A2 cookie needed
    """

    API_BASE    = "https://www.nseindia.com"
    API_INDICES = "https://www.nseindia.com/api/allIndices"
    API_GAINERS = "https://www.nseindia.com/api/live-analysis-variations?index=gainers"
    API_LOSERS  = "https://www.nseindia.com/api/live-analysis-variations?index=loosers"
    API_QUOTE   = "https://www.nseindia.com/api/quote-equity?symbol={}"
    API_MKTCAP  = "https://www.nseindia.com/api/market-data-pre-open?key=NIFTY"

    def __init__(self, config: ScraperConfig, logger):
        self.config  = config
        self.logger  = logger
        self.session = make_session(config.NSE_HEADERS, config)
        self._init_cookies()

    def _init_cookies(self):
        """
        Diagnosis showed homepage gives 403 but sets AKA_A2 cookie.
        We just need that cookie — ignore the 403.
        """
        self.logger.info("NSE: Setting up cookies…")
        try:
            # Try homepage (may 403 but still sets cookies)
            resp = self.session.get(
                self.API_BASE, timeout=15,
                allow_redirects=True
            )
            self.logger.info(
                f"  NSE home: {resp.status_code} | "
                f"cookies: {list(self.session.cookies.keys())}"
            )
        except Exception as e:
            self.logger.warning(f"  NSE home warning (OK to ignore): {e}")

        # Inject the AKA_A2 cookie manually if not set
        if "AKA_A2" not in self.session.cookies:
            self.session.cookies.set("AKA_A2", "A",
                                     domain=".nseindia.com")
        time.sleep(1.5)

    def _get_json(self, url: str) -> Optional[dict]:
        """Fetch JSON from NSE API."""
        resp = safe_get(
            self.session, url,
            timeout=25,
            logger=self.logger,
        )
        if not resp:
            return None
        try:
            return resp.json()
        except json.JSONDecodeError as e:
            self.logger.error(f"  NSE JSON decode error: {e}")
            self.logger.debug(f"  Response text: {resp.text[:200]}")
            return None

    # ── Indices ───────────────────────────────────────────────────────────────

    def scrape_indices(self) -> List[dict]:
        """
        Diagnosis confirmed this returns 135 records with full data.
        Sample: {"index":"NIFTY 50","last":24176.15,"variation":-150.5,...}
        """
        self.logger.info("NSE: Fetching all indices…")
        data = self._get_json(self.API_INDICES)
        if not data:
            return []

        records = []
        for item in data.get("data", []):
            pct = item.get("percentChange", "N/A")
            records.append(empty_row({
                "Date"           : now_str(),
                "Source"         : "NSE India",
                "Category"       : "Index",
                "Symbol"         : item.get("indexSymbol", ""),
                "Title"          : item.get("index",       ""),
                "Sector"         : "Index",
                "Price (₹)"      : str(item.get("last",           "N/A")),
                "Open"           : str(item.get("open",           "N/A")),
                "High"           : str(item.get("high",           "N/A")),
                "Low"            : str(item.get("low",            "N/A")),
                "Prev Close"     : str(item.get("previousClose",  "N/A")),
                "Change"         : str(item.get("variation",      "N/A")),
                "Change (%)"     : f"{pct}%" if pct != "N/A" else "N/A",
                "Volume"         : str(item.get("totalTradedVolume","N/A")),
                "Market Cap (Cr)": str(item.get("marketCap",      "N/A")),
                "52W High"       : str(item.get("yearHigh",       "N/A")),
                "52W Low"        : str(item.get("yearLow",        "N/A")),
                "URL"            : f"https://www.nseindia.com/market-data/live-equity-market",
            }))

        self.logger.info(f"  ✅ NSE Indices: {len(records)} records")
        return records

    # ── Gainers ───────────────────────────────────────────────────────────────

    def scrape_gainers(self) -> List[dict]:
        self.logger.info("NSE: Fetching gainers…")
        data = self._get_json(self.API_GAINERS)
        if not data:
            return []

        records = []
        # API returns dict with index keys: NIFTY, BANKNIFTY, etc.
        for index_key, index_data in data.items():
            if not isinstance(index_data, dict):
                continue
            for item in index_data.get("data", [])[:self.config.MAX_STOCKS]:
                pct = item.get("perChange", "N/A")
                records.append(empty_row({
                    "Date"      : now_str(),
                    "Source"    : "NSE India",
                    "Category"  : "Top Gainer",
                    "Symbol"    : item.get("symbol",    ""),
                    "Title"     : item.get("symbol",    ""),
                    "Sector"    : self.config.SECTOR_MAP.get(
                                    item.get("symbol",""), "Unknown"),
                    "Price (₹)" : str(item.get("lastPrice",  "N/A")),
                    "Open"      : str(item.get("open",       "N/A")),
                    "High"      : str(item.get("high",       "N/A")),
                    "Low"       : str(item.get("low",        "N/A")),
                    "Prev Close": str(item.get("previousPrice","N/A")),
                    "Change"    : str(item.get("netPrice",   "N/A")),
                    "Change (%)": f"{pct}%" if str(pct) != "N/A" else "N/A",
                    "Volume"    : str(item.get("tradedQuantity","N/A")),
                    "52W High"  : str(item.get("yearHigh",   "N/A")),
                    "52W Low"   : str(item.get("yearLow",    "N/A")),
                    "URL"       : f"https://www.nseindia.com/get-quotes/equity?symbol={item.get('symbol','')}",
                }))

        self.logger.info(f"  ✅ NSE Gainers: {len(records)} records")
        return records

    # ── Losers ────────────────────────────────────────────────────────────────

    def scrape_losers(self) -> List[dict]:
        self.logger.info("NSE: Fetching losers…")
        data = self._get_json(self.API_LOSERS)
        if not data:
            return []

        records = []
        for index_key, index_data in data.items():
            if not isinstance(index_data, dict):
                continue
            for item in index_data.get("data", [])[:self.config.MAX_STOCKS]:
                pct = item.get("perChange", "N/A")
                records.append(empty_row({
                    "Date"      : now_str(),
                    "Source"    : "NSE India",
                    "Category"  : "Top Loser",
                    "Symbol"    : item.get("symbol",    ""),
                    "Title"     : item.get("symbol",    ""),
                    "Sector"    : self.config.SECTOR_MAP.get(
                                    item.get("symbol",""), "Unknown"),
                    "Price (₹)" : str(item.get("lastPrice",  "N/A")),
                    "Open"      : str(item.get("open",       "N/A")),
                    "High"      : str(item.get("high",       "N/A")),
                    "Low"       : str(item.get("low",        "N/A")),
                    "Prev Close": str(item.get("previousPrice","N/A")),
                    "Change"    : str(item.get("netPrice",   "N/A")),
                    "Change (%)": f"{pct}%" if str(pct) != "N/A" else "N/A",
                    "Volume"    : str(item.get("tradedQuantity","N/A")),
                    "52W High"  : str(item.get("yearHigh",   "N/A")),
                    "52W Low"   : str(item.get("yearLow",    "N/A")),
                    "URL"       : f"https://www.nseindia.com/get-quotes/equity?symbol={item.get('symbol','')}",
                }))

        self.logger.info(f"  ✅ NSE Losers: {len(records)} records")
        return records

    # ── Individual Stock Quote ────────────────────────────────────────────────

    def scrape_quote(self, symbol: str) -> Optional[dict]:
        """Fetch one stock's full quote from NSE."""
        url  = self.API_QUOTE.format(symbol)
        data = self._get_json(url)
        if not data:
            return None

        try:
            price_info = data.get("priceInfo",          {})
            meta       = data.get("metadata",            {})
            week_hl    = price_info.get("weekHighLow",   {})
            intra_hl   = price_info.get("intraDayHighLow",{})
            trade_info = (data.get("marketDeptOrderBook",{})
                              .get("tradeInfo", {}))

            ltp    = price_info.get("lastPrice", "N/A")
            chg    = price_info.get("change",    "N/A")
            pct    = price_info.get("pChange",   "N/A")

            return empty_row({
                "Date"           : now_str(),
                "Source"         : "NSE India",
                "Category"       : "Watchlist",
                "Symbol"         : symbol,
                "Title"          : meta.get("companyName", symbol),
                "Sector"         : self.config.SECTOR_MAP.get(symbol, "Unknown"),
                "Price (₹)"      : str(ltp),
                "Open"           : str(price_info.get("open",  "N/A")),
                "High"           : str(intra_hl.get("max",     "N/A")),
                "Low"            : str(intra_hl.get("min",     "N/A")),
                "Prev Close"     : str(price_info.get("previousClose","N/A")),
                "Change"         : str(chg),
                "Change (%)"     : f"{pct}%" if str(pct) != "N/A" else "N/A",
                "Volume"         : str(trade_info.get("totalTradedVolume","N/A")),
                "Market Cap (Cr)": "N/A",
                "52W High"       : str(week_hl.get("max", "N/A")),
                "52W Low"        : str(week_hl.get("min", "N/A")),
                "URL"            : f"https://www.nseindia.com/get-quotes/equity?symbol={symbol}",
            })
        except Exception as e:
            self.logger.error(f"  NSE quote parse error [{symbol}]: {e}")
            return None

    def scrape_watchlist(self) -> List[dict]:
        records = []
        self.logger.info(f"NSE: Fetching {len(self.config.WATCHLIST)} watchlist stocks…")
        for sym in self.config.WATCHLIST:
            row = self.scrape_quote(sym)
            if row:
                records.append(row)
                self.logger.info(
                    f"  ✅ {sym:<15} "
                    f"₹{row['Price (₹)']:<12} "
                    f"{row['Change (%)']}"
                )
            else:
                self.logger.warning(f"  ⚠  {sym}: no data")
            time.sleep(0.5)   # gentle rate limit

        self.logger.info(f"  NSE Watchlist: {len(records)} records")
        return records


# ─────────────────────────────────────────────────────────────────────────────
# Source 2 ── Yahoo Finance (CONFIRMED WORKING from diagnosis)
# ─────────────────────────────────────────────────────────────────────────────

class YahooScraper:
    """
    Yahoo Finance scraper.

    Diagnosis confirmed:
      - fin-streamer tags ARE present (90 found)
      - data-value attribute holds the number (not inner text)
      - data-symbol on page = "^GSPC","^DJI" etc (US indices on homepage)
      - For Indian indices, must use correct Yahoo symbols:
          ^NSEI   = NIFTY 50
          ^BSESN  = BSE SENSEX
          RELIANCE.NS = NSE stock
    """

    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept"         : "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Referer"        : "https://finance.yahoo.com/",
        "Cache-Control"  : "no-cache",
    }

    def __init__(self, config: ScraperConfig, logger):
        self.config  = config
        self.logger  = logger
        self.session = make_session(self.HEADERS, config)

    def _get_soup(self, url: str) -> Optional[BeautifulSoup]:
        resp = safe_get(self.session, url, timeout=25, logger=self.logger)
        if not resp:
            return None
        return BeautifulSoup(resp.text, "lxml")

    def _extract_price(self, soup: BeautifulSoup,
                        symbol: str) -> Tuple[str, str, str]:
        """
        Extract price, change, pct using data-value attribute.
        Diagnosis showed: data-value="7398.93" on fin-streamer tags.
        The data-symbol on the quote page MATCHES the URL symbol.
        """
        price = change = pct = "N/A"

        # ── Strategy 1: fin-streamer with data-value (confirmed working) ──────
        all_streamers = soup.find_all("fin-streamer")
        self.logger.debug(f"  fin-streamer tags found: {len(all_streamers)}")

        for tag in all_streamers:
            tag_sym   = tag.get("data-symbol", "")
            tag_field = tag.get("data-field",  "")
            tag_val   = tag.get("data-value",  "")   # ← use data-value not value

            if tag_sym != symbol:
                continue

            if tag_field == "regularMarketPrice" and tag_val:
                price = tag_val
            elif tag_field == "regularMarketChange" and tag_val:
                try:
                    change = f"{float(tag_val):+.2f}"
                except ValueError:
                    change = tag_val
            elif tag_field == "regularMarketChangePercent" and tag_val:
                try:
                    pct = f"{float(tag_val):+.2f}%"
                except ValueError:
                    pct = tag_val

        if price != "N/A":
            return price, change, pct

        # ── Strategy 2: data-testid spans (new Yahoo UI) ──────────────────────
        price_span = soup.find("span", {"data-testid": "qsp-price"})
        if price_span:
            raw = price_span.get_text(strip=True).replace(",", "")
            if raw:
                price = raw

        change_span = soup.find("span", {"data-testid": "qsp-price-change"})
        pct_span    = soup.find("span", {"data-testid": "qsp-price-change-percent"})
        if change_span:
            change = change_span.get_text(strip=True)
        if pct_span:
            pct = pct_span.get_text(strip=True).strip("()")

        if price != "N/A":
            return price, change, pct

        # ── Strategy 3: JSON in embedded script ───────────────────────────────
        for script in soup.find_all("script"):
            text = script.string or ""
            if "regularMarketPrice" not in text:
                continue
            # Match: "regularMarketPrice":{"raw":24176.15,
            pm = re.search(
                r'"regularMarketPrice"\s*:\s*\{\s*"raw"\s*:\s*([\d.]+)',
                text
            )
            cm = re.search(
                r'"regularMarketChange"\s*:\s*\{\s*"raw"\s*:\s*([-\d.]+)',
                text
            )
            pcm = re.search(
                r'"regularMarketChangePercent"\s*:\s*\{\s*"raw"\s*:\s*([-\d.]+)',
                text
            )
            if pm:
                price = pm.group(1)
            if cm:
                try:
                    change = f"{float(cm.group(1)):+.2f}"
                except ValueError:
                    change = cm.group(1)
            if pcm:
                try:
                    pct = f"{float(pcm.group(1)):+.2f}%"
                except ValueError:
                    pct = pcm.group(1)

            if price != "N/A":
                break

        return price, change, pct

    def _extract_stats(self, soup: BeautifulSoup) -> dict:
        """Extract summary table stats."""
        stats = {}

        # Method 1: <tr><td> pairs
        for tr in soup.find_all("tr"):
            tds = tr.find_all("td")
            if len(tds) == 2:
                key = tds[0].get_text(strip=True)
                val = tds[1].get_text(strip=True)
                stats[key] = val

        # Method 2: fin-streamer for specific fields
        field_map = {
            "regularMarketOpen"          : "Open",
            "regularMarketDayHigh"       : "High",
            "regularMarketDayLow"        : "Low",
            "regularMarketPreviousClose" : "Prev Close",
            "regularMarketVolume"        : "Volume",
            "fiftyTwoWeekHigh"           : "52W High",
            "fiftyTwoWeekLow"            : "52W Low",
            "marketCap"                  : "Market Cap",
        }
        for tag in soup.find_all("fin-streamer"):
            field = tag.get("data-field", "")
            val   = tag.get("data-value", tag.get_text(strip=True))
            if field in field_map and val:
                stats[field_map[field]] = val

        # Method 3: script JSON fallback
        for script in soup.find_all("script"):
            text = script.string or ""
            if "fiftyTwoWeekHigh" not in text:
                continue
            for json_key, stat_key in [
                ("fiftyTwoWeekHigh", "52W High"),
                ("fiftyTwoWeekLow",  "52W Low"),
                ("regularMarketOpen","Open"),
                ("regularMarketVolume","Volume"),
                ("marketCap",        "Market Cap"),
            ]:
                m = re.search(
                    rf'"{json_key}"\s*:\s*\{{\s*"raw"\s*:\s*([\d.]+)',
                    text
                )
                if m and stat_key not in stats:
                    stats[stat_key] = m.group(1)
            break

        return stats

    def scrape_quote(self, yahoo_symbol: str, display_name: str,
                     category: str = "Index",
                     nse_symbol: str = "") -> List[dict]:
        """Scrape one Yahoo Finance quote page."""
        url  = f"https://finance.yahoo.com/quote/{yahoo_symbol}/"
        soup = self._get_soup(url)
        if not soup:
            return []

        price, change, pct = self._extract_price(soup, yahoo_symbol)
        stats              = self._extract_stats(soup)

        if price == "N/A":
            self.logger.warning(
                f"  ⚠  Yahoo: No price for {yahoo_symbol} "
                f"(page may need JS or symbol wrong)"
            )
            return []

        self.logger.info(
            f"  ✅ Yahoo {display_name:<20} "
            f"₹{price:<12} {pct}"
        )

        return [empty_row({
            "Date"           : now_str(),
            "Source"         : "Yahoo Finance",
            "Category"       : category,
            "Symbol"         : nse_symbol or yahoo_symbol,
            "Title"          : display_name,
            "Sector"         : self.config.SECTOR_MAP.get(
                                nse_symbol or yahoo_symbol, "Index"),
            "Price (₹)"      : price,
            "Open"           : stats.get("Open",       "N/A"),
            "High"           : stats.get("High",       "N/A"),
            "Low"            : stats.get("Low",        "N/A"),
            "Prev Close"     : stats.get("Prev Close", "N/A"),
            "Change"         : change,
            "Change (%)"     : pct,
            "Volume"         : stats.get("Volume",     "N/A"),
            "Market Cap (Cr)": stats.get("Market Cap", "N/A"),
            "52W High"       : stats.get("52W High",   "N/A"),
            "52W Low"        : stats.get("52W Low",    "N/A"),
            "URL"            : url,
        })]

    def scrape_indices(self) -> List[dict]:
        records = []
        self.logger.info("Yahoo: Fetching Indian indices…")
        for symbol, name in self.config.YAHOO_INDICES.items():
            rows = self.scrape_quote(symbol, name, category="Index")
            records.extend(rows)
        return records

    def scrape_watchlist(self) -> List[dict]:
        records = []
        self.logger.info(f"Yahoo: Fetching {len(self.config.WATCHLIST)} stocks…")
        for sym in self.config.WATCHLIST:
            yahoo_sym = f"{sym}.NS"   # NSE suffix on Yahoo
            rows = self.scrape_quote(
                yahoo_sym, sym,
                category   = "Watchlist",
                nse_symbol = sym,
            )
            records.extend(rows)
        return records


# ─────────────────────────────────────────────────────────────────────────────
# Source 3 ── Stooq (^SNX confirmed working, use as fallback)
# ─────────────────────────────────────────────────────────────────────────────

class StooqScraper:
    """
    Stooq CSV scraper.
    Diagnosis confirmed:
      - ^SNX (Sensex) returns real data ✅
      - ^NF50 returns N/D (use alternate symbols)
    """

    # Confirmed working Stooq symbols for Indian market
    CONFIRMED_INDICES = {
        "^SNX"     : "BSE SENSEX",      # ✅ confirmed
        "^bseit.bo": "BSE IT",
        "^bsebk.bo": "BSE BANKEX",
    }

    # Stock format for Stooq: SYMBOL.IN (NSE) or SYMBOL.BO (BSE)
    STOCK_SUFFIXES = [".in", ".bo"]   # try both

    BASE_CSV = "https://stooq.com/q/l/?s={}&f=sd2t2ohlcv&h&e=csv"
    HIST_CSV = "https://stooq.com/q/d/l/?s={}&i=d"

    def __init__(self, config: ScraperConfig, logger):
        self.config  = config
        self.logger  = logger
        self.session = make_session({
            "User-Agent": "Mozilla/5.0 (compatible; StooqBot/1.0)"
        }, config)

    def _fetch_csv(self, symbol: str) -> Optional[dict]:
        """Fetch live quote CSV from Stooq."""
        url  = self.BASE_CSV.format(symbol)
        resp = safe_get(self.session, url, timeout=15, logger=self.logger)
        if not resp:
            return None

        try:
            reader = csv.DictReader(io.StringIO(resp.text))
            for row in reader:
                # Skip N/D rows (symbol not found on Stooq)
                if row.get("Close", "N/D") == "N/D":
                    self.logger.debug(f"  Stooq N/D for {symbol}")
                    return None
                return {
                    "symbol": row.get("Symbol", symbol),
                    "date"  : row.get("Date",   ""),
                    "open"  : row.get("Open",   "N/A"),
                    "high"  : row.get("High",   "N/A"),
                    "low"   : row.get("Low",    "N/A"),
                    "close" : row.get("Close",  "N/A"),
                    "volume": row.get("Volume", "N/A"),
                }
        except Exception as e:
            self.logger.error(f"  Stooq CSV parse error [{symbol}]: {e}")
        return None

    def _fetch_prev_close(self, symbol: str) -> Optional[str]:
        """Get previous day's close for change calculation."""
        url  = self.HIST_CSV.format(symbol)
        resp = safe_get(self.session, url, timeout=15, logger=self.logger)
        if not resp:
            return None
        try:
            reader = csv.DictReader(io.StringIO(resp.text))
            rows   = list(reader)
            if len(rows) >= 2:
                return rows[-2].get("Close")
        except Exception:
            pass
        return None

    def _calc_change(self, close_str: str,
                     symbol: str) -> Tuple[str, str]:
        """Calculate change and pct from current and previous close."""
        try:
            prev_str = self._fetch_prev_close(symbol)
            if not prev_str:
                return "N/A", "N/A"
            curr  = float(close_str)
            prev  = float(prev_str)
            chg   = curr - prev
            pct   = (chg / prev) * 100
            return f"{chg:+.2f}", f"{pct:+.2f}%"
        except (ValueError, ZeroDivisionError):
            return "N/A", "N/A"

    def scrape_indices(self) -> List[dict]:
        """Scrape confirmed-working Stooq indices."""
        records = []
        self.logger.info("Stooq: Fetching indices…")
        for symbol, name in self.CONFIRMED_INDICES.items():
            quote = self._fetch_csv(symbol)
            if not quote:
                self.logger.warning(f"  ⚠  Stooq {name}: no data")
                continue
            close        = quote["close"]
            change, pct  = self._calc_change(close, symbol)
            records.append(empty_row({
                "Date"      : now_str(),
                "Source"    : "Stooq",
                "Category"  : "Index",
                "Symbol"    : symbol.upper(),
                "Title"     : name,
                "Sector"    : "Index",
                "Price (₹)" : close,
                "Open"      : quote["open"],
                "High"      : quote["high"],
                "Low"       : quote["low"],
                "Change"    : change,
                "Change (%)": pct,
                "Volume"    : quote["volume"],
                "URL"       : f"https://stooq.com/q/?s={symbol}",
            }))
            self.logger.info(f"  ✅ Stooq {name:<20} ₹{close} {pct}")

        return records

    def scrape_watchlist(self) -> List[dict]:
        """Try .in then .bo suffix for each watchlist stock."""
        records = []
        self.logger.info("Stooq: Fetching watchlist stocks…")
        for sym in self.config.WATCHLIST:
            quote = None
            used_sym = ""
            for suffix in self.STOCK_SUFFIXES:
                stooq_sym = f"{sym.lower()}{suffix}"
                quote = self._fetch_csv(stooq_sym)
                if quote:
                    used_sym = stooq_sym
                    break

            if not quote:
                self.logger.warning(f"  ⚠  Stooq {sym}: no data")
                continue

            close       = quote["close"]
            change, pct = self._calc_change(close, used_sym)

            records.append(empty_row({
                "Date"      : now_str(),
                "Source"    : "Stooq",
                "Category"  : "Watchlist",
                "Symbol"    : sym,
                "Title"     : sym,
                "Sector"    : self.config.SECTOR_MAP.get(sym, "Unknown"),
                "Price (₹)" : close,
                "Open"      : quote["open"],
                "High"      : quote["high"],
                "Low"       : quote["low"],
                "Change"    : change,
                "Change (%)": pct,
                "Volume"    : quote["volume"],
                "URL"       : f"https://stooq.com/q/?s={used_sym}",
            }))
            self.logger.info(
                f"  ✅ Stooq {sym:<15} ₹{close} {pct}"
            )

        return records


# ─────────────────────────────────────────────────────────────────────────────
# Master Scraper  ── Smart fallback chain
# ─────────────────────────────────────────────────────────────────────────────

class IndianStockScraper:
    """
    Master scraper with source priority and automatic fallback:
      1. NSE India API  → most accurate, confirmed working
      2. Yahoo Finance  → good for indices, confirmed working
      3. Stooq          → reliable CSV fallback
    """

    def __init__(self, config: ScraperConfig):
        self.config = config
        self.logger = get_logger(self.__class__.__name__, config)
        self.nse    = NSEScraper(config,   self.logger)
        self.yahoo  = YahooScraper(config, self.logger)
        self.stooq  = StooqScraper(config, self.logger)

    def _run(self, label: str, fn) -> List[dict]:
        """Run a scraper function with full error catching."""
        self.logger.info(f"\n{'─'*50}")
        self.logger.info(f"▶ {label}")
        self.logger.info(f"{'─'*50}")
        try:
            rows = fn()
            self.logger.info(f"  → {len(rows)} records from {label}")
            return rows if rows else []
        except Exception as e:
            self.logger.error(f"  ✘ {label} FAILED: {e}", exc_info=True)
            return []

    def run_all(self) -> List[dict]:
        all_records: List[dict] = []

        self.logger.info("\n" + "="*55)
        self.logger.info("  INDIAN STOCK SCRAPER  –  Starting")
        self.logger.info("="*55)

        # ── 1. Indices ────────────────────────────────────────────────────────
        # NSE API confirmed working → use as primary
        nse_indices = self._run("NSE Indices (API)", self.nse.scrape_indices)
        all_records.extend(nse_indices)

        # Yahoo as supplement for indices (for Yahoo-only users)
        yahoo_indices = self._run("Yahoo Indices", self.yahoo.scrape_indices)
        all_records.extend(yahoo_indices)

        # ── 2. Gainers & Losers ───────────────────────────────────────────────
        nse_gainers = self._run("NSE Gainers (API)", self.nse.scrape_gainers)
        all_records.extend(nse_gainers)

        nse_losers  = self._run("NSE Losers (API)",  self.nse.scrape_losers)
        all_records.extend(nse_losers)

        # ── 3. Watchlist ──────────────────────────────────────────────────────
        # Try NSE first (most accurate), fall back to Yahoo, then Stooq
        nse_watch = self._run("NSE Watchlist (API)", self.nse.scrape_watchlist)
        if nse_watch:
            all_records.extend(nse_watch)
        else:
            self.logger.info("  ↩ NSE watchlist empty → trying Yahoo Finance…")
            yahoo_watch = self._run("Yahoo Watchlist", self.yahoo.scrape_watchlist)
            if yahoo_watch:
                all_records.extend(yahoo_watch)
            else:
                self.logger.info("  ↩ Yahoo watchlist empty → trying Stooq…")
                stooq_watch = self._run("Stooq Watchlist", self.stooq.scrape_watchlist)
                all_records.extend(stooq_watch)

        # ── 4. Stooq supplement ───────────────────────────────────────────────
        stooq_indices = self._run("Stooq Indices", self.stooq.scrape_indices)
        all_records.extend(stooq_indices)

        # ── Summary ───────────────────────────────────────────────────────────
        self.logger.info("\n" + "="*55)
        self.logger.info(f"  TOTAL RECORDS: {len(all_records)}")
        cat_counts: Dict[str, int] = {}
        for r in all_records:
            cat = r.get("Category", "Unknown")
            cat_counts[cat] = cat_counts.get(cat, 0) + 1
        for cat, cnt in sorted(cat_counts.items()):
            self.logger.info(f"  {cat:<20}: {cnt:>4} records")
        self.logger.info("="*55 + "\n")

        return all_records


# ─────────────────────────────────────────────────────────────────────────────
# Quick standalone test
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Testing Indian Stock Scraper…\n")
    cfg     = ScraperConfig()
    scraper = IndianStockScraper(cfg)
    records = scraper.run_all()

    print(f"\n{'='*60}")
    print(f"Total: {len(records)} records")
    print(f"{'='*60}")

    for r in records[:15]:
        print(
            f"  {r['Source']:<15} "
            f"{r['Category']:<12} "
            f"{r['Symbol']:<15} "
            f"₹{str(r['Price (₹)']):<12} "
            f"{r['Change (%)']}"
        )

    if not records:
        print("\n❌ No records! Check logs/scraper.log for details")
    else:
        print(f"\n✅ Scraper working! {len(records)} records collected")