# sector_ui.py
# Complete self-contained file with ALL imports at the top

import os
import sys
import time
import random
import re
import logging
from datetime import datetime
from typing   import Dict, List, Optional, Tuple

# ── Path fix ──────────────────────────────────────────────────────────────────
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
if _THIS_DIR not in sys.path:
    sys.path.insert(0, _THIS_DIR)

# ── Third-party imports (must come BEFORE any usage) ─────────────────────────
import pandas   as pd
import numpy    as np
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from rich.console  import Console
from rich.panel    import Panel
from rich.table    import Table
from rich.prompt   import Confirm, Prompt, IntPrompt, FloatPrompt
from rich.progress import (
    Progress, SpinnerColumn,
    BarColumn, TextColumn, TaskProgressColumn,
)
from rich      import box
from rich.text import Text

# ── Local imports ─────────────────────────────────────────────────────────────
from config       import ScraperConfig
from logger_setup import get_logger

console = Console()

# ── sector_data imports with fallback ─────────────────────────────────────────
try:
    from sector_data import (
        SECTORS,
        SECTOR_COMPANIES,
        get_sector_companies,
        filter_by_price,
        METRIC_BENCHMARKS,
        SECTOR_PE_BENCHMARKS,
    )
except ImportError as e:
    console.print(f"[yellow]Warning: sector_data.py not found: {e}[/yellow]")
    SECTORS = {
        "1" : "Energy",
        "2" : "Materials",
        "3" : "Industrials",
        "4" : "Consumer Discretionary",
        "5" : "Consumer Staples",
        "6" : "Healthcare",
        "7" : "Financials",
        "8" : "Information Technology",
        "9" : "Communication Services",
        "10": "Utilities",
        "11": "Real Estate",
    }
    SECTOR_COMPANIES     = {}
    METRIC_BENCHMARKS    = {}
    SECTOR_PE_BENCHMARKS = {}

    def get_sector_companies(sector, top_n=50):
        return {}

    def filter_by_price(companies, prices, mode,
                        value=None, min_price=None, max_price=None):
        return companies

# ── sector_analyzer imports with fallback ─────────────────────────────────────
try:
    from sector_analyzer import SectorAnalyzer, normalise_columns
except ImportError as e:
    console.print(
        f"[yellow]Warning: sector_analyzer.py not found: {e}[/yellow]"
    )

    def normalise_columns(df):
        return df

    class SectorAnalyzer:
        def __init__(self):
            pass
        def analyze(self, fin_df, price_df, sector):
            return fin_df if fin_df is not None else pd.DataFrame()
        def show_metric_table(self, df, sector, top_n=20):
            console.print(df.head(top_n).to_string())
        def export_analysis(self, df, sector, path):
            df.to_excel(path, index=False)
            console.print(f"  Saved → {path}")


# ─────────────────────────────────────────────────────────────────────────────
# NSE session builder
# ─────────────────────────────────────────────────────────────────────────────

