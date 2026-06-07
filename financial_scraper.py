# financial_scraper.py
# Fixed based on ACTUAL diagnostic output:
# - Row labels end with "+" (expandable rows)
# - Values use Indian number format: ₹19,42,189Cr.
# - "Sales+" = Revenue, "OPM %" = EBITDA Margin
# - "Free Cash Flow" row exists directly in cash-flow section
# - top-ratios uses exact keys confirmed by diagnosis

import os, sys, re, time, json, random
from datetime import datetime
from typing   import Dict, List, Optional, Tuple, Any

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
# URLs (confirmed working from diagnosis)
# ─────────────────────────────────────────────────────────────────────────────

SCREENER_HOME        = "https://www.screener.in"
SCREENER_COMPANY_CON = "https://www.screener.in/company/{}/consolidated/"
SCREENER_COMPANY_STA = "https://www.screener.in/company/{}/"

# ─────────────────────────────────────────────────────────────────────────────
# Number cleaner (handles Indian format confirmed by diagnosis)
# ─────────────────────────────────────────────────────────────────────────────

def clean_indian_number(val: Any) -> Optional[float]:
    """
    Clean Indian formatted numbers from Screener.in
    
    Examples from diagnosis:
      '₹19,42,189Cr.'  → 1942189.0
      '₹1,435'         → 1435.0
      '10.5%'          → 10.5
      '24.0'           → 24.0
      '0.38%'          → 0.38
      '₹668'           → 668.0
      '-234'           → -234.0
      'Sales+'         → None (text, not number)
    """
    if val is None:
        return None

    s = str(val).strip()

    # Skip obvious non-numbers
    if not s or s in ["-", "--", "N/A", "NA", "", "None", "null", "0"]:
        return None

    # Remove the row-label "+" suffix used by Screener for expandable rows
    # e.g. "Sales+" → handled by caller, not this function

    # Remove currency symbol
    s = s.replace("₹", "").replace("Rs.", "").replace("Rs", "")

    # Remove "Cr." suffix (crores)
    s = re.sub(r'Cr\.?$', '', s, flags=re.IGNORECASE).strip()

    # Remove % sign (keep value)
    s = s.replace("%", "").strip()

    # Remove ALL commas (handles Indian format: 19,42,189 → 1942189)
    s = s.replace(",", "")

    # Remove trailing dots
    s = s.rstrip(".")

    # Handle parentheses as negative: (234) → -234
    m = re.match(r'^\(([0-9.]+)\)$', s)
    if m:
        s = "-" + m.group(1)

    if not s:
        return None

    try:
        return float(s)
    except ValueError:
        return None


def clean_label(label: str) -> str:
    """
    Remove trailing '+' from Screener expandable row labels.
    'Sales+'                      → 'Sales'
    'Cash from Operating Activity+' → 'Cash from Operating Activity'
    'Borrowings+'                 → 'Borrowings'
    """
    return label.rstrip("+").strip()


# ─────────────────────────────────────────────────────────────────────────────
# Session Manager
# ─────────────────────────────────────────────────────────────────────────────

class ScreenerSession:
    """
    HTTP session for Screener.in.
    Diagnosis confirmed no login wall — simple session works.
    """

    HEADERS = {
        "User-Agent"               : "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept"                   : "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language"          : "en-IN,en-GB;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept-Encoding"          : "gzip, deflate, br",
        "Connection"               : "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest"           : "document",
        "Sec-Fetch-Mode"           : "navigate",
        "Sec-Fetch-Site"           : "none",
        "Sec-Fetch-User"           : "?1",
        "Cache-Control"            : "max-age=0",
        "DNT"                      : "1",
    }

    def __init__(self, logger):
        self.logger  = logger
        self.session = self._make_session()
        self._warm_up()

    def _make_session(self) -> requests.Session:
        s = requests.Session()
        s.headers.update(self.HEADERS)
        retry = Retry(
            total            = 3,
            backoff_factor   = 2.0,
            status_forcelist = [429, 500, 502, 503, 504],
            allowed_methods  = ["GET"],
        )
        adapter = HTTPAdapter(max_retries=retry)
        s.mount("https://", adapter)
        s.mount("http://",  adapter)
        return s

    def _warm_up(self):
        """Visit homepage once to get cookies."""
        try:
            r = self.session.get(SCREENER_HOME, timeout=15)
            self.logger.info(
                f"Screener session: {r.status_code} | "
                f"cookies: {list(self.session.cookies.keys())}"
            )
            time.sleep(random.uniform(1.0, 2.0))
        except Exception as e:
            self.logger.warning(f"Screener warm-up error (OK): {e}")

    def get(self, url: str,
            retries: int = 3) -> Optional[requests.Response]:
        """Fetch URL with polite delay + retry."""
        for attempt in range(1, retries + 1):
            try:
                # Polite delay — Screener is free, respect it
                delay = random.uniform(2.5, 4.0)
                self.logger.debug(f"  Waiting {delay:.1f}s before request…")
                time.sleep(delay)

                self.session.headers["Referer"] = SCREENER_HOME
                resp = self.session.get(url, timeout=30)

                self.logger.info(
                    f"  [{attempt}] [{resp.status_code}] {url[-65:]}"
                )

                if resp.status_code == 200:
                    return resp

                elif resp.status_code == 404:
                    self.logger.warning(f"  404: Company not found at {url}")
                    return None

                elif resp.status_code == 429:
                    wait = int(resp.headers.get("Retry-After", 30))
                    self.logger.warning(
                        f"  Rate limited! Waiting {wait}s…"
                    )
                    time.sleep(wait)
                    continue

                elif resp.status_code in [403, 503]:
                    self.logger.warning(
                        f"  {resp.status_code}: Possible block. "
                        f"Re-initialising session…"
                    )
                    self._warm_up()
                    time.sleep(random.uniform(10, 20))
                    continue

            except requests.exceptions.ConnectionError as e:
                self.logger.warning(
                    f"  Connection error (attempt {attempt}): {e}"
                )
                time.sleep(5)
            except requests.exceptions.Timeout:
                self.logger.warning(f"  Timeout (attempt {attempt})")
                time.sleep(3)
            except Exception as e:
                self.logger.error(f"  Unexpected error: {e}")
                break

        return None


