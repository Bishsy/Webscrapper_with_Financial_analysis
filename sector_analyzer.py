# sector_analyzer.py
# Complete sector analysis engine with all 13 metrics,
# benchmarks, rich terminal display, and Excel export.

import os
import sys
import logging
import numpy  as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
if _THIS_DIR not in sys.path:
    sys.path.insert(0, _THIS_DIR)

from rich.console import Console
from rich.table   import Table
from rich.panel   import Panel
from rich.text    import Text
from rich         import box

console = Console()

# ─────────────────────────────────────────────────────────────────────────────
# Import sector data (benchmarks)
# ─────────────────────────────────────────────────────────────────────────────

try:
    from sector_data import METRIC_BENCHMARKS, SECTOR_PE_BENCHMARKS
except ImportError:
    # Fallback benchmarks if sector_data.py not found
    METRIC_BENCHMARKS = {
        "Revenue Growth (%)" : {
            "excellent": 20,  "good": 10,  "average": 5,   "poor": 0,
            "unit": "%", "higher_is_better": True,
            "description": "YoY Sales Growth", "category": "Growth",
        },
        "EBITDA (Cr)" : {
            "excellent": None,"good": None,"average": None,"poor": 0,
            "unit": "₹ Cr",  "higher_is_better": True,
            "description": "Operating Profit before D&A", "category": "Profitability",
        },
        "EBITDA Margin (%)" : {
            "excellent": 25,  "good": 15,  "average": 8,   "poor": 0,
            "unit": "%", "higher_is_better": True,
            "description": "EBITDA / Revenue × 100", "category": "Profitability",
        },
        "Net Profit / PAT (Cr)" : {
            "excellent": None,"good": None,"average": None,"poor": 0,
            "unit": "₹ Cr",  "higher_is_better": True,
            "description": "Profit After Tax",          "category": "Profitability",
        },
        "PAT Margin (%)" : {
            "excellent": 20,  "good": 10,  "average": 5,   "poor": 0,
            "unit": "%", "higher_is_better": True,
            "description": "PAT / Revenue × 100",       "category": "Profitability",
        },
        "ROE (%)" : {
            "excellent": 25,  "good": 15,  "average": 10,  "poor": 0,
            "unit": "%", "higher_is_better": True,
            "description": "Net Profit / Shareholders Equity", "category": "Returns",
        },
        "ROCE (%)" : {
            "excellent": 20,  "good": 12,  "average": 8,   "poor": 0,
            "unit": "%", "higher_is_better": True,
            "description": "EBIT / Capital Employed",   "category": "Returns",
        },
        "ROA (%)" : {
            "excellent": 10,  "good": 5,   "average": 2,   "poor": 0,
            "unit": "%", "higher_is_better": True,
            "description": "Net Profit / Total Assets", "category": "Returns",
        },
        "EPS (₹)" : {
            "excellent": None,"good": None,"average": None,"poor": 0,
            "unit": "₹",     "higher_is_better": True,
            "description": "Earnings Per Share",        "category": "Valuation",
        },
        "P/E Ratio" : {
            "excellent": None,"good": None,"average": None,"poor": None,
            "unit": "x",     "higher_is_better": False,
            "description": "Price / EPS",               "category": "Valuation",
        },
        "Debt to Equity" : {
            "excellent": 0.3, "good": 0.5, "average": 1.0, "poor": 2.0,
            "unit": "x",     "higher_is_better": False,
            "description": "Total Debt / Equity",       "category": "Financial Health",
        },
        "Current Ratio" : {
            "excellent": 2.5, "good": 1.5, "average": 1.0, "poor": 0.5,
            "unit": "x",     "higher_is_better": True,
            "description": "Current Assets / Current Liabilities", "category": "Liquidity",
        },
        "Free Cash Flow (Cr)" : {
            "excellent": None,"good": None,"average": None,"poor": 0,
            "unit": "₹ Cr",  "higher_is_better": True,
            "description": "Operating CF − Capex",      "category": "Cash Flow",
        },
    }

    SECTOR_PE_BENCHMARKS = {
        "Information Technology" : {"fair": 25, "expensive": 40},
        "Financials"             : {"fair": 15, "expensive": 25},
        "Healthcare"             : {"fair": 30, "expensive": 50},
        "Consumer Staples"       : {"fair": 40, "expensive": 60},
        "Consumer Discretionary" : {"fair": 35, "expensive": 55},
        "Energy"                 : {"fair": 12, "expensive": 20},
        "Materials"              : {"fair": 15, "expensive": 25},
        "Industrials"            : {"fair": 20, "expensive": 35},
        "Utilities"              : {"fair": 15, "expensive": 25},
        "Real Estate"            : {"fair": 20, "expensive": 40},
        "Communication Services" : {"fair": 25, "expensive": 40},
    }


# ─────────────────────────────────────────────────────────────────────────────
# Column normalisation
# ─────────────────────────────────────────────────────────────────────────────

# All known column name variants → standard Title Case name
_RENAME_MAP: Dict[str, str] = {
    # Symbol / company
    "symbol"           : "Symbol",
    "ticker"           : "Symbol",
    "nse_symbol"       : "Symbol",
    "company"          : "Company",
    "company_name"     : "Company",
    "name"             : "Company",

    # Price
    "price"            : "Price (₹)",
    "ltp"              : "Price (₹)",
    "last_price"       : "Price (₹)",
    "lastprice"        : "Price (₹)",
    "current_price"    : "Price (₹)",
    "currentprice"     : "Price (₹)",
    "current price (₹)": "Price (₹)",

    # Change
    "change (%)"       : "Change (%)",
    "change_pct"       : "Change (%)",
    "changepct"        : "Change (%)",
    "pchange"          : "Change (%)",
    "percent_change"   : "Change (%)",

    # Volume
    "volume"           : "Volume",
    "totalvolume"      : "Volume",
    "total_volume"     : "Volume",

    # OHLC
    "open"             : "Open (₹)",
    "high"             : "High (₹)",
    "low"              : "Low (₹)",
    "prev_close"       : "Prev Close (₹)",
    "prev close"       : "Prev Close (₹)",
    "previousclose"    : "Prev Close (₹)",

    # 52-week
    "week_high"        : "52W High (₹)",
    "52w_high"         : "52W High (₹)",
    "yearhigh"         : "52W High (₹)",
    "year_high"        : "52W High (₹)",
    "week_low"         : "52W Low (₹)",
    "52w_low"          : "52W Low (₹)",
    "yearlow"          : "52W Low (₹)",
    "year_low"         : "52W Low (₹)",

    # Market cap
    "market_cap"       : "Market Cap (Cr)",
    "marketcap"        : "Market Cap (Cr)",
    "mktcap"           : "Market Cap (Cr)",

    # Sector / sub-sector
    "sector"           : "Sector",
    "sub-sector"       : "Sub-Sector",
    "sub_sector"       : "Sub-Sector",
    "subsector"        : "Sub-Sector",
}


