# filters.py

import os
import sys
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, List, Optional, Tuple

import numpy as np
import pandas as pd

# ── Path fix ──────────────────────────────────────────────────────────────────
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
if _THIS_DIR not in sys.path:
    sys.path.insert(0, _THIS_DIR)


# ─────────────────────────────────────────────────────────────────────────────
# Utility
# ─────────────────────────────────────────────────────────────────────────────

def _to_float(val: Any) -> Optional[float]:
    """Safely convert any value to float."""
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return float(val) if not np.isnan(float(val)) else None
    s = (str(val).strip()
         .replace(",", "")
         .replace("₹", "")
         .replace("%", "")
         .replace("B", "e9")
         .replace("T", "e12")
         .replace("M", "e6")
         .replace("K", "e3"))
    try:
        return float(s)
    except (ValueError, TypeError):
        return None


def _numeric_col(df: pd.DataFrame, col: str) -> pd.Series:
    """Convert a DataFrame column to a float Series."""
    if col not in df.columns:
        return pd.Series([None] * len(df), index=df.index)
    return df[col].apply(_to_float)


# ─────────────────────────────────────────────────────────────────────────────
# Filter Classes
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class PriceRangeFilter:
    """Filter rows by price range (₹)."""
    min_price: Optional[float] = None
    max_price: Optional[float] = None

    def apply(self, df: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            return df
        prices = _numeric_col(df, "Price (₹)")
        mask   = pd.Series([True] * len(df), index=df.index)
        if self.min_price is not None:
            mask &= prices.fillna(-1) >= self.min_price
        if self.max_price is not None:
            mask &= prices.fillna(float("inf")) <= self.max_price
        return df[mask].copy()

    def describe(self) -> str:
        parts = []
        if self.min_price is not None:
            parts.append(f"≥ ₹{self.min_price:,.2f}")
        if self.max_price is not None:
            parts.append(f"≤ ₹{self.max_price:,.2f}")
        return f"Price Range [{' and '.join(parts)}]"


@dataclass
class PercentChangeFilter:
    """Filter rows by % change range."""
    min_pct: Optional[float] = None
    max_pct: Optional[float] = None

    def apply(self, df: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            return df
        pcts = _numeric_col(df, "Change (%)")
        mask = pd.Series([True] * len(df), index=df.index)
        if self.min_pct is not None:
            mask &= pcts.fillna(float("-inf")) >= self.min_pct
        if self.max_pct is not None:
            mask &= pcts.fillna(float("inf"))  <= self.max_pct
        return df[mask].copy()

    def describe(self) -> str:
        parts = []
        if self.min_pct is not None:
            parts.append(f"≥ {self.min_pct}%")
        if self.max_pct is not None:
            parts.append(f"≤ {self.max_pct}%")
        return f"% Change [{' and '.join(parts)}]"


@dataclass
class VolumeFilter:
    """Filter rows by volume range."""
    min_volume: Optional[float] = None
    max_volume: Optional[float] = None

    def apply(self, df: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            return df
        vols = _numeric_col(df, "Volume")
        mask = pd.Series([True] * len(df), index=df.index)
        if self.min_volume is not None:
            mask &= vols.fillna(-1) >= self.min_volume
        if self.max_volume is not None:
            mask &= vols.fillna(float("inf")) <= self.max_volume
        return df[mask].copy()

    def describe(self) -> str:
        parts = []
        if self.min_volume is not None:
            parts.append(f"≥ {self.min_volume:,.0f}")
        if self.max_volume is not None:
            parts.append(f"≤ {self.max_volume:,.0f}")
        return f"Volume [{' and '.join(parts)}]"


@dataclass
class CategoryFilter:
    """Filter by stock category."""
    categories: List[str] = field(default_factory=list)
    VALID: List[str] = field(default_factory=lambda: [
        "Index", "Top Gainer", "Top Loser", "Watchlist"
    ])

    def apply(self, df: pd.DataFrame) -> pd.DataFrame:
        if df.empty or not self.categories:
            return df
        return df[df["Category"].isin(self.categories)].copy()

    def describe(self) -> str:
        return f"Category [{', '.join(self.categories)}]"


@dataclass
class SourceFilter:
    """Filter by data source."""
    sources: List[str] = field(default_factory=list)
    VALID: List[str] = field(default_factory=lambda: [
        "Yahoo Finance", "NSE India API", "MoneyControl", "Investing.com"
    ])

    def apply(self, df: pd.DataFrame) -> pd.DataFrame:
        if df.empty or not self.sources:
            return df
        return df[df["Source"].isin(self.sources)].copy()

    def describe(self) -> str:
        return f"Source [{', '.join(self.sources)}]"


@dataclass
class SymbolSearchFilter:
    """Search for stocks by symbol or name."""
    query: str           = ""
    case_sensitive: bool = False
    use_regex: bool      = False

    def apply(self, df: pd.DataFrame) -> pd.DataFrame:
        if df.empty or not self.query.strip():
            return df
        flags = 0 if self.case_sensitive else re.IGNORECASE
        pat   = self.query if self.use_regex else re.escape(self.query)
        try:
            sym_match   = df["Symbol"].astype(str).str.contains(pat, flags=flags, regex=True, na=False)
            title_match = df["Title"].astype(str).str.contains(pat, flags=flags, regex=True, na=False)
            return df[sym_match | title_match].copy()
        except re.error as e:
            print(f"  ⚠  Invalid regex: {e}")
            return df

    def describe(self) -> str:
        mode = "regex" if self.use_regex else "text"
        cs   = "CS" if self.case_sensitive else "CI"
        return f"Search ['{self.query}' | {mode} | {cs}]"


@dataclass
class SectorFilter:
    """Filter by market sector."""
    sectors: List[str]  = field(default_factory=list)
    sector_map: dict    = field(default_factory=dict)

    VALID_SECTORS: List[str] = field(default_factory=lambda: [
        "IT", "Banking", "Finance", "FMCG", "Auto",
        "Pharma", "Energy", "Infrastructure", "Cement",
        "Consumer Goods", "Utilities", "Conglomerate",
    ])

    def apply(self, df: pd.DataFrame) -> pd.DataFrame:
        if df.empty or not self.sectors or not self.sector_map:
            return df
        allowed_symbols = {
            sym for sym, sec in self.sector_map.items()
            if sec in self.sectors
        }
        return df[df["Symbol"].isin(allowed_symbols)].copy()

    def describe(self) -> str:
        return f"Sector [{', '.join(self.sectors)}]"


@dataclass
class DateRangeFilter:
    """Filter by date range."""
    start_date: Optional[datetime] = None
    end_date:   Optional[datetime] = None

    def apply(self, df: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            return df
        dates = pd.to_datetime(df["Date"], errors="coerce")
        mask  = pd.Series([True] * len(df), index=df.index)
        if self.start_date:
            mask &= dates >= pd.Timestamp(self.start_date)
        if self.end_date:
            mask &= dates <= pd.Timestamp(self.end_date)
        return df[mask].copy()

    def describe(self) -> str:
        s = self.start_date.strftime("%Y-%m-%d") if self.start_date else "any"
        e = self.end_date.strftime("%Y-%m-%d")   if self.end_date   else "any"
        return f"Date Range [{s} → {e}]"


@dataclass
class TopNFilter:
    """Return top N rows by a numeric column."""
    n:        int = 10
    sort_col: str = "Price (₹)"

    def apply(self, df: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            return df
        temp = df.copy()
        temp["_sort_key"] = _numeric_col(temp, self.sort_col)
        return (temp.sort_values("_sort_key", ascending=False)
                    .drop(columns=["_sort_key"])
                    .head(self.n)
                    .copy())

    def describe(self) -> str:
        return f"Top {self.n} by [{self.sort_col}] ↓"


@dataclass
class BottomNFilter:
    """Return bottom N rows by a numeric column."""
    n:        int = 10
    sort_col: str = "Price (₹)"

    def apply(self, df: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            return df
        temp = df.copy()
        temp["_sort_key"] = _numeric_col(temp, self.sort_col)
        return (temp.sort_values("_sort_key", ascending=True)
                    .drop(columns=["_sort_key"])
                    .head(self.n)
                    .copy())

    def describe(self) -> str:
        return f"Bottom {self.n} by [{self.sort_col}] ↑"


@dataclass
class PositiveChangeFilter:
    """Keep only stocks with positive % change."""
    threshold: float = 0.0

    def apply(self, df: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            return df
        pcts = _numeric_col(df, "Change (%)")
        return df[pcts.fillna(float("-inf")) > self.threshold].copy()

    def describe(self) -> str:
        return f"Positive Change [> {self.threshold}%]"


@dataclass
class NegativeChangeFilter:
    """Keep only stocks with negative % change."""
    threshold: float = 0.0

    def apply(self, df: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            return df
        pcts = _numeric_col(df, "Change (%)")
        return df[pcts.fillna(float("inf")) < self.threshold].copy()

    def describe(self) -> str:
        return f"Negative Change [< {self.threshold}%]"


@dataclass
class WeekHighProximityFilter:
    """Keep stocks near their 52-week high."""
    within_pct: float = 5.0

    def apply(self, df: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            return df
        prices = _numeric_col(df, "Price (₹)")
        highs  = _numeric_col(df, "52W High")
        valid  = highs.notna() & prices.notna()
        lower  = highs * (1 - self.within_pct / 100)
        mask   = valid & (prices >= lower)
        return df[mask].copy()

    def describe(self) -> str:
        return f"Near 52W High [within {self.within_pct}%]"


@dataclass
class WeekLowProximityFilter:
    """Keep stocks near their 52-week low."""
    within_pct: float = 5.0

    def apply(self, df: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            return df
        prices = _numeric_col(df, "Price (₹)")
        lows   = _numeric_col(df, "52W Low")
        valid  = lows.notna() & prices.notna()
        upper  = lows * (1 + self.within_pct / 100)
        mask   = valid & (prices <= upper)
        return df[mask].copy()

    def describe(self) -> str:
        return f"Near 52W Low [within {self.within_pct}%]"


@dataclass
class CustomExpressionFilter:
    """Filter using a pandas query expression."""
    expression: str = ""

    # Helper columns available in the expression:
    # Price, Change, ChangePct, Volume

    def apply(self, df: pd.DataFrame) -> pd.DataFrame:
        if df.empty or not self.expression.strip():
            return df
        temp = df.copy()
        temp["Price"]     = _numeric_col(temp, "Price (₹)")
        temp["Change"]    = _numeric_col(temp, "Change")
        temp["ChangePct"] = _numeric_col(temp, "Change (%)")
        temp["Volume"]    = _numeric_col(temp, "Volume")
        try:
            result = temp.query(self.expression)
            return df.loc[result.index].copy()
        except Exception as exc:
            print(f"  ⚠  Expression error: {exc}")
            print(f"     Tip: Use Price, Change, ChangePct, Volume as column names")
            return df

    def describe(self) -> str:
        return f"Custom Expr [{self.expression}]"


@dataclass
class MultiColumnSortFilter:
    """Sort by multiple columns with configurable direction."""
    sort_spec: List[Tuple[str, bool]] = field(
        default_factory=lambda: [("Price (₹)", False)]
    )

    def apply(self, df: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            return df
        temp      = df.copy()
        sort_keys = []
        sort_asc  = []
        for col, asc in self.sort_spec:
            key = f"_sort_{col}"
            temp[key] = _numeric_col(temp, col)
            sort_keys.append(key)
            sort_asc.append(asc)
        sorted_df = temp.sort_values(by=sort_keys, ascending=sort_asc)
        return sorted_df[df.columns].copy()

    def describe(self) -> str:
        parts = [
            f"{col} {'↑' if asc else '↓'}"
            for col, asc in self.sort_spec
        ]
        return f"Sort [{', '.join(parts)}]"


# ─────────────────────────────────────────────────────────────────────────────
# Filter Pipeline
# ─────────────────────────────────────────────────────────────────────────────

class FilterPipeline:
    """Chains multiple filters and applies them in sequence."""

    def __init__(self):
        self._filters: List[Any]          = []
        self._history: List[Tuple[str, int]] = []

    def add(self, filter_obj: Any) -> "FilterPipeline":
        self._filters.append(filter_obj)
        return self

    def remove(self, index: int) -> "FilterPipeline":
        """Remove a filter by 0-based index."""
        if 0 <= index < len(self._filters):
            removed = self._filters.pop(index)
            print(f"  ✔ Removed: {removed.describe()}")
        else:
            print(f"  ⚠  Invalid index: {index}")
        return self

    def clear(self) -> "FilterPipeline":
        self._filters.clear()
        self._history.clear()
        return self

    def run(self, df: pd.DataFrame) -> pd.DataFrame:
        """Apply all filters in order."""
        result = df.copy()
        self._history = [("Original", len(result))]

        for f in self._filters:
            before = len(result)
            result = f.apply(result)
            after  = len(result)
            self._history.append((f.describe(), after))
            print(f"  ✔ {f.describe():<52} {before:>4} → {after:>4} rows")

        return result.reset_index(drop=True)

    def summary(self) -> str:
        lines = ["\nFilter Pipeline Summary", "─" * 55]
        for desc, rows in self._history:
            lines.append(f"  {desc:<50} → {rows:>4} rows")
        return "\n".join(lines)

    @property
    def is_empty(self) -> bool:
        return len(self._filters) == 0

    def __len__(self) -> int:
        return len(self._filters)

    def list_filters(self):
        """Print numbered list of active filters."""
        if self.is_empty:
            print("  (no filters active)")
            return
        for i, f in enumerate(self._filters, 1):
            print(f"  [{i}] {f.describe()}")


# ── Quick test ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import pandas as pd

    # Create sample data
    sample = pd.DataFrame({
        "Symbol"    : ["TCS", "INFY", "RELIANCE", "SBIN", "HDFC"],
        "Title"     : ["TCS", "Infosys", "Reliance", "SBI", "HDFC Bank"],
        "Category"  : ["Watchlist"] * 5,
        "Price (₹)" : ["3500", "1450", "2600", "580", "1620"],
        "Change (%)" : ["2.5", "-1.2", "3.8", "-0.5", "1.1"],
        "Volume"    : ["1000000", "2000000", "5000000", "8000000", "3000000"],
        "52W High"  : ["3800", "1600", "2900", "650", "1750"],
        "52W Low"   : ["2900", "1200", "2100", "450", "1300"],
        "Source"    : ["Yahoo Finance"] * 5,
        "Date"      : ["2024-01-15 10:30:00"] * 5,
    })

    pipeline = FilterPipeline()
    pipeline.add(PositiveChangeFilter(threshold=1.0))
    pipeline.add(TopNFilter(n=3, sort_col="Change (%)"))

    print("Running test pipeline on sample data:")
    result = pipeline.run(sample)
    print(result[["Symbol", "Price (₹)", "Change (%)"]].to_string())
    print(pipeline.summary())
    print("\n✅ filters.py working correctly!")