# ─────────────────────────────────────────────────────────────────────────────
# HTML Table Parser
# ─────────────────────────────────────────────────────────────────────────────

class ScreenerTableParser:
    """
    Parses Screener.in HTML tables.
    
    CONFIRMED from diagnosis:
    - Sections: profit-loss, balance-sheet, cash-flow, ratios, quarters
    - Row labels end with "+" for expandable rows
    - Columns are years: 'Mar 2020', 'Mar 2021', etc. + 'TTM'
    - 13 rows in P&L, 11 in BS, 7 in CF
    """

    def __init__(self, logger):
        self.logger = logger

    def parse_section(self, soup: BeautifulSoup,
                       section_id: str) -> Dict[str, Dict[str, str]]:
        """
        Parse one Screener section table.

        Returns:
            {
                'Sales': {'Mar 2022': '792756', 'Mar 2023': '876048', ...},
                'Operating Profit': {'Mar 2022': '93636', ...},
                ...
            }
        Note: row labels have "+" stripped automatically.
        """
        result = {}

        section = soup.find("section", {"id": section_id})
        if not section:
            self.logger.debug(f"  Section '{section_id}' not found")
            return result

        table = section.find("table")
        if not table:
            self.logger.debug(
                f"  Section '{section_id}': found but no table"
            )
            return result

        # ── Extract column headers (year periods) ─────────────────────────────
        headers = self._get_headers(table)
        if not headers:
            self.logger.debug(
                f"  Section '{section_id}': no headers found"
            )
            return result

        self.logger.debug(
            f"  '{section_id}' headers ({len(headers)}): {headers}"
        )

        # ── Extract data rows ─────────────────────────────────────────────────
        tbody = table.find("tbody") or table
        rows  = tbody.find_all("tr")

        for tr in rows:
            cells = tr.find_all("td")
            if not cells:
                continue

            # First cell = row label (strip + suffix)
            raw_label   = cells[0].get_text(strip=True)
            clean_lbl   = clean_label(raw_label)

            if not clean_lbl:
                continue

            # Remaining cells = data values per period
            row_data = {}
            for i, cell in enumerate(cells[1:], start=1):
                if i >= len(headers):
                    break
                period = headers[i]
                value  = cell.get_text(strip=True).replace("\xa0", "").strip()
                if value:
                    row_data[period] = value

            if row_data:
                result[clean_lbl] = row_data

        self.logger.debug(
            f"  '{section_id}' rows extracted: {list(result.keys())}"
        )
        return result

    def _get_headers(self, table: BeautifulSoup) -> List[str]:
        """
        Extract column headers from table.
        Screener uses <thead> with <th> elements.
        """
        headers = []

        # Try <thead>
        thead = table.find("thead")
        if thead:
            for th in thead.find_all("th"):
                t = th.get_text(strip=True)
                headers.append(t)
            if len(headers) > 1:
                return headers

        # Fallback: first <tr>
        rows = table.find_all("tr")
        if rows:
            for cell in rows[0].find_all(["th", "td"]):
                t = cell.get_text(strip=True)
                headers.append(t)

        return headers

    def get_last_n_years(self, row_data: Dict[str, str],
                          n: int = 3,
                          exclude_ttm: bool = True
                          ) -> Tuple[List[str], List[Optional[float]]]:
        """
        Get last N fiscal years from a row dict.
        Returns (periods, values) newest-first.

        Screener columns look like:
            'Mar 2019', 'Mar 2020', 'Mar 2021', 'Mar 2022', 'Mar 2023', 'TTM'
        """
        if not row_data:
            return [], []

        items = []
        for period, raw_val in row_data.items():
            # Skip TTM if requested
            if exclude_ttm and "TTM" in period.upper():
                continue

            # Extract year number
            year_match = re.search(r"(\d{4})", period)
            if not year_match:
                continue

            year  = int(year_match.group(1))
            value = clean_indian_number(raw_val)
            items.append((year, period, value))

        # Sort newest first
        items.sort(key=lambda x: x[0], reverse=True)
        items = items[:n]

        periods = [x[1] for x in items]
        values  = [x[2] for x in items]
        return periods, values

    def find_row(self, table_data: Dict[str, Dict],
                  *search_terms: str) -> Dict[str, str]:
        """
        Find a row by trying multiple search terms.
        Strips "+" from stored keys before comparison.

        Diagnosis confirmed actual row labels (after + strip):
        P&L: Sales, Expenses, Operating Profit, OPM %, Other Income,
             Interest, Depreciation, Profit before tax, Tax %, Net Profit,
             EPS in Rs
        BS:  Equity Capital, Reserves, Borrowings, Other Liabilities,
             Total Liabilities, Fixed Assets, CWIP, Investments,
             Other Assets, Total Assets
        CF:  Cash from Operating Activity, Cash from Investing Activity,
             Cash from Financing Activity, Net Cash Flow, Free Cash Flow
        """
        for term in search_terms:
            term_lower = term.lower().strip()

            # Exact match (case-insensitive)
            for key in table_data:
                if key.lower() == term_lower:
                    return table_data[key]

            # Partial match
            for key in table_data:
                if term_lower in key.lower() or key.lower() in term_lower:
                    return table_data[key]

        return {}