def normalise_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Rename DataFrame columns to the standard Title Case names
    used throughout the app.

    Handles:
      - lowercase API keys   (symbol → Symbol)
      - underscore variants  (market_cap → Market Cap (Cr))
      - mixed case           (ChangePercent → Change (%))

    Always returns a DataFrame (never raises).
    """
    if df is None or df.empty:
        return df if df is not None else pd.DataFrame()

    rename = {}
    for col in df.columns:
        lower = col.lower().strip()
        if lower in _RENAME_MAP and col != _RENAME_MAP[lower]:
            rename[col] = _RENAME_MAP[lower]

    if rename:
        df = df.rename(columns=rename)

    return df


# ─────────────────────────────────────────────────────────────────────────────
# Number utilities
# ─────────────────────────────────────────────────────────────────────────────

def _to_float(val: Any) -> Optional[float]:
    """Convert any value to float, return None on failure."""
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return None if np.isnan(float(val)) else float(val)
    s = (str(val).strip()
         .replace(",", "")
         .replace("₹", "")
         .replace("%", "")
         .replace("Cr.", "")
         .replace("Cr",  "")
         .replace("+",   "")
         .strip())
    if not s or s in ["-", "--", "N/A", "NA", "None", "null"]:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _safe_series(df: pd.DataFrame, col: str) -> pd.Series:
    """Return a float Series for a column, NaN where conversion fails."""
    if col not in df.columns:
        return pd.Series(np.nan, index=df.index)
    return df[col].apply(_to_float)


def _fmt_cr(val: Any, prefix: str = "₹") -> str:
    """Format a crore value for display."""
    v = _to_float(val)
    if v is None:
        return "[dim]N/A[/dim]"
    if abs(v) >= 100_000:
        return f"{prefix}{v/100_000:.2f}L Cr"
    return f"{prefix}{v:,.0f}"


def _fmt_pct(val: Any) -> str:
    """Format a percentage value."""
    v = _to_float(val)
    if v is None:
        return "[dim]N/A[/dim]"
    color = "green" if v >= 0 else "red"
    sign  = "+" if v >= 0 else ""
    return f"[{color}]{sign}{v:.2f}%[/]"


def _fmt_num(val: Any, decimals: int = 2,
              prefix: str = "", suffix: str = "") -> str:
    """Generic number formatter."""
    v = _to_float(val)
    if v is None:
        return "[dim]N/A[/dim]"
    return f"{prefix}{v:,.{decimals}f}{suffix}"


# ─────────────────────────────────────────────────────────────────────────────
# Metric rating engine
# ─────────────────────────────────────────────────────────────────────────────

def rate_metric(metric: str,
                value:  Any,
                sector: str = "") -> str:
    """
    Return a Rich-markup rating string for a metric value.

    Levels:
      ✅ Excellent  (bold green)
      👍 Good       (green)
      ⚠  Average    (yellow)
      ❌ Poor        (red)
      N/A           (dim)

    P/E uses sector-specific benchmarks.
    Absolute metrics (Revenue, PAT, FCF) use green/red only.
    """
    v = _to_float(value)
    if v is None:
        return "[dim]N/A[/dim]"

    bench  = METRIC_BENCHMARKS.get(metric, {})
    h_is_b = bench.get("higher_is_better", True)
    unit   = bench.get("unit", "")

    # ── Format helpers ────────────────────────────────────────────────────────
    def fmt(x: float) -> str:
        if "%" in unit:
            return f"{x:.2f}%"
        if "Cr" in unit:
            return f"₹{x:,.0f} Cr"
        if "₹" in unit:
            return f"₹{x:.2f}"
        return f"{x:.2f}{unit}"

    # ── P/E Ratio — sector-specific ───────────────────────────────────────────
    if "P/E" in metric or "PE" in metric or metric == "P/E Ratio":
        pe_bench = SECTOR_PE_BENCHMARKS.get(
            sector, {"fair": 25, "expensive": 40}
        )
        fair      = pe_bench.get("fair",      25)
        expensive = pe_bench.get("expensive", 40)
        if v <= 0:
            return f"[dim]{v:.1f}x (negative earnings)[/dim]"
        elif v < fair:
            return f"[bold green]✅ {v:.1f}x  Attractive (<{fair})[/]"
        elif v < expensive:
            return f"[yellow]⚠  {v:.1f}x  Fair ({fair}–{expensive})[/]"
        else:
            return f"[red]❌ {v:.1f}x  Expensive (>{expensive})[/]"

    exc = bench.get("excellent")
    gd  = bench.get("good")
    avg = bench.get("average")

    # ── Absolute / monotone metrics (no upper threshold) ─────────────────────
    if exc is None:
        if h_is_b:
            color = "green" if v > 0 else "red"
        else:
            color = "green" if v < 0 else "red"
        return f"[{color}]{fmt(v)}[/]"

    # ── Benchmarked metrics ────────────────────────────────────────────────────
    if h_is_b:
        # Higher is better (ROE, ROCE, Margins, etc.)
        if v >= exc:
            return f"[bold green]✅ {fmt(v)}  (≥{fmt(exc)})[/]"
        elif gd is not None and v >= gd:
            return f"[green]👍 {fmt(v)}  (≥{fmt(gd)})[/]"
        elif avg is not None and v >= avg:
            return f"[yellow]⚠  {fmt(v)}  (≥{fmt(avg)})[/]"
        else:
            thr = fmt(avg) if avg is not None else "benchmark"
            return f"[red]❌ {fmt(v)}  (<{thr})[/]"
    else:
        # Lower is better (D/E Ratio)
        if v <= exc:
            return f"[bold green]✅ {fmt(v)}  (≤{fmt(exc)})[/]"
        elif gd is not None and v <= gd:
            return f"[green]👍 {fmt(v)}  (≤{fmt(gd)})[/]"
        elif avg is not None and v <= avg:
            return f"[yellow]⚠  {fmt(v)}  (≤{fmt(avg)})[/]"
        else:
            thr = fmt(avg) if avg is not None else "benchmark"
            return f"[red]❌ {fmt(v)}  (>{thr})[/]"


# ─────────────────────────────────────────────────────────────────────────────
# Main SectorAnalyzer class
# ─────────────────────────────────────────────────────────────────────────────

class SectorAnalyzer:
    """
    Merges price + financial DataFrames, computes derived metrics,
    displays rich terminal tables, and exports colour-coded Excel.

    13 Metrics Covered
    ------------------
    Growth         : Revenue Growth (%)
    Profitability  : EBITDA, EBITDA Margin, PAT, PAT Margin
    Returns        : ROE, ROCE, ROA
    Valuation      : EPS, P/E Ratio
    Financial Health: Debt to Equity
    Liquidity      : Current Ratio
    Cash Flow      : Free Cash Flow
    """

    # All numeric columns the analyzer handles
    NUMERIC_COLS = [
        "Revenue Y1 (Cr)", "Revenue Y2 (Cr)", "Revenue Y3 (Cr)",
        "Revenue Growth (%)",
        "EBITDA Y1 (Cr)",  "EBITDA Y2 (Cr)",  "EBITDA Y3 (Cr)",
        "EBITDA Margin (%)",
        "PAT Y1 (Cr)",     "PAT Y2 (Cr)",     "PAT Y3 (Cr)",
        "PAT Margin (%)",
        "ROE (%)",         "ROCE (%)",         "ROA (%)",
        "EPS (₹)",         "P/E Ratio",
        "Debt to Equity",  "Current Ratio",
        "FCF Y1 (Cr)",     "FCF Y2 (Cr)",     "FCF Y3 (Cr)",
        "Market Cap (Cr)",
        "Price (₹)",       "Change (%)",
        "52W High (₹)",    "52W Low (₹)",
        "Dividend Yield (%)",
        "Book Value (₹)",
    ]

    def __init__(self):
        # Logger
        self.logger = logging.getLogger(self.__class__.__name__)
        if not self.logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            handler.setFormatter(
                logging.Formatter(
                    "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S",
                )
            )
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.DEBUG)

    # ─────────────────────────────────────────────────────────────────────────
    # analyze()  ← public entry point
    # ─────────────────────────────────────────────────────────────────────────

    def analyze(self,
                fin_df   : pd.DataFrame,
                price_df : Optional[pd.DataFrame],
                sector   : str) -> pd.DataFrame:
        """
        Merge financial + price data, compute derived metrics.

        Parameters
        ----------
        fin_df   : DataFrame from ScreenerFinancialScraper
        price_df : DataFrame from NSE price fetch (may be empty)
        sector   : sector name string (for PE benchmark lookup)

        Returns
        -------
        Combined DataFrame with all numeric columns ready for display.
        """
        if fin_df is None or fin_df.empty:
            self.logger.warning("analyze(): fin_df is empty")
            return pd.DataFrame()

        # ── Step 1: normalise column names ────────────────────────────────────
        df       = normalise_columns(fin_df.copy())
        p_df     = normalise_columns(price_df.copy()) \
                   if (price_df is not None and not price_df.empty) \
                   else pd.DataFrame()

        # ── Step 2: ensure Symbol column exists ───────────────────────────────
        df = self._ensure_symbol(df)
        if "Symbol" not in df.columns:
            self.logger.error("analyze(): no Symbol column found")
            return df

        # ── Step 3: convert to numeric ────────────────────────────────────────
        for col in self.NUMERIC_COLS:
            if col in df.columns:
                df[col] = df[col].apply(_to_float)

        # ── Step 4: compute derived metrics ───────────────────────────────────
        df = self._compute_derived(df)

        # ── Step 5: merge price data ──────────────────────────────────────────
        df = self._merge_price(df, p_df)

        # ── Step 6: sort by Revenue Y1 descending ────────────────────────────
        if "Revenue Y1 (Cr)" in df.columns:
            df = df.sort_values(
                "Revenue Y1 (Cr)", ascending=False, na_position="last"
            )

        return df.reset_index(drop=True)

    # ─────────────────────────────────────────────────────────────────────────
    # Private helpers
    # ─────────────────────────────────────────────────────────────────────────

    def _ensure_symbol(self, df: pd.DataFrame) -> pd.DataFrame:
        """Try multiple column names to find / create Symbol."""
        if "Symbol" in df.columns:
            return df
        for candidate in ["symbol", "SYMBOL", "Ticker",
                           "ticker", "NSE_Symbol", "nse_symbol"]:
            if candidate in df.columns:
                self.logger.debug(
                    f"  Renaming '{candidate}' → 'Symbol'"
                )
                return df.rename(columns={candidate: "Symbol"})
        self.logger.warning(
            "  No Symbol column found. "
            f"Available: {list(df.columns)}"
        )
        return df

    def _compute_derived(self, df: pd.DataFrame) -> pd.DataFrame:
        """Compute Revenue Growth, PAT Margin, EBITDA Margin where null."""

        # ── Revenue Growth % ──────────────────────────────────────────────────
        if "Revenue Growth (%)" not in df.columns:
            df["Revenue Growth (%)"] = np.nan

        mask_rg = (
            df["Revenue Y1 (Cr)"].notna()  &
            df["Revenue Y2 (Cr)"].notna()  &
            (df["Revenue Y2 (Cr)"] != 0)   &
            df["Revenue Growth (%)"].isna()
        )
        if mask_rg.any():
            df.loc[mask_rg, "Revenue Growth (%)"] = (
                (df.loc[mask_rg, "Revenue Y1 (Cr)"] -
                 df.loc[mask_rg, "Revenue Y2 (Cr)"]) /
                df.loc[mask_rg, "Revenue Y2 (Cr)"].abs() * 100
            ).round(2)

        # ── PAT Margin % ──────────────────────────────────────────────────────
        if "PAT Margin (%)" not in df.columns:
            df["PAT Margin (%)"] = np.nan

        mask_pm = (
            df["PAT Y1 (Cr)"].notna()      &
            df["Revenue Y1 (Cr)"].notna()  &
            (df["Revenue Y1 (Cr)"] != 0)   &
            df["PAT Margin (%)"].isna()
        )
        if mask_pm.any():
            df.loc[mask_pm, "PAT Margin (%)"] = (
                df.loc[mask_pm, "PAT Y1 (Cr)"] /
                df.loc[mask_pm, "Revenue Y1 (Cr)"] * 100
            ).round(2)

        # ── EBITDA Margin % ───────────────────────────────────────────────────
        if "EBITDA Margin (%)" not in df.columns:
            df["EBITDA Margin (%)"] = np.nan

        mask_em = (
            df["EBITDA Y1 (Cr)"].notna()   &
            df["Revenue Y1 (Cr)"].notna()  &
            (df["Revenue Y1 (Cr)"] != 0)   &
            df["EBITDA Margin (%)"].isna()
        )
        if mask_em.any():
            df.loc[mask_em, "EBITDA Margin (%)"] = (
                df.loc[mask_em, "EBITDA Y1 (Cr)"] /
                df.loc[mask_em, "Revenue Y1 (Cr)"] * 100
            ).round(2)

        # ── ROA (if missing) ──────────────────────────────────────────────────
        # Cannot compute without Total Assets — leave as-is if missing

        return df

    def _merge_price(self,
                      df    : pd.DataFrame,
                      p_df  : pd.DataFrame) -> pd.DataFrame:
        """Safely merge price columns into the financial DataFrame."""
        if p_df.empty:
            self.logger.debug("  No price data to merge")
            return df

        if "Symbol" not in p_df.columns:
            self.logger.warning(
                "  Price DataFrame missing 'Symbol' column. "
                f"Columns: {list(p_df.columns)}"
            )
            return df

        # Select price columns that exist
        price_cols = [
            "Symbol", "Price (₹)", "Change (%)", "Volume",
            "Open (₹)", "High (₹)", "Low (₹)",
            "52W High (₹)", "52W Low (₹)", "Prev Close (₹)",
        ]
        available = [c for c in price_cols if c in p_df.columns]
        if len(available) <= 1:   # only Symbol, nothing useful
            return df

        p_sub = (
            p_df[available]
            .drop_duplicates(subset="Symbol")
            .reset_index(drop=True)
        )

        # Drop price cols already in df to avoid _x/_y conflicts
        drop_existing = [
            c for c in available
            if c != "Symbol" and c in df.columns
        ]
        if drop_existing:
            df = df.drop(columns=drop_existing)

        df = df.merge(p_sub, on="Symbol", how="left")
        self.logger.debug(
            f"  Price merge: {len(df)} rows, "
            f"added cols: {[c for c in available if c != 'Symbol']}"
        )
        return df

    # ─────────────────────────────────────────────────────────────────────────
    # show_metric_table()  ← main display entry point
    # ─────────────────────────────────────────────────────────────────────────

    def show_metric_table(self,
                           df     : pd.DataFrame,
                           sector : str,
                           top_n  : int = 20):
        """
        Display all 13 financial metrics in the terminal
        with colour-coded benchmark ratings.
        """
        if df is None or df.empty:
            console.print("[yellow]  No data to display.[/yellow]")
            return

        show = df.head(top_n).copy()
        n    = len(show)

        # ── Header panel ──────────────────────────────────────────────────────
        console.print(Panel(
            Text.assemble(
                (f"  📊  {sector} Sector — Financial Dashboard\n\n",
                 "bold white"),
                (f"  Showing top {n} companies  │  "
                 f"All 13 key metrics with benchmarks",
                 "dim"),
            ),
            border_style="bright_blue",
            padding=(1, 2),
        ))

        # ── 1. Sector summary averages ────────────────────────────────────────
        self._display_sector_summary(df, sector)

        # ── 2. Growth ─────────────────────────────────────────────────────────
        self._display_growth(show, sector)

        # ── 3. Profitability ──────────────────────────────────────────────────
        self._display_profitability(show, sector)

        # ── 4. Returns ────────────────────────────────────────────────────────
        self._display_returns(show, sector)

        # ── 5. Valuation ──────────────────────────────────────────────────────
        self._display_valuation(show, sector)

        # ── 6. Financial Health + Liquidity + Cash Flow ───────────────────────
        self._display_health(show, sector)

        # ── 7. Mini leaderboard ───────────────────────────────────────────────
        self._display_leaderboard(df, sector)

    # ─────────────────────────────────────────────────────────────────────────
    # Individual display sections
    # ─────────────────────────────────────────────────────────────────────────

    def _display_sector_summary(self, df: pd.DataFrame, sector: str):
        """Sector-wide averages vs benchmarks."""
        console.print(Panel(
            "[bold cyan]📈 Sector Averages vs Benchmarks[/bold cyan]",
            border_style="cyan",
        ))

        t = Table(
            box         = box.ROUNDED,
            border_style= "cyan",
            header_style= "bold white on navy_blue",
            show_lines  = True,
            padding     = (0, 1),
        )
        t.add_column("Category",     style="bold yellow",  width=20)
        t.add_column("Metric",       style="cyan",         width=25)
        t.add_column("Companies",    justify="right",      width=12)
        t.add_column("Mean",         justify="right",      width=14)
        t.add_column("Median",       justify="right",      width=14)
        t.add_column("Best",         justify="right",      width=14)
        t.add_column("Worst",        justify="right",      width=14)
        t.add_column("Benchmark Rating (Mean)", width=38)

        summary_rows = [
            ("Growth",         "Revenue Growth (%)",
             "Revenue Growth (%)"),
            ("Profitability",  "EBITDA Margin (%)",
             "EBITDA Margin (%)"),
            ("Profitability",  "PAT Margin (%)",
             "PAT Margin (%)"),
            ("Returns",        "ROE (%)",
             "ROE (%)"),
            ("Returns",        "ROCE (%)",
             "ROCE (%)"),
            ("Returns",        "ROA (%)",
             "ROA (%)"),
            ("Valuation",      "P/E Ratio",
             "P/E Ratio"),
            ("Health",         "Debt to Equity",
             "Debt to Equity"),
            ("Liquidity",      "Current Ratio",
             "Current Ratio"),
        ]

        for cat, display, col in summary_rows:
            if col not in df.columns:
                continue
            series = _safe_series(df, col).dropna()
            if series.empty:
                t.add_row(cat, display, "0",
                          "[dim]N/A[/]","[dim]N/A[/]",
                          "[dim]N/A[/]","[dim]N/A[/]",
                          "[dim]No data[/]")
                continue

            h_better = METRIC_BENCHMARKS.get(
                col, {}
            ).get("higher_is_better", True)
            best  = series.max() if h_better else series.min()
            worst = series.min() if h_better else series.max()

            t.add_row(
                cat,
                display,
                str(len(series)),
                f"{series.mean():,.2f}",
                f"{series.median():,.2f}",
                f"{best:,.2f}",
                f"{worst:,.2f}",
                rate_metric(display, series.mean(), sector),
            )

        console.print(t)

    # ── Growth ────────────────────────────────────────────────────────────────

    def _display_growth(self, df: pd.DataFrame, sector: str):
        console.print(
            "\n[bold green]📈  GROWTH — Revenue Last 3 Years[/bold green]"
        )

        t = Table(
            box=box.SIMPLE_HEAD,
            header_style="bold green on black",
            show_lines=True,
            padding=(0, 1),
        )
        t.add_column("Symbol",       width=14, style="bold cyan", no_wrap=True)
        t.add_column("Company",      width=24, no_wrap=True)
        t.add_column("Period",       width=10, style="dim")
        t.add_column("Revenue Y1",   justify="right", width=16)
        t.add_column("Revenue Y2",   justify="right", width=16)
        t.add_column("Revenue Y3",   justify="right", width=16)
        t.add_column("YoY Growth",   width=36)

        for _, row in df.iterrows():
            r1     = row.get("Revenue Y1 (Cr)")
            r2     = row.get("Revenue Y2 (Cr)")
            r3     = row.get("Revenue Y3 (Cr)")
            growth = row.get("Revenue Growth (%)")
            period = str(row.get("Revenue Y1 Period", ""))

            t.add_row(
                str(row.get("Symbol",  ""))[:13],
                str(row.get("Company", ""))[:23],
                period[:10],
                _fmt_cr(r1),
                _fmt_cr(r2),
                _fmt_cr(r3),
                rate_metric("Revenue Growth (%)", growth, sector),
            )

        console.print(t)

    # ── Profitability ─────────────────────────────────────────────────────────

    def _display_profitability(self, df: pd.DataFrame, sector: str):
        console.print(
            "\n[bold yellow]💰  PROFITABILITY — "
            "EBITDA & PAT Last 3 Years[/bold yellow]"
        )

        t = Table(
            box=box.SIMPLE_HEAD,
            header_style="bold yellow on black",
            show_lines=True,
            padding=(0, 1),
        )
        t.add_column("Symbol",         width=14, style="bold cyan", no_wrap=True)
        t.add_column("Company",        width=22, no_wrap=True)
        t.add_column("EBITDA Y1",      justify="right", width=14)
        t.add_column("EBITDA Y2",      justify="right", width=14)
        t.add_column("EBITDA Y3",      justify="right", width=14)
        t.add_column("EBITDA Margin",  width=36)
        t.add_column("PAT Y1",         justify="right", width=14)
        t.add_column("PAT Y2",         justify="right", width=14)
        t.add_column("PAT Y3",         justify="right", width=14)
        t.add_column("PAT Margin",     width=36)

        for _, row in df.iterrows():
            e1 = row.get("EBITDA Y1 (Cr)")
            e2 = row.get("EBITDA Y2 (Cr)")
            e3 = row.get("EBITDA Y3 (Cr)")
            em = row.get("EBITDA Margin (%)")
            p1 = row.get("PAT Y1 (Cr)")
            p2 = row.get("PAT Y2 (Cr)")
            p3 = row.get("PAT Y3 (Cr)")
            pm = row.get("PAT Margin (%)")

            t.add_row(
                str(row.get("Symbol",  ""))[:13],
                str(row.get("Company", ""))[:21],
                _fmt_cr(e1), _fmt_cr(e2), _fmt_cr(e3),
                rate_metric("EBITDA Margin (%)", em, sector),
                _fmt_cr(p1), _fmt_cr(p2), _fmt_cr(p3),
                rate_metric("PAT Margin (%)", pm, sector),
            )

        console.print(t)

    # ── Returns ───────────────────────────────────────────────────────────────

    def _display_returns(self, df: pd.DataFrame, sector: str):
        console.print(
            "\n[bold magenta]📊  RETURNS — ROE / ROCE / ROA[/bold magenta]"
        )

        t = Table(
            box=box.SIMPLE_HEAD,
            header_style="bold magenta on black",
            show_lines=True,
            padding=(0, 1),
        )
        t.add_column("Symbol",   width=14, style="bold cyan", no_wrap=True)
        t.add_column("Company",  width=24, no_wrap=True)
        t.add_column("ROE (%)",  width=36)
        t.add_column("ROCE (%)", width=36)
        t.add_column("ROA (%)",  width=36)

        for _, row in df.iterrows():
            t.add_row(
                str(row.get("Symbol",  ""))[:13],
                str(row.get("Company", ""))[:23],
                rate_metric("ROE (%)",  row.get("ROE (%)"),  sector),
                rate_metric("ROCE (%)", row.get("ROCE (%)"), sector),
                rate_metric("ROA (%)",  row.get("ROA (%)"),  sector),
            )

        console.print(t)

    # ── Valuation ─────────────────────────────────────────────────────────────

    def _display_valuation(self, df: pd.DataFrame, sector: str):
        console.print(
            "\n[bold blue]💎  VALUATION — "
            "EPS / P/E / Price / Dividend[/bold blue]"
        )

        t = Table(
            box=box.SIMPLE_HEAD,
            header_style="bold blue on black",
            show_lines=True,
            padding=(0, 1),
        )
        t.add_column("Symbol",      width=14, style="bold cyan", no_wrap=True)
        t.add_column("Company",     width=22, no_wrap=True)
        t.add_column("EPS (₹)",     justify="right", width=12)
        t.add_column("P/E Ratio",   width=38)
        t.add_column("Book Val (₹)",justify="right", width=12)
        t.add_column("Div Yield",   justify="right", width=12)
        t.add_column("Price (₹)",   justify="right", width=14)
        t.add_column("Change",      width=18)

        for _, row in df.iterrows():
            eps  = _to_float(row.get("EPS (₹)"))
            pe   = row.get("P/E Ratio")
            bv   = _to_float(row.get("Book Value (₹)"))
            dy   = _to_float(row.get("Dividend Yield (%)"))
            pr   = _to_float(row.get("Price (₹)"))
            ch   = _to_float(row.get("Change (%)"))

            # Change colour
            ch_str = "[dim]N/A[/]"
            if ch is not None:
                color  = "green" if ch >= 0 else "red"
                sign   = "+" if ch >= 0 else ""
                ch_str = f"[{color}]{sign}{ch:.2f}%[/]"

            t.add_row(
                str(row.get("Symbol",  ""))[:13],
                str(row.get("Company", ""))[:21],
                f"₹{eps:,.2f}"   if eps else "[dim]N/A[/]",
                rate_metric("P/E Ratio", pe, sector),
                f"₹{bv:,.2f}"   if bv  else "[dim]N/A[/]",
                f"{dy:.2f}%"    if dy  else "[dim]N/A[/]",
                f"₹{pr:,.2f}"   if pr  else "[dim]N/A[/]",
                ch_str,
            )

        console.print(t)

    # ── Health + Liquidity + Cash Flow ────────────────────────────────────────

    def _display_health(self, df: pd.DataFrame, sector: str):
        console.print(
            "\n[bold red]🏥  FINANCIAL HEALTH  │  "
            "LIQUIDITY  │  CASH FLOW[/bold red]"
        )

        t = Table(
            box=box.SIMPLE_HEAD,
            header_style="bold red on black",
            show_lines=True,
            padding=(0, 1),
        )
        t.add_column("Symbol",       width=14, style="bold cyan", no_wrap=True)
        t.add_column("Company",      width=22, no_wrap=True)
        t.add_column("D/E Ratio",    width=34)
        t.add_column("Curr Ratio",   width=30)
        t.add_column("FCF Y1 (Cr)",  justify="right", width=16)
        t.add_column("FCF Y2 (Cr)",  justify="right", width=16)
        t.add_column("FCF Y3 (Cr)",  justify="right", width=16)

        for _, row in df.iterrows():
            de  = row.get("Debt to Equity")
            cr  = row.get("Current Ratio")
            f1  = _to_float(row.get("FCF Y1 (Cr)"))
            f2  = _to_float(row.get("FCF Y2 (Cr)"))
            f3  = _to_float(row.get("FCF Y3 (Cr)"))

            def fmt_fcf(v: Optional[float]) -> str:
                if v is None:
                    return "[dim]N/A[/]"
                color = "green" if v >= 0 else "red"
                return f"[{color}]₹{v:,.0f}[/]"

            t.add_row(
                str(row.get("Symbol",  ""))[:13],
                str(row.get("Company", ""))[:21],
                rate_metric("Debt to Equity", de, sector),
                rate_metric("Current Ratio",  cr, sector),
                fmt_fcf(f1),
                fmt_fcf(f2),
                fmt_fcf(f3),
            )

        console.print(t)

    # ── Leaderboard ───────────────────────────────────────────────────────────

    def _display_leaderboard(self, df: pd.DataFrame, sector: str):
        """Mini leaderboard: best company per metric."""
        console.print(Panel(
            "[bold white]🏆  Sector Leaders (Best per Metric)[/bold white]",
            border_style="gold1",
        ))

        t = Table(
            box=box.ROUNDED,
            border_style="gold1",
            header_style="bold white on dark_goldenrod",
            show_lines=True,
            padding=(0, 1),
        )
        t.add_column("Category",     width=18, style="bold yellow")
        t.add_column("Metric",       width=25, style="cyan")
        t.add_column("Best Company", width=22, style="bold green")
        t.add_column("Best Symbol",  width=14, style="bold cyan")
        t.add_column("Value",        width=22)

        leader_metrics = [
            ("Growth",      "Revenue Growth (%)", True),
            ("Profitability","EBITDA Margin (%)",  True),
            ("Profitability","PAT Margin (%)",      True),
            ("Returns",     "ROE (%)",              True),
            ("Returns",     "ROCE (%)",             True),
            ("Returns",     "ROA (%)",              True),
            ("Valuation",   "P/E Ratio",            False),  # lower = better
            ("Health",      "Debt to Equity",       False),
            ("Liquidity",   "Current Ratio",        True),
            ("Cash Flow",   "FCF Y1 (Cr)",          True),
        ]

        for cat, col, h_better in leader_metrics:
            if col not in df.columns:
                continue
            series = _safe_series(df, col).dropna()
            if series.empty:
                continue

            idx   = series.idxmax() if h_better else series.idxmin()
            best  = df.loc[idx]
            val   = series[idx]
            unit  = METRIC_BENCHMARKS.get(col, {}).get("unit", "")

            def fmt_val(v: float) -> str:
                if "%" in unit:
                    sign = "+" if v >= 0 else ""
                    return f"{sign}{v:.2f}%"
                if "Cr" in unit:
                    return f"₹{v:,.0f} Cr"
                return f"{v:.2f}{unit}"

            t.add_row(
                cat,
                col,
                str(best.get("Company", ""))[:21],
                str(best.get("Symbol",  ""))[:13],
                rate_metric(col, val, sector),
            )

        console.print(t)

    # ─────────────────────────────────────────────────────────────────────────
    # Excel export
    # ─────────────────────────────────────────────────────────────────────────

    # def export_analysis(self,
    #                      df     : pd.DataFrame,
    #                      sector : str,
    #                      path   : str):
    #     """
    #     Export the analysed DataFrame to a colour-coded Excel workbook.

    #     Sheets created:
    #       1. <Sector> Analysis  — all companies, colour-coded by benchmark
    #       2. 📊 Sector Summary  — averages + ratings
    #       3. 📖 Benchmarks      — metric reference table
    #     """
    #     try:
    #         import openpyxl
    #         from openpyxl.styles import (Font, PatternFill,
    #                                       Alignment, Border, Side)
    #         from openpyxl.utils  import get_column_letter
    #     except ImportError:
    #         console.print("[red]openpyxl not installed. "
    #                       "Run: pip install openpyxl[/red]")
    #         return

    #     if df is None or df.empty:
    #         console.print("[yellow]  Nothing to export.[/yellow]")
    #         return

    #     wb  = openpyxl.Workbook()
    #     # Remove default sheet
    #     if "Sheet" in wb.sheetnames:
    #         del wb["Sheet"]

    #     thin   = Side(style="thin", color="CCCCCC")
    #     border = Border(left=thin, right=thin, top=thin, bottom=thin)

    #     # ── Benchmark colour thresholds ───────────────────────────────────────
    #     BENCH_FILL = {
    #         "excellent": "C6EFCE",   # light green
    #         "good"     : "DDEBF7",   # light blue
    #         "average"  : "FFEB9C",   # light yellow
    #         "poor"     : "FFC7CE",   # light red
    #     }

    #     def get_fill_hex(col: str, val: Any) -> Optional[str]:
    #         """Return fill hex for a cell based on benchmark."""
    #         v     = _to_float(val)
    #         if v is None:
    #             return None
    #         bench = METRIC_BENCHMARKS.get(col, {})
    #         h     = bench.get("higher_is_better", True)
    #         exc   = bench.get("excellent")
    #         gd    = bench.get("good")
    #         avg   = bench.get("average")
    #         if exc is None:
    #             return None
    #         if h:
    #             if   v >= exc: return BENCH_FILL["excellent"]
    #             elif gd  and v >= gd:  return BENCH_FILL["good"]
    #             elif avg and v >= avg: return BENCH_FILL["average"]
    #             else:                  return BENCH_FILL["poor"]
    #         else:
    #             if   v <= exc: return BENCH_FILL["excellent"]
    #             elif gd  and v <= gd:  return BENCH_FILL["good"]
    #             elif avg and v <= avg: return BENCH_FILL["average"]
    #             else:                  return BENCH_FILL["poor"]

    #     def write_df_to_sheet(ws, data: pd.DataFrame,
    #                            header_colour: str = "1F4E79",
    #                            colour_cells:  bool = True):
    #         """Write a DataFrame to an openpyxl worksheet."""
    #         cols = list(data.columns)

    #         # ── Header row ────────────────────────────────────────────────────
    #         for ci, col in enumerate(cols, 1):
    #             c = ws.cell(row=1, column=ci, value=col)
    #             c.font      = Font(bold=True, color="FFFFFF",
    #                                size=10, name="Calibri")
    #             c.fill      = PatternFill("solid", fgColor=header_colour)
    #             c.alignment = Alignment(horizontal="center",
    #                                     wrap_text=True, vertical="center")
    #             c.border    = border
    #         ws.row_dimensions[1].height = 28

    #         # ── Data rows ─────────────────────────────────────────────────────
    #         for ri, (_, row) in enumerate(data.iterrows(), 2):
    #             for ci, col in enumerate(cols, 1):
    #                 raw = row.get(col)

    #                 # Convert NaN → None for cleaner Excel output
    #                 if isinstance(raw, float) and np.isnan(raw):
    #                     raw = None

    #                 # Numeric value for Excel
    #                 num = _to_float(raw)
    #                 cell_val = num if num is not None else (
    #                     str(raw) if raw is not None else ""
    #                 )

    #                 c = ws.cell(row=ri, column=ci, value=cell_val)
    #                 c.border = border
    #                 c.font   = Font(size=9, name="Calibri")

    #                 # Alignment
    #                 text_cols = {"Symbol", "Company", "Sector",
    #                              "Sub-Sector", "Data Status",
    #                              "Source URL", "Scraped At",
    #                              "Revenue Y1 Period",
    #                              "Revenue Y2 Period",
    #                              "Revenue Y3 Period",
    #                              "EBITDA Y1 Period",
    #                              "PAT Y1 Period",
    #                              "FCF Y1 Period"}
    #                 c.alignment = Alignment(
    #                     horizontal="left" if col in text_cols else "right",
    #                     vertical="center",
    #                 )

    #                 # Colour-code metric cells
    #                 if colour_cells:
    #                     hex_c = get_fill_hex(col, raw)
    #                     if hex_c:
    #                         c.fill = PatternFill("solid", fgColor=hex_c)

    #         # ── Column widths ─────────────────────────────────────────────────
    #         for col_cells in ws.columns:
    #             max_w = max(
    #                 (len(str(c.value or "")) for c in col_cells),
    #                 default=10,
    #             )
    #             ws.column_dimensions[
    #                 get_column_letter(col_cells[0].column)
    #             ].width = min(max_w + 3, 38)

    #         ws.freeze_panes    = "C2"
    #         ws.auto_filter.ref = ws.dimensions

    #     # ── Sheet 1: Main analysis ────────────────────────────────────────────
    #     ws1       = wb.create_sheet(f"{sector[:25]} Analysis")
    #     write_df_to_sheet(ws1, df, header_colour="1F4E79")
    #     console.print(
    #         f"  Sheet 1: {sector} Analysis ({len(df)} companies)"
    #     )

    #     # ── Sheet 2: Sector Summary ───────────────────────────────────────────
    #     ws2 = wb.create_sheet("📊 Sector Summary")
    #     summary_cols = [
    #         "Revenue Growth (%)",
    #         "EBITDA Margin (%)",
    #         "PAT Margin (%)",
    #         "ROE (%)",
    #         "ROCE (%)",
    #         "ROA (%)",
    #         "P/E Ratio",
    #         "Debt to Equity",
    #         "Current Ratio",
    #         "Revenue Y1 (Cr)",
    #         "PAT Y1 (Cr)",
    #         "EBITDA Y1 (Cr)",
    #         "FCF Y1 (Cr)",
    #     ]
    #     summary_rows = []
    #     for col in summary_cols:
    #         if col not in df.columns:
    #             continue
    #         series = _safe_series(df, col).dropna()
    #         if series.empty:
    #             continue
    #         h_b   = METRIC_BENCHMARKS.get(col, {}).get("higher_is_better", True)
    #         best  = series.max() if h_b else series.min()
    #         worst = series.min() if h_b else series.max()

    #         # Leader
    #         idx_best  = series.idxmax() if h_b else series.idxmin()
    #         leader_sym = str(df.loc[idx_best, "Symbol"]) \
    #                      if "Symbol" in df.columns else ""

    #         summary_rows.append({
    #             "Metric"       : col,
    #             "Category"     : METRIC_BENCHMARKS.get(col, {}).get("category",""),
    #             "Companies"    : len(series),
    #             "Mean"         : round(series.mean(),   2),
    #             "Median"       : round(series.median(), 2),
    #             "Best"         : round(best,  2),
    #             "Worst"        : round(worst, 2),
    #             "Std Dev"      : round(series.std(), 2),
    #             "Leader"       : leader_sym,
    #             "Sector"       : sector,
    #             "Generated At" : datetime.now().strftime("%Y-%m-%d %H:%M"),
    #         })

    #     if summary_rows:
    #         sum_df = pd.DataFrame(summary_rows)
    #         write_df_to_sheet(ws2, sum_df,
    #                            header_colour="1F6B3B",
    #                            colour_cells=False)
    #         console.print(
    #             f"  Sheet 2: 📊 Sector Summary ({len(summary_rows)} metrics)"
    #         )

    #     # ── Sheet 3: Benchmark Legend ─────────────────────────────────────────
    #     ws3 = wb.create_sheet("📖 Benchmarks")
    #     bench_rows = []
    #     for metric, bench in METRIC_BENCHMARKS.items():
    #         unit = bench.get("unit", "")
    #         def fmtb(v):
    #             return f"{v}{unit}" if v is not None else "Varies"
    #         bench_rows.append({
    #             "Category"       : bench.get("category",    ""),
    #             "Metric"         : metric,
    #             "Description"    : bench.get("description", ""),
    #             "Excellent"      : fmtb(bench.get("excellent")),
    #             "Good"           : fmtb(bench.get("good")),
    #             "Average"        : fmtb(bench.get("average")),
    #             "Poor"           : fmtb(bench.get("poor")),
    #             "Unit"           : unit,
    #             "Higher is Better": "Yes" if bench.get("higher_is_better") else "No",
    #         })

    #     # Add sector P/E table
    #     bench_rows.append({
    #         "Category": "─── Sector P/E Benchmarks ───",
    #         "Metric": "", "Description": "",
    #         "Excellent": "", "Good": "", "Average": "",
    #         "Poor": "", "Unit": "", "Higher is Better": "",
    #     })
    #     for sec, pe_vals in SECTOR_PE_BENCHMARKS.items():
    #         bench_rows.append({
    #             "Category"        : "Valuation",
    #             "Metric"          : f"P/E — {sec}",
    #             "Description"     : "Sector-specific P/E benchmark",
    #             "Excellent"       : f"< {pe_vals['fair']}x",
    #             "Good"            : f"{pe_vals['fair']}–{pe_vals['expensive']}x",
    #             "Average"         : "",
    #             "Poor"            : f"> {pe_vals['expensive']}x",
    #             "Unit"            : "x",
    #             "Higher is Better": "No",
    #         })

    #     bench_df = pd.DataFrame(bench_rows)
    #     write_df_to_sheet(ws3, bench_df,
    #                        header_colour="7B2D8B",
    #                        colour_cells=False)
    #     console.print("  Sheet 3: 📖 Benchmarks")

    #     # ── Save ──────────────────────────────────────────────────────────────
    #     try:
    #         wb.save(path)
    #         console.print(
    #             f"\n  [bold green]✅ Excel saved → {path}[/bold green]"
    #         )
    #         console.print(
    #             f"  Sheets: {wb.sheetnames}"
    #         )
    #     except PermissionError:
    #         console.print(
    #             f"\n  [red]❌ Permission denied: {path}\n"
    #             "  Close the file in Excel and retry.[/red]"
    #         )
    #     except Exception as e:
    #         console.print(f"\n  [red]Save error: {e}[/red]")
    #         self.logger.error(f"Excel save error: {e}", exc_info=True)