def _make_nse_session(logger) -> requests.Session:
    """
    Build a requests.Session for NSE India API.
    Homepage returns 403 — that is expected and OK.
    The /api/ endpoints still return 200.
    """
    nse_headers = {
        "User-Agent"     : (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept"         : "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Referer"        : "https://www.nseindia.com/",
        "sec-fetch-dest" : "empty",
        "sec-fetch-mode" : "cors",
        "sec-fetch-site" : "same-origin",
        "Connection"     : "keep-alive",
    }

    session = requests.Session()
    session.headers.update(nse_headers)

    retry_strategy = Retry(
        total            = 3,
        backoff_factor   = 1.5,
        status_forcelist = [429, 500, 502, 503, 504],
        allowed_methods  = ["GET"],
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)
    session.mount("http://",  adapter)

    # Visit homepage to collect cookies (403 is normal here)
    try:
        r = session.get(
            "https://www.nseindia.com", timeout=15
        )
        logger.info(
            f"NSE home: {r.status_code} "
            f"(403=expected, cookies: {list(r.cookies.keys())})"
        )
    except Exception as exc:
        logger.warning(f"NSE home warning (continuing): {exc}")

    # Inject required cookie manually
    session.cookies.set("AKA_A2", "A", domain=".nseindia.com")
    time.sleep(1.5)
    return session


# ─────────────────────────────────────────────────────────────────────────────
# NSE price fetcher
# ─────────────────────────────────────────────────────────────────────────────

def fetch_nse_price(
    session: requests.Session,
    symbol:  str,
    logger,
) -> Optional[Dict]:
    """
    Fetch live stock quote from NSE API.
    Returns a dict with Title Case keys, or None on failure.
    """
    url = f"https://www.nseindia.com/api/quote-equity?symbol={symbol}"
    try:
        time.sleep(random.uniform(0.6, 1.2))
        resp = session.get(url, timeout=20)
        logger.debug(f"  NSE [{resp.status_code}] {symbol}")

        if resp.status_code != 200:
            return None

        data       = resp.json()
        price_info = data.get("priceInfo",             {})
        meta       = data.get("metadata",               {})
        week_hl    = price_info.get("weekHighLow",      {})
        intra      = price_info.get("intraDayHighLow",  {})
        trade      = (
            data.get("marketDeptOrderBook", {})
                .get("tradeInfo", {})
        )

        ltp = price_info.get("lastPrice", None)
        if ltp is None:
            return None

        return {
            "Symbol"         : symbol,
            "Company"        : meta.get("companyName", symbol),
            "Price (₹)"      : float(ltp),
            "Open (₹)"       : float(price_info.get("open",          0) or 0),
            "High (₹)"       : float(intra.get("max",                0) or 0),
            "Low (₹)"        : float(intra.get("min",                0) or 0),
            "Prev Close (₹)" : float(price_info.get("previousClose", 0) or 0),
            "Change (₹)"     : float(price_info.get("change",        0) or 0),
            "Change (%)"     : float(price_info.get("pChange",       0) or 0),
            "Volume"         : trade.get("totalTradedVolume",         0),
            "52W High (₹)"   : float(week_hl.get("max",              0) or 0),
            "52W Low (₹)"    : float(week_hl.get("min",              0) or 0),
        }

    except Exception as exc:
        logger.debug(f"  NSE price error [{symbol}]: {exc}")
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Helper: safe DataFrame check
# ─────────────────────────────────────────────────────────────────────────────

def _safe_df(df: Optional[pd.DataFrame]) -> pd.DataFrame:
    """
    Return df if it is a non-empty DataFrame, else return empty DataFrame.
    NEVER use  'df or pd.DataFrame()'  with pandas — it raises ValueError.
    """
    if df is None:
        return pd.DataFrame()
    if not isinstance(df, pd.DataFrame):
        return pd.DataFrame()
    if df.empty:
        return pd.DataFrame()
    return df


# ─────────────────────────────────────────────────────────────────────────────
# SectorUI
# ─────────────────────────────────────────────────────────────────────────────

class SectorUI:
    """
    Interactive terminal UI for sector-based stock analysis.

    Public entry point
    ------------------
    ui = SectorUI(config)
    ui.run()
    """

    def __init__(self, config: ScraperConfig):
        self.config       = config
        self.logger       = get_logger(self.__class__.__name__, config)
        self.analyzer     = SectorAnalyzer()
        self.out_dir      = os.path.join(config.output_dir, "sectors")
        os.makedirs(self.out_dir, exist_ok=True)

        # NSE HTTP session
        self.nse_session : requests.Session       = _make_nse_session(self.logger)

        # Lazy financial scraper (created on first use)
        self._fin_scraper                         = None

        # Session state — always use _safe_df() before accessing
        self.price_df    : Optional[pd.DataFrame] = None
        self.fin_df      : Optional[pd.DataFrame] = None
        self.sector      : str                    = ""

    # ── Lazy financial scraper ────────────────────────────────────────────────

    def _get_fin_scraper(self):
        """Create ScreenerFinancialScraper on first call."""
        if self._fin_scraper is None:
            try:
                from financial_scraper import ScreenerFinancialScraper
                self._fin_scraper = ScreenerFinancialScraper(
                    self.config, self.logger
                )
            except ImportError as exc:
                self.logger.error(
                    f"financial_scraper.py not found: {exc}"
                )
                raise
        return self._fin_scraper

    # ─────────────────────────────────────────────────────────────────────────
    # run()  ← PUBLIC ENTRY POINT called from main.py
    # ─────────────────────────────────────────────────────────────────────────

    def run(self):
        """Main loop. Called from main.py as:  sector_ui.run()"""
        console.print(Panel(
            Text.assemble(
                ("  🏭  Sector Analysis Studio\n\n",      "bold white"),
                ("  11 GICS Sectors | Up to 50 companies\n","cyan"),
                ("  13 Financial Metrics + Benchmarks\n",  "green"),
                ("  Price filters: High / Low / Range",    "yellow"),
            ),
            border_style="bright_blue",
            padding=(1, 4),
        ))

        while True:
            self._show_main_menu()
            choice = Prompt.ask("  Choice", default="Q").strip().upper()

            if choice == "1":
                sector = self._select_sector()
                if sector:
                    self._run_analysis(sector)

            elif choice == "2":
                console.print("\n  Select FIRST sector:")
                s1 = self._select_sector()
                if not s1:
                    continue
                console.print("\n  Select SECOND sector:")
                s2 = self._select_sector()
                if s2:
                    self._compare_sectors(s1, s2)

            elif choice == "3":
                fin = _safe_df(self.fin_df)
                if fin.empty:
                    console.print(
                        "  [yellow]No session data. Run option 1 first.[/yellow]"
                    )
                    continue
                top = IntPrompt.ask(
                    "  Show top N companies", default=10
                )
                analyzed = self.analyzer.analyze(
                    fin, _safe_df(self.price_df), self.sector
                )
                if not analyzed.empty:
                    self.analyzer.show_metric_table(
                        analyzed, self.sector, int(top)
                    )
                else:
                    console.print(
                        "  [yellow]Analysis returned empty.[/yellow]"
                    )

            elif choice == "4":
                self._show_benchmark_reference()

            elif choice == "5":
                fin = _safe_df(self.fin_df)
                if fin.empty:
                    console.print(
                        "  [yellow]No data to export. "
                        "Run option 1 first.[/yellow]"
                    )
                    continue
                price    = _safe_df(self.price_df)
                analyzed = self.analyzer.analyze(
                    fin, price, self.sector
                )
                self._save(self.sector, price, fin, analyzed)

            elif choice == "Q":
                console.print(
                    "  [cyan]Returning to main menu…[/cyan]\n"
                )
                break

            else:
                console.print(
                    f"  [red]Unknown choice '{choice}'. "
                    "Try again.[/red]"
                )

    # ─────────────────────────────────────────────────────────────────────────
    # Menu
    # ─────────────────────────────────────────────────────────────────────────

    def _show_main_menu(self):
        p_rows = len(_safe_df(self.price_df))
        f_rows = len(_safe_df(self.fin_df))

        console.print(Panel(
            f"[bold cyan]🏭 Sector Studio[/bold cyan]  │  "
            f"[dim]Session: {p_rows} price rows, "
            f"{f_rows} fin rows, "
            f"sector={self.sector or 'None'}[/dim]",
            border_style="blue",
            padding=(0, 2),
        ))

        items = [
            ("1", "Analyze a sector  (scrape + 13 metrics + benchmarks)"),
            ("2", "Compare two sectors side-by-side"),
            ("3", "View last session results"),
            ("4", "Show benchmark reference table"),
            ("5", "Export last session to Excel"),
            ("Q", "Back to main menu"),
        ]
        for key, label in items:
            colour = "bold green" if key == "Q" else "bold yellow"
            console.print(f"  [{colour}]{key}[/]  {label}")
        console.print()

    # ─────────────────────────────────────────────────────────────────────────
    # Sector selection
    # ─────────────────────────────────────────────────────────────────────────

    def _select_sector(self) -> Optional[str]:
        """Show sector picker. Returns sector name or None."""
        examples = {
            "Energy"                 : "RELIANCE, NTPC, ONGC, BPCL",
            "Materials"              : "TATASTEEL, ULTRACEMCO, PIDILITIND",
            "Industrials"            : "LT, SIEMENS, HAL, ADANIPORTS",
            "Consumer Discretionary" : "MARUTI, TATAMOTORS, TITAN, ZOMATO",
            "Consumer Staples"       : "HINDUNILVR, ITC, NESTLEIND",
            "Healthcare"             : "SUNPHARMA, DRREDDY, CIPLA",
            "Financials"             : "HDFCBANK, ICICIBANK, BAJFINANCE",
            "Information Technology" : "TCS, INFY, WIPRO, HCLTECH",
            "Communication Services" : "BHARTIARTL, ZOMATO, SUNTVNET",
            "Utilities"              : "NTPC, POWERGRID, ADANIGREEN",
            "Real Estate"            : "DLF, GODREJPROP, PHOENIXLTD",
        }

        console.print(Panel(
            "[bold white]🏭 Select Sector[/bold white]",
            border_style="bright_blue",
        ))

        t = Table(
            box=box.ROUNDED,
            border_style="blue",
            header_style="bold white on navy_blue",
            show_lines=True,
        )
        t.add_column("#",          width=4,  style="bold yellow")
        t.add_column("Sector",     width=28, style="bold white")
        t.add_column("In DB",      width=8,  justify="right", style="green")
        t.add_column("Key Stocks",           style="dim")

        for num, sector in SECTORS.items():
            count = len(SECTOR_COMPANIES.get(sector, {}))
            t.add_row(
                num, sector,
                str(count),
                examples.get(sector, ""),
            )

        console.print(t)
        console.print(
            "  [bold yellow]0[/bold yellow]  Cancel / back\n"
        )

        choice = Prompt.ask("  Sector number", default="0").strip()

        if choice == "0":
            return None
        if choice not in SECTORS:
            console.print(
                f"  [red]Invalid choice '{choice}'[/red]"
            )
            return None
        return SECTORS[choice]

    # ─────────────────────────────────────────────────────────────────────────
    # Configuration helpers
    # ─────────────────────────────────────────────────────────────────────────

    def _select_top_n(self, sector: str) -> int:
        total = len(SECTOR_COMPANIES.get(sector, {}))
        console.print(
            f"\n  [bold]{sector}[/bold] has "
            f"[cyan]{total}[/cyan] companies in database."
        )
        n = IntPrompt.ask(
            "  Top N companies (sorted by market cap)",
            default=min(20, total),
        )
        return max(1, min(int(n), total))

    def _select_price_filter(
        self, sector: str
    ) -> Tuple[str, dict]:
        console.print(Panel(
            f"[bold cyan]💰 Price Range Filter — {sector}[/bold cyan]",
            border_style="cyan",
        ))
        options = [
            ("1", "Top 50 by HIGHEST price"),
            ("2", "Top 50 by LOWEST  price"),
            ("3", "Custom range  (₹ min – ₹ max)"),
            ("4", "Top N highest price"),
            ("5", "Top N lowest  price"),
            ("6", "No filter — use all companies"),
        ]
        for k, v in options:
            console.print(f"  [bold yellow]{k}[/bold yellow]  {v}")
        console.print()

        ch = Prompt.ask(
            "  Choice",
            choices=[o[0] for o in options],
            default="6",
        )

        if ch == "1":
            return "top_high", {"value": 50}
        elif ch == "2":
            return "top_low",  {"value": 50}
        elif ch == "3":
            lo = FloatPrompt.ask("  Min price (₹)", default=0.0)
            hi = FloatPrompt.ask("  Max price (₹)", default=100_000.0)
            return "range", {"min_price": float(lo), "max_price": float(hi)}
        elif ch == "4":
            n = IntPrompt.ask("  Top N (highest)", default=20)
            return "top_high", {"value": int(n)}
        elif ch == "5":
            n = IntPrompt.ask("  Top N (lowest)",  default=20)
            return "top_low",  {"value": int(n)}
        else:
            return "all", {}

    def _select_data_options(self) -> Tuple[bool, bool]:
        console.print(Panel(
            "[bold cyan]📦 What data to fetch?[/bold cyan]",
            border_style="cyan",
        ))
        console.print("  [bold yellow]1[/bold yellow]  "
                      "Live prices only  (~1 min)")
        console.print("  [bold yellow]2[/bold yellow]  "
                      "Financial data only  (13 metrics from Screener.in)")
        console.print("  [bold yellow]3[/bold yellow]  "
                      "Prices + Financials  (recommended)\n")

        ch = Prompt.ask(
            "  Choice", choices=["1","2","3"], default="3"
        )
        return (ch in ("1","3")), (ch in ("2","3"))

    # ─────────────────────────────────────────────────────────────────────────
    # Main analysis pipeline
    # ─────────────────────────────────────────────────────────────────────────

    def _run_analysis(self, sector: str):
        """configure → scrape → normalise → filter → analyze → display → save"""

        top_n                    = self._select_top_n(sector)
        companies                = get_sector_companies(sector, top_n)
        price_mode, price_params = self._select_price_filter(sector)
        fetch_price, fetch_fin   = self._select_data_options()

        console.print(Panel(
            f"[bold green]🚀 Starting: {sector}[/bold green]\n"
            f"  Companies     : [cyan]{len(companies)}[/cyan]\n"
            f"  Price filter  : [cyan]{price_mode}[/cyan]\n"
            f"  Fetch prices  : [cyan]{fetch_price}[/cyan]  │  "
            f"Fetch financials: [cyan]{fetch_fin}[/cyan]",
            border_style="green",
        ))

        price_records : List[Dict] = []
        fin_records   : List[Dict] = []
        symbols                    = list(companies.keys())

        # ── Scrape loop ───────────────────────────────────────────────────────
        with Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console,
            transient=False,
        ) as progress:
            task = progress.add_task(
                f"Scraping {sector}…", total=len(symbols)
            )

            for i, sym in enumerate(symbols, 1):
                info = companies[sym]
                progress.update(
                    task,
                    description=(
                        f"[bold blue]({i}/{len(symbols)}) "
                        f"{sym} — "
                        f"{str(info.get('name',''))[:22]}"
                    ),
                    completed=i,
                )

                # Live price from NSE
                if fetch_price:
                    row = fetch_nse_price(
                        self.nse_session, sym, self.logger
                    )
                    if row:
                        row["Sector"]          = sector
                        row["Sub-Sector"]      = info.get("sub", "")
                        row["Market Cap (Cr)"] = info.get("cap",  0)
                        price_records.append(row)
                    else:
                        self.logger.debug(f"  ⚠  {sym}: no price data")

                # Financials from Screener.in
                if fetch_fin:
                    try:
                        scraper = self._get_fin_scraper()
                        fin     = scraper.scrape_company(sym)
                        fin["Sector"]     = sector
                        fin["Sub-Sector"] = info.get("sub", "")
                        fin["Company"]    = info.get("name", sym)
                        fin_records.append(fin)
                    except Exception as exc:
                        self.logger.error(
                            f"  Financial scrape error [{sym}]: {exc}"
                        )

        # ── Build DataFrames ──────────────────────────────────────────────────
        price_df = (
            pd.DataFrame(price_records)
            if price_records else pd.DataFrame()
        )
        fin_df = (
            pd.DataFrame(fin_records)
            if fin_records else pd.DataFrame()
        )

        console.print(
            f"\n  Price records     : [cyan]{len(price_df)}[/cyan]\n"
            f"  Financial records : [cyan]{len(fin_df)}[/cyan]"
        )

        # ── Normalise column names ────────────────────────────────────────────
        price_df = normalise_columns(price_df)
        fin_df   = normalise_columns(fin_df)

        # ── Apply price filter ────────────────────────────────────────────────
        has_price = (
            not price_df.empty
            and "Symbol"    in price_df.columns
            and "Price (₹)" in price_df.columns
        )

        if price_mode != "all" and has_price:
            prices_dict = dict(
                zip(
                    price_df["Symbol"],
                    pd.to_numeric(
                        price_df["Price (₹)"], errors="coerce"
                    ),
                )
            )
            filtered_cos = filter_by_price(
                companies, prices_dict, price_mode,
                value     = price_params.get("value"),
                min_price = price_params.get("min_price"),
                max_price = price_params.get("max_price"),
            )
            keep   = list(filtered_cos.keys())
            before = len(price_df)

            price_df = price_df[
                price_df["Symbol"].isin(keep)
            ].reset_index(drop=True)

            if not fin_df.empty and "Symbol" in fin_df.columns:
                fin_df = fin_df[
                    fin_df["Symbol"].isin(keep)
                ].reset_index(drop=True)

            console.print(
                f"  [cyan]Price filter [{price_mode}]: "
                f"{before} → {len(price_df)} companies[/cyan]"
            )

        # ── Analyze + display ─────────────────────────────────────────────────
        analyzed_df = pd.DataFrame()

        if not fin_df.empty:
            analyzed_df = self.analyzer.analyze(
                fin_df, _safe_df(price_df), sector
            )
            if not analyzed_df.empty:
                top_show = IntPrompt.ask(
                    "\n  Companies to show in stats table",
                    default=min(15, len(analyzed_df)),
                )
                self.analyzer.show_metric_table(
                    analyzed_df, sector, int(top_show)
                )
            else:
                console.print(
                    "  [yellow]Analysis returned no rows. "
                    "Check financial scraper logs.[/yellow]"
                )

        elif not price_df.empty:
            console.print(
                f"\n  [green]Price data: {len(price_df)} companies[/green]"
            )
            self._show_price_table(price_df, sector)

        else:
            console.print(
                "\n  [red]No data collected. "
                "Check internet connection.[/red]"
            )
            return

        # ── Store session state ───────────────────────────────────────────────
        self.price_df = price_df
        self.fin_df   = fin_df
        self.sector   = sector

        # ── Save prompt ───────────────────────────────────────────────────────
        if Confirm.ask("\n  Save results to Excel?", default=True):
            self._save(
                sector,
                _safe_df(price_df),
                fin_df,
                analyzed_df,
            )

    # ─────────────────────────────────────────────────────────────────────────
    # Price-only display table
    # ─────────────────────────────────────────────────────────────────────────

    def _show_price_table(self, df: pd.DataFrame, sector: str):
        """Show price table when financials were not fetched."""
        t = Table(
            title       = f"📈 {sector} — Live Prices",
            box         = box.ROUNDED,
            border_style= "bright_blue",
            header_style= "bold white on navy_blue",
            show_lines  = True,
        )

        display_cols = [
            "Symbol", "Company", "Price (₹)", "Change (%)",
            "Volume", "52W High (₹)", "52W Low (₹)",
        ]
        show_cols = [c for c in display_cols if c in df.columns]

        for col in show_cols:
            just  = "right" if col not in ("Symbol","Company") else "left"
            width = 22 if col == "Company" else 14
            t.add_column(col, justify=just, width=width)

        for _, row in df.head(30).iterrows():
            cells = []
            for col in show_cols:
                val = row.get(col, "N/A")
                if col == "Change (%)":
                    try:
                        v     = float(val)
                        color = "green" if v >= 0 else "red"
                        sign  = "+" if v >= 0 else ""
                        val   = f"[{color}]{sign}{v:.2f}%[/]"
                    except (TypeError, ValueError):
                        pass
                elif col == "Price (₹)":
                    try:
                        val = f"₹{float(val):,.2f}"
                    except (TypeError, ValueError):
                        pass
                cells.append(str(val))
            t.add_row(*cells)

        console.print(t)

    # ─────────────────────────────────────────────────────────────────────────
    # Save to Excel
    # ─────────────────────────────────────────────────────────────────────────

    def _save(
        self,
        sector     : str,
        price_df   : pd.DataFrame,
        fin_df     : pd.DataFrame,
        analyzed_df: pd.DataFrame,
    ):
        """Save results to output/sectors/<sector>_<timestamp>.xlsx"""
        safe_name = re.sub(r"[^\w]", "_", sector)
        ts        = datetime.now().strftime("%Y%m%d_%H%M")
        path      = os.path.join(
            self.out_dir, f"{safe_name}_{ts}.xlsx"
        )

        try:
            if not analyzed_df.empty:
                self.analyzer.export_analysis(
                    analyzed_df, sector, path
                )
            elif not fin_df.empty:
                fin_df.to_excel(path, index=False)
                console.print(
                    f"  [green]✅ Financial data → {path}[/green]"
                )
            elif not price_df.empty:
                price_df.to_excel(path, index=False)
                console.print(
                    f"  [green]✅ Price data → {path}[/green]"
                )
            else:
                console.print("  [yellow]No data to save.[/yellow]")

        except PermissionError:
            console.print(
                f"  [red]❌ Permission denied: {path}\n"
                "  Close the file in Excel and retry.[/red]"
            )
        except Exception as exc:
            console.print(f"  [red]Save error: {exc}[/red]")
            self.logger.error(
                f"Save error: {exc}", exc_info=True
            )

    # ─────────────────────────────────────────────────────────────────────────
    # Compare two sectors
    # ─────────────────────────────────────────────────────────────────────────

    def _compare_sectors(self, s1: str, s2: str):
        console.print(Panel(
            f"[bold white]⚖  {s1}  vs  {s2}[/bold white]",
            border_style="bright_blue",
        ))

        co1 = get_sector_companies(s1, 50)
        co2 = get_sector_companies(s2, 50)

        def avg_cap(cos: dict) -> float:
            caps = [
                v.get("cap", 0)
                for v in cos.values()
                if v.get("cap", 0)
            ]
            return sum(caps) / len(caps) / 1_000 if caps else 0.0

        def total_cap(cos: dict) -> float:
            return sum(
                v.get("cap", 0) for v in cos.values()
            ) / 1_000

        t = Table(
            box=box.ROUNDED,
            border_style="blue",
            header_style="bold white on navy_blue",
            show_lines=True,
        )
        t.add_column("Metric",   width=30, style="bold cyan")
        t.add_column(s1[:22],    width=20, justify="right")
        t.add_column(s2[:22],    width=20, justify="right")
        t.add_column("Winner",   width=14, justify="center")

        rows_data = [
            ("Companies in database",
             len(co1), len(co2), True),
            ("Avg Market Cap (₹000 Cr)",
             avg_cap(co1), avg_cap(co2), True),
            ("Total Market Cap (₹000 Cr)",
             total_cap(co1), total_cap(co2), True),
        ]

        for label, v1, v2, h_better in rows_data:
            if v1 != v2:
                is_first = (v1 > v2) if h_better else (v1 < v2)
                winner   = (
                    f"[green]{s1[:10]}[/]"
                    if is_first else
                    f"[green]{s2[:10]}[/]"
                )
            else:
                winner = "[dim]Tie[/]"
            t.add_row(
                label,
                f"{v1:,.0f}",
                f"{v2:,.0f}",
                winner,
            )
        console.print(t)

        # Sub-sector breakdown
        for sector, cos in [(s1, co1), (s2, co2)]:
            subs: Dict[str, int] = {}
            for info in cos.values():
                sub = info.get("sub", "Other")
                subs[sub] = subs.get(sub, 0) + 1

            st = Table(
                title       = f"{sector} — Sub-sectors",
                box         = box.SIMPLE_HEAD,
                header_style= "bold cyan",
            )
            st.add_column("Sub-Sector", style="white")
            st.add_column("Count",
                          justify="right", style="green")
            for sub, cnt in sorted(
                subs.items(),
                key=lambda x: x[1],
                reverse=True,
            ):
                st.add_row(sub, str(cnt))
            console.print(st)

    # ─────────────────────────────────────────────────────────────────────────
    # Benchmark reference
    # ─────────────────────────────────────────────────────────────────────────

    def _show_benchmark_reference(self):
        console.print(Panel(
            "[bold white]📖 Financial Metrics Benchmark Reference[/bold white]",
            border_style="bright_blue",
        ))

        t = Table(
            box=box.ROUNDED,
            border_style="blue",
            header_style="bold white on navy_blue",
            show_lines=True,
        )
        t.add_column("Category",     width=18, style="bold yellow")
        t.add_column("Metric",       width=25, style="bold cyan")
        t.add_column("Description",  width=38)
        t.add_column("✅ Excellent", width=14,
                     style="bold green", justify="center")
        t.add_column("👍 Good",      width=12,
                     style="green",     justify="center")
        t.add_column("⚠ Average",   width=12,
                     style="yellow",    justify="center")
        t.add_column("❌ Poor",      width=10,
                     style="red",       justify="center")
        t.add_column("↑ Better",     width=9,  justify="center")

        def fmtb(val, unit: str) -> str:
            if val is None:
                return "Varies"
            if "%" in unit:
                return f"{val}%"
            if "x" in unit:
                return f"{val}x"
            return str(val)

        for metric, bench in METRIC_BENCHMARKS.items():
            unit = bench.get("unit", "")
            t.add_row(
                bench.get("category",    ""),
                metric,
                bench.get("description", ""),
                fmtb(bench.get("excellent"), unit),
                fmtb(bench.get("good"),      unit),
                fmtb(bench.get("average"),   unit),
                fmtb(bench.get("poor"),      unit),
                "Yes" if bench.get("higher_is_better") else "No",
            )
        console.print(t)

        # Sector P/E table
        console.print("\n[bold cyan]📊 Sector P/E Benchmarks[/bold cyan]")
        pt = Table(
            box=box.SIMPLE_HEAD,
            header_style="bold cyan",
            show_lines=False,
        )
        pt.add_column("Sector",    style="white",  width=30)
        pt.add_column("Fair P/E",  justify="right",
                      style="green",  width=12)
        pt.add_column("Expensive", justify="right",
                      style="red",    width=12)

        for sec_name, vals in SECTOR_PE_BENCHMARKS.items():
            pt.add_row(
                sec_name,
                f"< {vals['fair']}x",
                f"> {vals['expensive']}x",
            )
        console.print(pt)


# ─────────────────────────────────────────────────────────────────────────────
# Quick self-test
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("sector_ui.py — import check")
    print(f"  requests      : OK ({requests.__version__})")
    print(f"  pandas        : OK ({pd.__version__})")
    print(f"  SectorUI.run  : {hasattr(SectorUI, 'run')}")
    print(f"  _safe_df([])  : {_safe_df(None).empty}")
    print("✅ All imports successful!")