# ─────────────────────────────────────────────────────────────────────────────
# Ratio Parser
# ─────────────────────────────────────────────────────────────────────────────

class ScreenerRatioParser:
    """
    Parses Screener.in top-ratios section.

    CONFIRMED from diagnosis — exact keys:
    {
        'Market Cap'    : '₹19,42,189Cr.',
        'Current Price' : '₹1,435',
        'High / Low'    : '₹1,612/1,290',
        'Stock P/E'     : '24.0',
        'Book Value'    : '₹668',
        'Dividend Yield': '0.38%',
        'ROCE'          : '10.5%',
        'ROE'           : '9.25%',
        'Face Value'    : '₹10.0'
    }
    """

    # Map our metric names → Screener's confirmed label names
    CONFIRMED_LABELS = {
        "Market Cap"    : ["Market Cap"],
        "Current Price" : ["Current Price"],
        "High Low"      : ["High / Low"],
        "PE Ratio"      : ["Stock P/E", "P/E", "PE"],
        "Book Value"    : ["Book Value"],
        "Dividend Yield": ["Dividend Yield"],
        "ROCE"          : ["ROCE"],
        "ROE"           : ["ROE"],
        "Face Value"    : ["Face Value"],
        # These appear in the ratios section table (not top-ratios)
        "EPS"           : ["EPS in Rs", "EPS", "Earnings Per Share"],
        "Debt Equity"   : ["Debt / Equity", "Debt/Equity", "D/E Ratio"],
        "Current Ratio" : ["Current Ratio"],
        "ROA"           : ["Return on Assets", "ROA"],
    }

    def __init__(self, logger):
        self.logger = logger

    def parse_top_ratios(self, soup: BeautifulSoup) -> Dict[str, str]:
        """
        Extract top-ratios from the ul#top-ratios element.
        Confirmed working from diagnosis.
        """
        ratios = {}

        ratios_ul = soup.find("ul", {"id": "top-ratios"})
        if not ratios_ul:
            self.logger.warning("  top-ratios ul NOT found")
            return ratios

        for li in ratios_ul.find_all("li"):
            # Name span
            name_span = (
                li.find("span", {"class": "name"}) or
                li.find("span", attrs={
                    "class": lambda c: c and "name" in c
                })
            )
            # Value span — Screener uses 'nowrap' class for values
            value_span = (
                li.find("span", {"class": "nowrap"})  or
                li.find("span", {"class": "value"})   or
                li.find("span", attrs={
                    "class": lambda c: c and (
                        "nowrap" in c or "value" in c or "number" in c
                    )
                })
            )

            if name_span:
                name = name_span.get_text(strip=True)
                val  = value_span.get_text(strip=True) if value_span else ""
                if name:
                    ratios[name] = val

        self.logger.debug(
            f"  top-ratios extracted: {list(ratios.keys())}"
        )
        return ratios

    def parse_ratios_table(self, soup: BeautifulSoup) -> Dict[str, Dict]:
        """
        Parse the section#ratios table.
        Confirmed rows: Debtor Days, Inventory Days, Days Payable,
                        Cash Conversion Cycle, Working Capital Days,
                        ROCE %, ROE %  (last 2 rows often)
        """
        ratios = {}
        section = soup.find("section", {"id": "ratios"})
        if not section:
            return ratios

        table = section.find("table")
        if not table:
            return ratios

        # Headers
        headers = []
        thead   = table.find("thead")
        if thead:
            for th in thead.find_all("th"):
                headers.append(th.get_text(strip=True))

        tbody = table.find("tbody") or table
        for tr in tbody.find_all("tr"):
            cells = tr.find_all("td")
            if len(cells) < 2:
                continue
            label    = clean_label(cells[0].get_text(strip=True))
            row_data = {}
            for i, cell in enumerate(cells[1:], 1):
                if i < len(headers):
                    val = cell.get_text(strip=True).replace("\xa0", "")
                    if val:
                        row_data[headers[i]] = val
            if label and row_data:
                ratios[label] = row_data

        return ratios

    def get(self, ratios: Dict[str, str],
             metric_key: str) -> Optional[float]:
        """
        Get a cleaned numeric value for a metric.
        Uses CONFIRMED_LABELS mapping.
        """
        labels = self.CONFIRMED_LABELS.get(metric_key, [metric_key])
        for label in labels:
            # Exact match
            if label in ratios:
                return clean_indian_number(ratios[label])
            # Case-insensitive
            for k, v in ratios.items():
                if label.lower() == k.lower():
                    return clean_indian_number(v)
        return None

    def get_raw(self, ratios: Dict[str, str],
                 metric_key: str) -> str:
        """Get raw string value for a metric."""
        labels = self.CONFIRMED_LABELS.get(metric_key, [metric_key])
        for label in labels:
            if label in ratios:
                return ratios[label]
            for k, v in ratios.items():
                if label.lower() == k.lower():
                    return v
        return "N/A"