# In sector_analyzer.py — replace the entire export_analysis method

    def export_analysis(self,
                        df     : pd.DataFrame,
                        sector : str,
                        path   : str):
        """
        Export the analysed DataFrame to a colour-coded Excel workbook.

        Sheets:
        1. <Sector> Analysis  — all companies, colour-coded
        2. Sector Summary     — averages + ratings
        3. Benchmarks         — metric reference
        """
        # ── Guard imports ─────────────────────────────────────────────────────────
        from datetime import datetime as _datetime   # local import as safety net

        try:
            import openpyxl
            from openpyxl.styles import (Font, PatternFill,
                                        Alignment, Border, Side)
            from openpyxl.utils  import get_column_letter
        except ImportError:
            console.print(
                "[red]openpyxl not installed. "
                "Run: pip install openpyxl[/red]"
            )
            return

        if df is None or df.empty:
            console.print("[yellow]  Nothing to export.[/yellow]")
            return

        wb = openpyxl.Workbook()
        if "Sheet" in wb.sheetnames:
            del wb["Sheet"]

        thin   = Side(style="thin", color="CCCCCC")
        border = Border(left=thin, right=thin, top=thin, bottom=thin)

        # ── Benchmark colour map ──────────────────────────────────────────────────
        BENCH_FILL = {
            "excellent": "C6EFCE",
            "good"     : "DDEBF7",
            "average"  : "FFEB9C",
            "poor"     : "FFC7CE",
        }

        def get_fill_hex(col: str, val) -> Optional[str]:
            v     = _to_float(val)
            if v is None:
                return None
            bench = METRIC_BENCHMARKS.get(col, {})
            h     = bench.get("higher_is_better", True)
            exc   = bench.get("excellent")
            gd    = bench.get("good")
            avg   = bench.get("average")
            if exc is None:
                return None
            if h:
                if   v >= exc:                return BENCH_FILL["excellent"]
                elif gd  is not None and v >= gd:  return BENCH_FILL["good"]
                elif avg is not None and v >= avg: return BENCH_FILL["average"]
                else:                              return BENCH_FILL["poor"]
            else:
                if   v <= exc:                return BENCH_FILL["excellent"]
                elif gd  is not None and v <= gd:  return BENCH_FILL["good"]
                elif avg is not None and v <= avg: return BENCH_FILL["average"]
                else:                              return BENCH_FILL["poor"]

        def write_df_to_sheet(ws,
                            data: pd.DataFrame,
                            header_colour: str = "1F4E79",
                            colour_cells: bool = True):
            """Write DataFrame to openpyxl worksheet with formatting."""
            cols = list(data.columns)

            # Header row
            for ci, col in enumerate(cols, 1):
                c           = ws.cell(row=1, column=ci, value=col)
                c.font      = Font(bold=True, color="FFFFFF",
                                size=10, name="Calibri")
                c.fill      = PatternFill("solid", fgColor=header_colour)
                c.alignment = Alignment(horizontal="center",
                                        wrap_text=True, vertical="center")
                c.border    = border
            ws.row_dimensions[1].height = 28

            # Text columns (left-aligned)
            text_cols = {
                "Symbol", "Company", "Sector", "Sub-Sector",
                "Data Status", "Source URL", "Scraped At",
                "Revenue Y1 Period", "Revenue Y2 Period",
                "Revenue Y3 Period", "EBITDA Y1 Period",
                "PAT Y1 Period", "FCF Y1 Period",
            }

            # Data rows
            for ri, (_, row) in enumerate(data.iterrows(), 2):
                for ci, col in enumerate(cols, 1):
                    raw = row.get(col)

                    # NaN → None for clean Excel output
                    if isinstance(raw, float) and np.isnan(raw):
                        raw = None

                    # Use numeric value in Excel if possible
                    num      = _to_float(raw)
                    cell_val = (num if num is not None
                                else (str(raw) if raw is not None else ""))

                    c           = ws.cell(row=ri, column=ci, value=cell_val)
                    c.border    = border
                    c.font      = Font(size=9, name="Calibri")
                    c.alignment = Alignment(
                        horizontal = "left" if col in text_cols else "right",
                        vertical   = "center",
                    )

                    # Colour-code metric cells
                    if colour_cells:
                        hex_c = get_fill_hex(col, raw)
                        if hex_c:
                            c.fill = PatternFill("solid", fgColor=hex_c)

            # Auto column widths
            for col_cells in ws.columns:
                max_w = max(
                    (len(str(c.value or "")) for c in col_cells),
                    default=10,
                )
                ws.column_dimensions[
                    get_column_letter(col_cells[0].column)
                ].width = min(max_w + 3, 38)

            ws.freeze_panes    = "C2"
            ws.auto_filter.ref = ws.dimensions

        # ── Sheet 1: Main Analysis ────────────────────────────────────────────────
        ws1 = wb.create_sheet(f"{sector[:25]} Analysis")
        write_df_to_sheet(ws1, df, header_colour="1F4E79")
        console.print(
            f"  Sheet 1: {sector} Analysis "
            f"({len(df)} companies)"
        )

        # ── Sheet 2: Sector Summary ───────────────────────────────────────────────
        ws2 = wb.create_sheet("📊 Sector Summary")

        summary_metric_cols = [
            "Revenue Growth (%)",
            "EBITDA Margin (%)",
            "PAT Margin (%)",
            "ROE (%)",
            "ROCE (%)",
            "ROA (%)",
            "P/E Ratio",
            "Debt to Equity",
            "Current Ratio",
            "Revenue Y1 (Cr)",
            "PAT Y1 (Cr)",
            "EBITDA Y1 (Cr)",
            "FCF Y1 (Cr)",
        ]

        summary_rows = []
        now_str = _datetime.now().strftime("%Y-%m-%d %H:%M")   # ← fixed

        for col in summary_metric_cols:
            if col not in df.columns:
                continue
            series = _safe_series(df, col).dropna()
            if series.empty:
                continue

            h_b   = METRIC_BENCHMARKS.get(col, {}).get(
                "higher_is_better", True
            )
            best  = series.max() if h_b else series.min()
            worst = series.min() if h_b else series.max()

            # Leader symbol
            try:
                idx_best   = series.idxmax() if h_b else series.idxmin()
                leader_sym = str(df.loc[idx_best, "Symbol"]) \
                            if "Symbol" in df.columns else ""
            except Exception:
                leader_sym = ""

            summary_rows.append({
                "Metric"       : col,
                "Category"     : METRIC_BENCHMARKS.get(
                    col, {}
                ).get("category", ""),
                "Companies"    : int(len(series)),
                "Mean"         : round(float(series.mean()),   2),
                "Median"       : round(float(series.median()), 2),
                "Best"         : round(float(best),            2),
                "Worst"        : round(float(worst),           2),
                "Std Dev"      : round(float(series.std()),    2),
                "Leader"       : leader_sym,
                "Sector"       : sector,
                "Generated At" : now_str,                       # ← fixed
            })

        if summary_rows:
            sum_df = pd.DataFrame(summary_rows)
            write_df_to_sheet(
                ws2, sum_df,
                header_colour="1F6B3B",
                colour_cells=False,
            )
            console.print(
                f"  Sheet 2: 📊 Sector Summary "
                f"({len(summary_rows)} metrics)"
            )

        # ── Sheet 3: Benchmark Reference ─────────────────────────────────────────
        ws3 = wb.create_sheet("📖 Benchmarks")

        bench_rows = []
        for metric, bench in METRIC_BENCHMARKS.items():
            unit = bench.get("unit", "")
            def fmtb(v):
                return f"{v}{unit}" if v is not None else "Varies"
            bench_rows.append({
                "Category"        : bench.get("category",    ""),
                "Metric"          : metric,
                "Description"     : bench.get("description", ""),
                "Excellent"       : fmtb(bench.get("excellent")),
                "Good"            : fmtb(bench.get("good")),
                "Average"         : fmtb(bench.get("average")),
                "Poor"            : fmtb(bench.get("poor")),
                "Unit"            : unit,
                "Higher is Better": "Yes" if bench.get(
                    "higher_is_better"
                ) else "No",
            })

        # Separator
        bench_rows.append({k: "" for k in bench_rows[0].keys()} if bench_rows else {})
        if bench_rows:
            bench_rows[-1]["Category"] = "── Sector P/E Benchmarks ──"

        # Sector P/E rows
        for sec, pe_vals in SECTOR_PE_BENCHMARKS.items():
            bench_rows.append({
                "Category"        : "Valuation",
                "Metric"          : f"P/E — {sec}",
                "Description"     : "Sector-specific P/E benchmark",
                "Excellent"       : f"< {pe_vals['fair']}x",
                "Good"            : f"{pe_vals['fair']}–{pe_vals['expensive']}x",
                "Average"         : "",
                "Poor"            : f"> {pe_vals['expensive']}x",
                "Unit"            : "x",
                "Higher is Better": "No",
            })

        if bench_rows:
            bench_df = pd.DataFrame(bench_rows)
            write_df_to_sheet(
                ws3, bench_df,
                header_colour="7B2D8B",
                colour_cells=False,
            )
            console.print("  Sheet 3: 📖 Benchmarks")

        # ── Save workbook ─────────────────────────────────────────────────────────
        try:
            wb.save(path)
            console.print(
                f"\n  [bold green]✅ Excel saved → {path}[/bold green]"
            )
            console.print(f"  Sheets: {wb.sheetnames}")

        except PermissionError:
            console.print(
                f"\n  [red]❌ Permission denied: {path}\n"
                "  Close the file in Excel and retry.[/red]"
            )
        except Exception as e:
            console.print(f"\n  [red]Save error: {e}[/red]")
            self.logger.error(
                f"Excel save error: {e}", exc_info=True
            )