# ─────────────────────────────────────────────────────────────────────────────
# Main Financial Scraper
# ─────────────────────────────────────────────────────────────────────────────

class ScreenerFinancialScraper:
    """
    Production Screener.in scraper.

    Based on CONFIRMED diagnostic results:
    - P&L rows: Sales, Expenses, Operating Profit, OPM %, Net Profit, EPS
    - CF rows: Cash from Operating Activity, Free Cash Flow (DIRECT!)
    - BS rows: Equity Capital, Reserves, Borrowings, Fixed Assets
    - top-ratios: Market Cap, Current Price, Stock P/E, Book Value,
                  Dividend Yield, ROCE, ROE, Face Value
    """

    def __init__(self, config: ScraperConfig, logger=None):
        self.config       = config
        self.logger       = logger or get_logger(
            self.__class__.__name__, config
        )
        self.sess         = ScreenerSession(self.logger)
        self.tbl_parser   = ScreenerTableParser(self.logger)
        self.ratio_parser = ScreenerRatioParser(self.logger)

        # Stats
        self.success_count = 0
        self.fail_count    = 0

    def _fetch_html(self, symbol: str) -> Optional[Tuple[str, str]]:
        """
        Fetch company page HTML.
        Returns (html, url) or None.
        """
        for url_tmpl, label in [
            (SCREENER_COMPANY_CON, "consolidated"),
            (SCREENER_COMPANY_STA, "standalone"),
        ]:
            url  = url_tmpl.format(symbol)
            resp = self.sess.get(url)
            if resp is None:
                continue

            html = resp.text

            # Quick validation
            if len(html) < 10000:
                self.logger.debug(
                    f"  {label}: Page too small ({len(html)} chars)"
                )
                continue

            if "profit-loss" not in html:
                self.logger.debug(
                    f"  {label}: No financial data in page"
                )
                continue

            self.logger.info(
                f"  ✅ {symbol} ({label}): "
                f"{len(html):,} chars"
            )
            return html, url

        return None

    def scrape_company(self, symbol: str) -> Dict:
        """
        Scrape all financial metrics for one company.
        Returns a flat dict with all 13 metrics + 3-year data.
        """
        self.logger.info(f"\n  ── {symbol} ──────────────────────")

        # Fetch page
        fetch_result = self._fetch_html(symbol)
        if not fetch_result:
            self.logger.warning(f"  ✘ {symbol}: Fetch failed")
            self.fail_count += 1
            return self._empty(symbol, "Fetch failed")

        html, source_url = fetch_result
        soup = BeautifulSoup(html, "lxml")

        # ── Parse all sections ────────────────────────────────────────────────
        pnl = self.tbl_parser.parse_section(soup, "profit-loss")
        bs  = self.tbl_parser.parse_section(soup, "balance-sheet")
        cf  = self.tbl_parser.parse_section(soup, "cash-flow")

        self.logger.debug(
            f"  P&L rows: {list(pnl.keys())}\n"
            f"  BS rows:  {list(bs.keys())}\n"
            f"  CF rows:  {list(cf.keys())}"
        )

        # ── Parse ratios ──────────────────────────────────────────────────────
        top_ratios  = self.ratio_parser.parse_top_ratios(soup)
        ratio_table = self.ratio_parser.parse_ratios_table(soup)

        self.logger.debug(
            f"  top-ratios: {top_ratios}\n"
            f"  ratio_table rows: {list(ratio_table.keys())}"
        )

        # ─────────────────────────────────────────────────────────────────────
        # Extract each metric using CONFIRMED row labels
        # ─────────────────────────────────────────────────────────────────────

        # ── 1. Revenue (Sales) ────────────────────────────────────────────────
        # Confirmed label: "Sales" (stored after stripping "+")
        rev_row = self.tbl_parser.find_row(
            pnl, "Sales", "Revenue from Operations",
            "Net Sales", "Revenue", "Total Revenue",
        )
        rev_periods, rev_values = self.tbl_parser.get_last_n_years(rev_row, 3)
        self.logger.debug(
            f"  Revenue: periods={rev_periods} values={rev_values}"
        )

        # ── 2. Operating Profit (EBITDA) ──────────────────────────────────────
        # Confirmed label: "Operating Profit"
        ebitda_row = self.tbl_parser.find_row(
            pnl, "Operating Profit", "EBITDA",
            "PBDIT", "Earnings before interest",
        )
        ebitda_periods, ebitda_values = self.tbl_parser.get_last_n_years(
            ebitda_row, 3
        )

        # ── 3. OPM % (EBITDA Margin) ──────────────────────────────────────────
        # Confirmed label: "OPM %" 
        opm_row = self.tbl_parser.find_row(
            pnl, "OPM %", "OPM", "EBITDA Margin",
            "Operating Profit Margin", "Operating Margin",
        )
        _, opm_values = self.tbl_parser.get_last_n_years(opm_row, 3)
        ebitda_margin_y1 = opm_values[0] if opm_values else None

        # ── 4. Net Profit (PAT) ───────────────────────────────────────────────
        # Confirmed label: "Net Profit"
        pat_row = self.tbl_parser.find_row(
            pnl, "Net Profit", "PAT",
            "Profit after tax", "Net profit",
            "Profit After Tax",
        )
        pat_periods, pat_values = self.tbl_parser.get_last_n_years(pat_row, 3)

        # ── 5. EPS ────────────────────────────────────────────────────────────
        # Confirmed label: "EPS in Rs" (from P&L table)
        eps_row = self.tbl_parser.find_row(
            pnl, "EPS in Rs", "EPS", "Earnings Per Share",
            "Basic EPS", "Diluted EPS",
        )
        _, eps_pnl_values = self.tbl_parser.get_last_n_years(eps_row, 1)
        eps_from_pnl = eps_pnl_values[0] if eps_pnl_values else None

        # ── 6. Free Cash Flow (DIRECT from CF section) ───────────────────────
        # Confirmed label: "Free Cash Flow" — exists as its own row!
        fcf_row = self.tbl_parser.find_row(
            cf, "Free Cash Flow",
        )
        fcf_periods, fcf_values = self.tbl_parser.get_last_n_years(fcf_row, 3)

        # Fallback: calculate FCF = Operating CF - Capex
        if not fcf_values:
            ocf_row = self.tbl_parser.find_row(
                cf,
                "Cash from Operating Activity",
                "Cash from Operations",
                "Operating Activities",
            )
            cap_row = self.tbl_parser.find_row(
                cf,
                "Cash from Investing Activity",
                "Capital Expenditure",
                "Capex",
            )
            _, ocf_vals  = self.tbl_parser.get_last_n_years(ocf_row, 3)
            _, capex_vals= self.tbl_parser.get_last_n_years(cap_row, 3)
            fcf_values   = []
            for i in range(max(len(ocf_vals), len(capex_vals))):
                o = ocf_vals[i]   if i < len(ocf_vals)   else None
                c = capex_vals[i] if i < len(capex_vals) else None
                if o is not None and c is not None:
                    fcf_values.append(round(o - abs(c), 2))
                elif o is not None:
                    fcf_values.append(o)
                else:
                    fcf_values.append(None)
            fcf_periods = []

        # ── 7. Borrowings (for Debt/Equity calc) ─────────────────────────────
        # Confirmed label: "Borrowings"
        borrow_row = self.tbl_parser.find_row(
            bs, "Borrowings", "Total Debt", "Long Term Borrowings",
        )
        _, borrow_vals = self.tbl_parser.get_last_n_years(borrow_row, 1)

        # Reserves + Equity Capital = Equity
        equity_row = self.tbl_parser.find_row(bs, "Reserves")
        eq_cap_row = self.tbl_parser.find_row(bs, "Equity Capital")
        _, reserve_vals = self.tbl_parser.get_last_n_years(equity_row,  1)
        _, eqcap_vals   = self.tbl_parser.get_last_n_years(eq_cap_row,  1)

        # ── 8. Total Assets (for ROA) ─────────────────────────────────────────
        assets_row = self.tbl_parser.find_row(bs, "Total Assets")
        _, assets_vals = self.tbl_parser.get_last_n_years(assets_row, 1)

        # ─────────────────────────────────────────────────────────────────────
        # Get ratios from top-ratios (confirmed working)
        # ─────────────────────────────────────────────────────────────────────
        mktcap  = self.ratio_parser.get(top_ratios, "Market Cap")
        price   = self.ratio_parser.get(top_ratios, "Current Price")
        pe      = self.ratio_parser.get(top_ratios, "PE Ratio")
        bv      = self.ratio_parser.get(top_ratios, "Book Value")
        div_yld = self.ratio_parser.get(top_ratios, "Dividend Yield")
        roce    = self.ratio_parser.get(top_ratios, "ROCE")
        roe     = self.ratio_parser.get(top_ratios, "ROE")

        # High/Low — parse "₹1,612/1,290"
        high_price = low_price = None
        hl_raw = self.ratio_parser.get_raw(top_ratios, "High Low")
        if "/" in hl_raw:
            parts = hl_raw.split("/")
            high_price = clean_indian_number(parts[0])
            low_price  = clean_indian_number(parts[1])

        # ─────────────────────────────────────────────────────────────────────
        # Compute derived metrics
        # ─────────────────────────────────────────────────────────────────────

        # Revenue Growth % (Y1 vs Y2)
        rev_growth = None
        if (len(rev_values) >= 2 and
                rev_values[0] is not None and
                rev_values[1] is not None and
                rev_values[1] != 0):
            rev_growth = round(
                (rev_values[0] - rev_values[1]) / abs(rev_values[1]) * 100,
                2
            )

        # PAT Margin %
        pat_margin = None
        if (pat_values and rev_values and
                pat_values[0] is not None and
                rev_values[0] is not None and
                rev_values[0] != 0):
            pat_margin = round(
                pat_values[0] / rev_values[0] * 100, 2
            )

        # EBITDA Margin % (calculated if OPM % row found numeric)
        if ebitda_margin_y1 is None:
            if (ebitda_values and rev_values and
                    ebitda_values[0] is not None and
                    rev_values[0] is not None and
                    rev_values[0] != 0):
                ebitda_margin_y1 = round(
                    ebitda_values[0] / rev_values[0] * 100, 2
                )

        # ROA % = Net Profit / Total Assets
        roa = None
        if (pat_values and assets_vals and
                pat_values[0] is not None and
                assets_vals[0] is not None and
                assets_vals[0] != 0):
            roa = round(pat_values[0] / assets_vals[0] * 100, 2)

        # Debt/Equity (if not in top-ratios)
        de_ratio = None
        if borrow_vals and reserve_vals and eqcap_vals:
            debt   = borrow_vals[0]
            equity = (reserve_vals[0] or 0) + (eqcap_vals[0] or 0)
            if debt is not None and equity and equity != 0:
                de_ratio = round(debt / equity, 2)

        # EPS — prefer P&L table value, fallback: Price / PE
        eps_final = eps_from_pnl
        if eps_final is None and price and pe and pe != 0:
            try:
                eps_final = round(price / pe, 2)
            except (TypeError, ZeroDivisionError):
                pass

        # Current Ratio — from balance sheet
        current_assets      = None
        current_liabilities = None
        # Try to find in BS
        ca_row = self.tbl_parser.find_row(
            bs, "Other Assets", "Current Assets",
            "Trade Receivables",
        )
        cl_row = self.tbl_parser.find_row(
            bs, "Other Liabilities", "Current Liabilities",
            "Trade Payables",
        )
        _, ca_vals = self.tbl_parser.get_last_n_years(ca_row, 1)
        _, cl_vals = self.tbl_parser.get_last_n_years(cl_row, 1)
        current_ratio = None
        if ca_vals and cl_vals and ca_vals[0] and cl_vals[0] and cl_vals[0] != 0:
            current_ratio = round(ca_vals[0] / cl_vals[0], 2)

        # ─────────────────────────────────────────────────────────────────────
        # Build final record
        # ─────────────────────────────────────────────────────────────────────
        record = {
            # ── Identity ──────────────────────────────────────────────────────
            "Symbol"               : symbol,
            "Scraped At"           : datetime.now().strftime("%Y-%m-%d %H:%M"),
            "Source URL"           : source_url,
            "Data Status"          : "OK",

            # ── Market Data (from top-ratios, confirmed) ──────────────────────
            "Current Price (₹)"    : price,
            "Market Cap (Cr)"      : mktcap,
            "52W High (₹)"         : high_price,
            "52W Low (₹)"          : low_price,
            "Book Value (₹)"       : bv,
            "Face Value (₹)"       : self.ratio_parser.get(
                                        top_ratios, "Face Value"),

            # ── GROWTH ────────────────────────────────────────────────────────
            "Revenue Y1 Period"    : rev_periods[0] if rev_periods else "N/A",
            "Revenue Y1 (Cr)"      : rev_values[0]  if rev_values  else None,
            "Revenue Y2 Period"    : rev_periods[1] if len(rev_periods) > 1 else "N/A",
            "Revenue Y2 (Cr)"      : rev_values[1]  if len(rev_values) > 1 else None,
            "Revenue Y3 Period"    : rev_periods[2] if len(rev_periods) > 2 else "N/A",
            "Revenue Y3 (Cr)"      : rev_values[2]  if len(rev_values) > 2 else None,
            "Revenue Growth (%)"   : rev_growth,

            # ── PROFITABILITY ─────────────────────────────────────────────────
            "EBITDA Y1 Period"     : ebitda_periods[0] if ebitda_periods else "N/A",
            "EBITDA Y1 (Cr)"       : ebitda_values[0]  if ebitda_values  else None,
            "EBITDA Y2 (Cr)"       : ebitda_values[1]  if len(ebitda_values) > 1 else None,
            "EBITDA Y3 (Cr)"       : ebitda_values[2]  if len(ebitda_values) > 2 else None,
            "EBITDA Margin (%)"    : ebitda_margin_y1,

            "PAT Y1 Period"        : pat_periods[0] if pat_periods else "N/A",
            "PAT Y1 (Cr)"          : pat_values[0]  if pat_values  else None,
            "PAT Y2 (Cr)"          : pat_values[1]  if len(pat_values) > 1 else None,
            "PAT Y3 (Cr)"          : pat_values[2]  if len(pat_values) > 2 else None,
            "PAT Margin (%)"       : pat_margin,

            # ── RETURNS ───────────────────────────────────────────────────────
            # Confirmed from top-ratios: "ROCE": "10.5%", "ROE": "9.25%"
            "ROE (%)"              : roe,
            "ROCE (%)"             : roce,
            "ROA (%)"              : roa,

            # ── VALUATION ─────────────────────────────────────────────────────
            "EPS (₹)"              : eps_final,
            "P/E Ratio"            : pe,
            "Dividend Yield (%)"   : div_yld,

            # ── FINANCIAL HEALTH ──────────────────────────────────────────────
            "Debt to Equity"       : de_ratio,
            "Current Ratio"        : current_ratio,

            # ── CASH FLOW ─────────────────────────────────────────────────────
            # Confirmed: "Free Cash Flow" row exists directly!
            "FCF Y1 Period"        : fcf_periods[0] if fcf_periods else "N/A",
            "FCF Y1 (Cr)"          : fcf_values[0]  if fcf_values  else None,
            "FCF Y2 (Cr)"          : fcf_values[1]  if len(fcf_values) > 1 else None,
            "FCF Y3 (Cr)"          : fcf_values[2]  if len(fcf_values) > 2 else None,
        }

        # Check if we got meaningful data
        key_metrics = [
            "Revenue Y1 (Cr)", "PAT Y1 (Cr)",
            "EBITDA Y1 (Cr)", "ROE (%)",
        ]
        got_data = any(
            record.get(k) is not None for k in key_metrics
        )

        if got_data:
            self.success_count += 1
            self.logger.info(
                f"  ✅ {symbol}: "
                f"Rev=₹{record.get('Revenue Y1 (Cr)','?'):} Cr | "
                f"PAT=₹{record.get('PAT Y1 (Cr)','?')} Cr | "
                f"ROE={record.get('ROE (%)','?')}% | "
                f"PE={record.get('P/E Ratio','?')}"
            )
        else:
            self.fail_count += 1
            record["Data Status"] = "No numeric data extracted"
            self.logger.warning(
                f"  ⚠  {symbol}: Page fetched but no numeric data"
            )

        return record

    def _empty(self, symbol: str, reason: str) -> Dict:
        """Return empty record for failed fetch."""
        fields = [
            "Current Price (₹)","Market Cap (Cr)","52W High (₹)","52W Low (₹)",
            "Book Value (₹)","Face Value (₹)",
            "Revenue Y1 Period","Revenue Y1 (Cr)",
            "Revenue Y2 Period","Revenue Y2 (Cr)",
            "Revenue Y3 Period","Revenue Y3 (Cr)",
            "Revenue Growth (%)",
            "EBITDA Y1 Period","EBITDA Y1 (Cr)",
            "EBITDA Y2 (Cr)","EBITDA Y3 (Cr)","EBITDA Margin (%)",
            "PAT Y1 Period","PAT Y1 (Cr)",
            "PAT Y2 (Cr)","PAT Y3 (Cr)","PAT Margin (%)",
            "ROE (%)","ROCE (%)","ROA (%)",
            "EPS (₹)","P/E Ratio","Dividend Yield (%)",
            "Debt to Equity","Current Ratio",
            "FCF Y1 Period","FCF Y1 (Cr)",
            "FCF Y2 (Cr)","FCF Y3 (Cr)",
        ]
        rec = {
            "Symbol"     : symbol,
            "Scraped At" : datetime.now().strftime("%Y-%m-%d %H:%M"),
            "Source URL" : "",
            "Data Status": reason,
        }
        for f in fields:
            rec[f] = None
        return rec

    def scrape_multiple(self,
                         symbols: List[str],
                         progress_cb = None) -> List[Dict]:
        """Scrape multiple companies."""
        results = []
        total   = len(symbols)

        self.logger.info(
            f"\nScreener: Scraping {total} companies…"
        )

        for i, sym in enumerate(symbols, 1):
            if progress_cb:
                progress_cb(i, total, sym)

            rec = self.scrape_company(sym)
            results.append(rec)

            # Cool-down every 15 requests
            if i % 15 == 0 and i < total:
                pause = random.uniform(10, 20)
                self.logger.info(
                    f"\n  [{i}/{total}] Cooling down {pause:.0f}s… "
                    f"(✅{self.success_count} ✘{self.fail_count})\n"
                )
                time.sleep(pause)

        self.logger.info(
            f"\n  Complete: {self.success_count}/{total} successful, "
            f"{self.fail_count} failed"
        )
        return results