# ─────────────────────────────────────────────────────────────────────────────
# Standalone test
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from datetime import datetime

    print("\n" + "="*60)
    print("  sector_analyzer.py — Self Test")
    print("="*60)

    # ── Sample data mimicking Screener output ─────────────────────────────────
    sample_fin = pd.DataFrame([
        {
            "symbol"           : "TCS",
            "company"          : "Tata Consultancy Services",
            "Sector"           : "Information Technology",
            "Revenue Y1 (Cr)"  : 240893,
            "Revenue Y2 (Cr)"  : 225458,
            "Revenue Y3 (Cr)"  : 191754,
            "Revenue Y1 Period": "Mar 2024",
            "Revenue Y2 Period": "Mar 2023",
            "Revenue Y3 Period": "Mar 2022",
            "Revenue Growth (%)" : None,        # will be computed
            "EBITDA Y1 (Cr)"   : 60223,
            "EBITDA Y2 (Cr)"   : 57450,
            "EBITDA Y3 (Cr)"   : 50022,
            "EBITDA Margin (%)" : None,         # will be computed
            "PAT Y1 (Cr)"      : 46099,
            "PAT Y2 (Cr)"      : 42303,
            "PAT Y3 (Cr)"      : 38327,
            "PAT Margin (%)"   : None,          # will be computed
            "ROE (%)"          : 51.8,
            "ROCE (%)"         : 63.0,
            "ROA (%)"          : 22.5,
            "EPS (₹)"          : 124.9,
            "P/E Ratio"        : 19.2,
            "Debt to Equity"   : 0.02,
            "Current Ratio"    : 2.8,
            "FCF Y1 (Cr)"      : 41200,
            "FCF Y2 (Cr)"      : 38900,
            "FCF Y3 (Cr)"      : 35600,
            "Market Cap (Cr)"  : 866315,
            "Dividend Yield (%)": 2.67,
            "Book Value (₹)"   : 296,
        },
        {
            "symbol"           : "INFY",
            "company"          : "Infosys",
            "Sector"           : "Information Technology",
            "Revenue Y1 (Cr)"  : 153670,
            "Revenue Y2 (Cr)"  : 146767,
            "Revenue Y3 (Cr)"  : 121641,
            "Revenue Y1 Period": "Mar 2024",
            "Revenue Y2 Period": "Mar 2023",
            "Revenue Y3 Period": "Mar 2022",
            "Revenue Growth (%)" : None,
            "EBITDA Y1 (Cr)"   : 36881,
            "EBITDA Y2 (Cr)"   : 36691,
            "EBITDA Y3 (Cr)"   : 30328,
            "EBITDA Margin (%)" : None,
            "PAT Y1 (Cr)"      : 26248,
            "PAT Y2 (Cr)"      : 24095,
            "PAT Y3 (Cr)"      : 22110,
            "PAT Margin (%)"   : None,
            "ROE (%)"          : 31.5,
            "ROCE (%)"         : 39.0,
            "ROA (%)"          : 17.8,
            "EPS (₹)"          : 62.9,
            "P/E Ratio"        : 22.4,
            "Debt to Equity"   : 0.08,
            "Current Ratio"    : 2.1,
            "FCF Y1 (Cr)"      : 22800,
            "FCF Y2 (Cr)"      : 21500,
            "FCF Y3 (Cr)"      : 19200,
            "Market Cap (Cr)"  : 780000,
            "Dividend Yield (%)": 3.2,
            "Book Value (₹)"   : 210,
        },
        {
            "symbol"           : "WIPRO",
            "company"          : "Wipro",
            "Sector"           : "Information Technology",
            "Revenue Y1 (Cr)"  : 89376,
            "Revenue Y2 (Cr)"  : 90488,
            "Revenue Y3 (Cr)"  : 79312,
            "Revenue Y1 Period": "Mar 2024",
            "Revenue Y2 Period": "Mar 2023",
            "Revenue Y3 Period": "Mar 2022",
            "Revenue Growth (%)" : None,
            "EBITDA Y1 (Cr)"   : 16888,
            "EBITDA Y2 (Cr)"   : 17193,
            "EBITDA Y3 (Cr)"   : 16265,
            "EBITDA Margin (%)" : None,
            "PAT Y1 (Cr)"      : 11148,
            "PAT Y2 (Cr)"      : 11366,
            "PAT Y3 (Cr)"      : 12236,
            "PAT Margin (%)"   : None,
            "ROE (%)"          : 14.8,
            "ROCE (%)"         : 16.9,
            "ROA (%)"          : 8.5,
            "EPS (₹)"          : 21.3,
            "P/E Ratio"        : 20.5,
            "Debt to Equity"   : 0.15,
            "Current Ratio"    : 2.4,
            "FCF Y1 (Cr)"      : 13400,
            "FCF Y2 (Cr)"      : 11800,
            "FCF Y3 (Cr)"      : 12100,
            "Market Cap (Cr)"  : 320000,
            "Dividend Yield (%)": 0.18,
            "Book Value (₹)"   : 154,
        },
    ])

    # Sample price data (lowercase keys — tests normalise_columns)
    sample_price = pd.DataFrame([
        {"symbol": "TCS",   "price": 2394.0, "change (%)":  0.85,
         "volume": 1200000},
        {"symbol": "INFY",  "price": 1580.0, "change (%)": -0.42,
         "volume": 2100000},
        {"symbol": "WIPRO", "price":  450.0, "change (%)":  1.20,
         "volume": 3500000},
    ])

    # ── Run analysis ──────────────────────────────────────────────────────────
    analyzer = SectorAnalyzer()
    result   = analyzer.analyze(sample_fin, sample_price, "Information Technology")

    print(f"\n  Analyzed DataFrame: {result.shape}")
    print(f"  Columns: {list(result.columns)}")
    print(f"  Revenue Growth computed: "
          f"{result['Revenue Growth (%)'].tolist()}")
    print(f"  PAT Margin computed: "
          f"{result['PAT Margin (%)'].tolist()}")
    print(f"  EBITDA Margin computed: "
          f"{result['EBITDA Margin (%)'].tolist()}")

    # ── Display in terminal ───────────────────────────────────────────────────
    analyzer.show_metric_table(
        result, "Information Technology", top_n=3
    )

    # ── Export to Excel ───────────────────────────────────────────────────────
    out_path = os.path.join(
        _THIS_DIR, "output",
        f"IT_Test_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
    )
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    analyzer.export_analysis(result, "Information Technology", out_path)

    print("\n✅ sector_analyzer.py self-test complete!")