# ─────────────────────────────────────────────────────────────────────────────
# Quick verification test
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from config import ScraperConfig

    cfg     = ScraperConfig()
    scraper = ScreenerFinancialScraper(cfg)

    print("\n" + "="*60)
    print("  Screener.in Financial Scraper — Verification Test")
    print("="*60)

    for sym in ["RELIANCE", "TCS"]:
        data = scraper.scrape_company(sym)

        print(f"\n{'─'*55}")
        print(f"  {sym}  |  {data['Data Status']}")
        print(f"{'─'*55}")

        DISPLAY = [
            ("Revenue Y1 Period",  "Period"),
            ("Revenue Y1 (Cr)",    "Revenue Y1"),
            ("Revenue Y2 (Cr)",    "Revenue Y2"),
            ("Revenue Y3 (Cr)",    "Revenue Y3"),
            ("Revenue Growth (%)", "Revenue Growth"),
            ("EBITDA Y1 (Cr)",     "EBITDA Y1"),
            ("EBITDA Margin (%)",  "EBITDA Margin"),
            ("PAT Y1 (Cr)",        "PAT Y1"),
            ("PAT Y2 (Cr)",        "PAT Y2"),
            ("PAT Y3 (Cr)",        "PAT Y3"),
            ("PAT Margin (%)",     "PAT Margin"),
            ("ROE (%)",            "ROE"),
            ("ROCE (%)",           "ROCE"),
            ("ROA (%)",            "ROA"),
            ("EPS (₹)",            "EPS"),
            ("P/E Ratio",          "P/E"),
            ("Debt to Equity",     "D/E Ratio"),
            ("Current Ratio",      "Current Ratio"),
            ("FCF Y1 (Cr)",        "FCF Y1"),
            ("FCF Y2 (Cr)",        "FCF Y2"),
            ("FCF Y3 (Cr)",        "FCF Y3"),
            ("Market Cap (Cr)",    "Market Cap"),
            ("Current Price (₹)",  "Price"),
        ]

        for key, label in DISPLAY:
            val = data.get(key)
            if val is not None:
                if isinstance(val, float):
                    print(f"  {label:<22}: {val:>12,.2f}")
                else:
                    print(f"  {label:<22}: {val}")

    print(f"\n{'='*60}")
    print(
        f"  Success: {scraper.success_count} | "
        f"Failed: {scraper.fail_count}"
    )
    print("="*60)