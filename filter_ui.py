# filter_ui.py
"""
Rich terminal UI for building and applying filter pipelines interactively.
Supports:
  - Menu-driven filter selection
  - Filter preview before applying
  - Save / load filter presets
  - Filter history display
  - Coloured result tables
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta
from typing import Optional

import pandas as pd
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, FloatPrompt, IntPrompt, Prompt
from rich.table import Table
from rich.text import Text
from rich import print as rprint

from filters import (
    BottomNFilter,
    CategoryFilter,
    CustomExpressionFilter,
    DateRangeFilter,
    FilterPipeline,
    MultiColumnSortFilter,
    NegativeChangeFilter,
    PercentChangeFilter,
    PositiveChangeFilter,
    PriceRangeFilter,
    SectorFilter,
    SourceFilter,
    SymbolSearchFilter,
    TopNFilter,
    VolumeFilter,
    WeekHighProximityFilter,
    WeekLowProximityFilter,
    _numeric_col,
)
from config import ScraperConfig

console = Console()

PRESETS_FILE = "output/filter_presets.json"

# ─────────────────────────────────────────────────────────────────────────────
# Display helpers
# ─────────────────────────────────────────────────────────────────────────────

def print_header(title: str):
    console.print(Panel(
        Text(title, style="bold white", justify="center"),
        style="bold blue",
        border_style="bright_blue",
    ))


def print_dataframe(df: pd.DataFrame, title: str = "Results", max_rows: int = 30):
    """Render a DataFrame as a rich Table with colour-coded change column."""
    table = Table(
        title       = title,
        box         = box.ROUNDED,
        border_style= "bright_blue",
        header_style= "bold white on navy_blue",
        show_lines  = True,
    )

    # Define columns
    display_cols = [
        "Symbol", "Title", "Category", "Price (₹)",
        "Change (%)", "Volume", "52W High", "52W Low", "Source",
    ]
    display_cols = [c for c in display_cols if c in df.columns]

    for col in display_cols:
        table.add_column(col, justify="right" if col in ["Price (₹)", "Change (%)", "Volume"] else "left")

    shown = 0
    for _, row in df.iterrows():
        if shown >= max_rows:
            break
        cells = []
        for col in display_cols:
            val = str(row.get(col, "N/A"))

            # Colour-code change column
            if col == "Change (%)":
                try:
                    num = float(val.replace("%", ""))
                    if num > 0:
                        val = f"[bold green]+{num:.2f}%[/]"
                    elif num < 0:
                        val = f"[bold red]{num:.2f}%[/]"
                    else:
                        val = f"[yellow]{num:.2f}%[/]"
                except ValueError:
                    pass

            # Colour-code category
            elif col == "Category":
                colour_map = {
                    "Top Gainer" : "green",
                    "Top Loser"  : "red",
                    "Index"      : "cyan",
                    "Watchlist"  : "yellow",
                }
                clr = colour_map.get(val, "white")
                val = f"[{clr}]{val}[/]"

            cells.append(val)

        table.add_row(*cells)
        shown += 1

    console.print(table)

    if len(df) > max_rows:
        console.print(
            f"[dim]  … {len(df) - max_rows} more rows not shown. "
            f"Export to Excel to see all.[/dim]"
        )
    console.print(f"[bold]Total rows:[/bold] {len(df)}\n")


def print_statistics(df: pd.DataFrame):
    """Show quick statistics panel for numeric columns."""
    console.print(Panel("[bold cyan]Quick Statistics[/bold cyan]", border_style="cyan"))

    stat_table = Table(box=box.SIMPLE, header_style="bold cyan", show_lines=False)
    stat_table.add_column("Metric",     style="bold white")
    stat_table.add_column("Price (₹)",  justify="right")
    stat_table.add_column("Change (%)", justify="right")
    stat_table.add_column("Volume",     justify="right")

    prices  = _numeric_col(df, "Price (₹)").dropna()
    changes = _numeric_col(df, "Change (%)").dropna()
    volumes = _numeric_col(df, "Volume").dropna()

    def fmt(series, prefix="", suffix=""):
        if series.empty:
            return "N/A"
        return f"{prefix}{series:.2f}{suffix}" if False else series

    rows_data = [
        ("Count",  len(prices),          len(changes),           len(volumes)),
        ("Mean",   prices.mean()  if len(prices)  else "N/A",
                   changes.mean() if len(changes) else "N/A",
                   volumes.mean() if len(volumes) else "N/A"),
        ("Median", prices.median()  if len(prices)  else "N/A",
                   changes.median() if len(changes) else "N/A",
                   volumes.median() if len(volumes) else "N/A"),
        ("Min",    prices.min()  if len(prices)  else "N/A",
                   changes.min() if len(changes) else "N/A",
                   volumes.min() if len(volumes) else "N/A"),
        ("Max",    prices.max()  if len(prices)  else "N/A",
                   changes.max() if len(changes) else "N/A",
                   volumes.max() if len(volumes) else "N/A"),
        ("Std Dev",prices.std()  if len(prices)  else "N/A",
                   changes.std() if len(changes) else "N/A",
                   volumes.std() if len(volumes) else "N/A"),
    ]

    for label, p, c, v in rows_data:
        def safe_fmt(x, is_pct=False, is_vol=False):
            if isinstance(x, str):
                return x
            if is_pct:
                clr = "green" if x > 0 else ("red" if x < 0 else "yellow")
                return f"[{clr}]{x:+.2f}%[/]"
            if is_vol:
                if x >= 1e6:
                    return f"{x/1e6:.1f}M"
                if x >= 1e3:
                    return f"{x/1e3:.1f}K"
                return f"{x:.0f}"
            return f"₹{x:,.2f}"

        stat_table.add_row(
            label,
            safe_fmt(p),
            safe_fmt(c, is_pct=True),
            safe_fmt(v, is_vol=True),
        )

    console.print(stat_table)


# ─────────────────────────────────────────────────────────────────────────────
# Individual filter builders  (each returns a filter object or None)
# ─────────────────────────────────────────────────────────────────────────────

def build_price_filter() -> Optional[PriceRangeFilter]:
    console.print("\n[bold yellow]── Price Range Filter ──[/bold yellow]")
    console.print("  Leave blank to skip a bound.")
    min_s = Prompt.ask("  Minimum price (₹)", default="")
    max_s = Prompt.ask("  Maximum price (₹)", default="")
    min_p = float(min_s) if min_s.strip() else None
    max_p = float(max_s) if max_s.strip() else None
    if min_p is None and max_p is None:
        console.print("  [dim]No bounds entered — filter skipped.[/dim]")
        return None
    return PriceRangeFilter(min_price=min_p, max_price=max_p)


def build_pct_filter() -> Optional[PercentChangeFilter]:
    console.print("\n[bold yellow]── Percentage Change Filter ──[/bold yellow]")
    console.print("  Example: min=-5  max=5  keeps stocks between -5% and +5%")
    min_s = Prompt.ask("  Minimum % change", default="")
    max_s = Prompt.ask("  Maximum % change", default="")
    min_p = float(min_s) if min_s.strip() else None
    max_p = float(max_s) if max_s.strip() else None
    if min_p is None and max_p is None:
        return None
    return PercentChangeFilter(min_pct=min_p, max_pct=max_p)


def build_volume_filter() -> Optional[VolumeFilter]:
    console.print("\n[bold yellow]── Volume Filter ──[/bold yellow]")
    console.print("  Enter volume in raw numbers (e.g. 1000000 for 1M)")
    min_s = Prompt.ask("  Minimum volume", default="")
    max_s = Prompt.ask("  Maximum volume", default="")
    min_v = float(min_s) if min_s.strip() else None
    max_v = float(max_s) if max_s.strip() else None
    if min_v is None and max_v is None:
        return None
    return VolumeFilter(min_volume=min_v, max_volume=max_v)


def build_category_filter() -> Optional[CategoryFilter]:
    console.print("\n[bold yellow]── Category Filter ──[/bold yellow]")
    console.print("  Available: [cyan]Index[/cyan] | [green]Top Gainer[/green] | "
                  "[red]Top Loser[/red] | [yellow]Watchlist[/yellow]")
    console.print("  Enter comma-separated choices (e.g. Index,Watchlist)")
    raw = Prompt.ask("  Categories", default="")
    cats = [c.strip() for c in raw.split(",") if c.strip()]
    if not cats:
        return None
    valid = CategoryFilter.VALID
    chosen = [c for c in cats if c in valid]
    invalid = [c for c in cats if c not in valid]
    if invalid:
        console.print(f"  [red]Ignored invalid categories: {invalid}[/red]")
    return CategoryFilter(categories=chosen) if chosen else None


def build_source_filter() -> Optional[SourceFilter]:
    console.print("\n[bold yellow]── Source Filter ──[/bold yellow]")
    for i, src in enumerate(SourceFilter.VALID, 1):
        console.print(f"  [{i}] {src}")
    raw = Prompt.ask("  Enter source names or numbers (comma-separated)", default="")
    parts = [p.strip() for p in raw.split(",") if p.strip()]
    chosen = []
    for p in parts:
        if p.isdigit():
            idx = int(p) - 1
            if 0 <= idx < len(SourceFilter.VALID):
                chosen.append(SourceFilter.VALID[idx])
        elif p in SourceFilter.VALID:
            chosen.append(p)
    return SourceFilter(sources=chosen) if chosen else None


def build_symbol_search() -> Optional[SymbolSearchFilter]:
    console.print("\n[bold yellow]── Symbol / Name Search Filter ──[/bold yellow]")
    query = Prompt.ask("  Search query", default="")
    if not query.strip():
        return None
    case_s  = Confirm.ask("  Case-sensitive?",   default=False)
    use_re  = Confirm.ask("  Use regex pattern?", default=False)
    return SymbolSearchFilter(query=query.strip(), case_sensitive=case_s, use_regex=use_re)


def build_sector_filter(config: ScraperConfig) -> Optional[SectorFilter]:
    console.print("\n[bold yellow]── Sector Filter ──[/bold yellow]")
    sectors = SectorFilter.VALID_SECTORS
    for i, sec in enumerate(sectors, 1):
        console.print(f"  [{i:>2}] {sec}")
    raw = Prompt.ask("  Enter sector names or numbers (comma-separated)", default="")
    parts = [p.strip() for p in raw.split(",") if p.strip()]
    chosen = []
    for p in parts:
        if p.isdigit():
            idx = int(p) - 1
            if 0 <= idx < len(sectors):
                chosen.append(sectors[idx])
        elif p in sectors:
            chosen.append(p)
    if not chosen:
        return None
    return SectorFilter(sectors=chosen, sector_map=config.SECTOR_MAP)


def build_date_filter() -> Optional[DateRangeFilter]:
    console.print("\n[bold yellow]── Date Range Filter ──[/bold yellow]")
    console.print("  Presets: [1] Today  [2] Last 7 days  [3] Last 30 days  [4] Custom")
    choice = Prompt.ask("  Choice", choices=["1","2","3","4",""], default="")
    now = datetime.now()
    if choice == "1":
        return DateRangeFilter(start_date=now.replace(hour=0,minute=0,second=0), end_date=now)
    elif choice == "2":
        return DateRangeFilter(start_date=now - timedelta(days=7), end_date=now)
    elif choice == "3":
        return DateRangeFilter(start_date=now - timedelta(days=30), end_date=now)
    elif choice == "4":
        start_s = Prompt.ask("  Start date (YYYY-MM-DD)", default="")
        end_s   = Prompt.ask("  End date   (YYYY-MM-DD)", default="")
        start = datetime.strptime(start_s, "%Y-%m-%d") if start_s else None
        end   = datetime.strptime(end_s,   "%Y-%m-%d") if end_s   else None
        return DateRangeFilter(start_date=start, end_date=end)
    return None


def build_topn_filter() -> Optional[TopNFilter]:
    console.print("\n[bold yellow]── Top N Filter ──[/bold yellow]")
    sortable = ["Price (₹)", "Change (%)", "Volume", "52W High"]
    for i, col in enumerate(sortable, 1):
        console.print(f"  [{i}] {col}")
    col_choice = Prompt.ask("  Sort column number", default="1")
    col_idx    = int(col_choice) - 1
    col        = sortable[col_idx] if 0 <= col_idx < len(sortable) else "Price (₹)"
    n          = IntPrompt.ask("  How many top rows?", default=10)
    return TopNFilter(n=n, sort_col=col)


def build_bottomn_filter() -> Optional[BottomNFilter]:
    console.print("\n[bold yellow]── Bottom N Filter ──[/bold yellow]")
    sortable = ["Price (₹)", "Change (%)", "Volume", "52W Low"]
    for i, col in enumerate(sortable, 1):
        console.print(f"  [{i}] {col}")
    col_choice = Prompt.ask("  Sort column number", default="1")
    col_idx    = int(col_choice) - 1
    col        = sortable[col_idx] if 0 <= col_idx < len(sortable) else "Price (₹)"
    n          = IntPrompt.ask("  How many bottom rows?", default=10)
    return BottomNFilter(n=n, sort_col=col)


def build_positive_filter() -> PositiveChangeFilter:
    console.print("\n[bold yellow]── Positive Change Filter ──[/bold yellow]")
    threshold = FloatPrompt.ask("  Minimum % gain (default 0)", default=0.0)
    return PositiveChangeFilter(threshold=threshold)


def build_negative_filter() -> NegativeChangeFilter:
    console.print("\n[bold yellow]── Negative Change Filter ──[/bold yellow]")
    threshold = FloatPrompt.ask("  Maximum % loss (default 0)", default=0.0)
    return NegativeChangeFilter(threshold=-abs(threshold))


def build_52w_high_filter() -> WeekHighProximityFilter:
    console.print("\n[bold yellow]── Near 52-Week High Filter ──[/bold yellow]")
    within = FloatPrompt.ask("  Within how many % of 52W High?", default=5.0)
    return WeekHighProximityFilter(within_pct=within)


def build_52w_low_filter() -> WeekLowProximityFilter:
    console.print("\n[bold yellow]── Near 52-Week Low Filter ──[/bold yellow]")
    within = FloatPrompt.ask("  Within how many % of 52W Low?", default=5.0)
    return WeekLowProximityFilter(within_pct=within)


def build_custom_expression() -> Optional[CustomExpressionFilter]:
    console.print("\n[bold yellow]── Custom Expression Filter ──[/bold yellow]")
    console.print("  Available columns: Price, Change, ChangePct, Volume")
    console.print("  Examples:")
    console.print("    [dim]Price > 500 and ChangePct > 2[/dim]")
    console.print("    [dim]Volume > 1000000 or ChangePct < -3[/dim]")
    console.print("    [dim]Price >= 200 and Price <= 1000[/dim]")
    expr = Prompt.ask("  Expression", default="")
    if not expr.strip():
        return None
    return CustomExpressionFilter(expression=expr.strip())


def build_sort_filter() -> Optional[MultiColumnSortFilter]:
    console.print("\n[bold yellow]── Multi-Column Sort ──[/bold yellow]")
    sortable = ["Price (₹)", "Change (%)", "Volume", "52W High", "52W Low", "Symbol", "Title"]
    for i, col in enumerate(sortable, 1):
        console.print(f"  [{i}] {col}")
    console.print("  Enter column numbers and direction, e.g.:  1 desc, 2 asc")
    raw = Prompt.ask("  Sort spec", default="1 desc")
    spec = []
    for part in raw.split(","):
        tokens = part.strip().split()
        if not tokens:
            continue
        col_token = tokens[0].strip()
        direction = tokens[1].lower() if len(tokens) > 1 else "desc"
        if col_token.isdigit():
            idx = int(col_token) - 1
            col = sortable[idx] if 0 <= idx < len(sortable) else sortable[0]
        else:
            col = col_token
        spec.append((col, direction == "asc"))
    if not spec:
        return None
    return MultiColumnSortFilter(sort_spec=spec)


# ─────────────────────────────────────────────────────────────────────────────
# Preset manager
# ─────────────────────────────────────────────────────────────────────────────

class PresetManager:
    """Save and load filter configurations as JSON presets."""

    PRESET_FILE = PRESETS_FILE

    def __init__(self):
        os.makedirs(os.path.dirname(self.PRESET_FILE), exist_ok=True)
        self._presets: dict = self._load_all()

    def _load_all(self) -> dict:
        if os.path.exists(self.PRESET_FILE):
            try:
                with open(self.PRESET_FILE, "r") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def _save_all(self):
        with open(self.PRESET_FILE, "w") as f:
            json.dump(self._presets, f, indent=2)

    def save(self, name: str, pipeline_config: list[dict]):
        self._presets[name] = {
            "saved_at": datetime.now().isoformat(),
            "filters" : pipeline_config,
        }
        self._save_all()
        console.print(f"  [green]✔ Preset '{name}' saved.[/green]")

    def load(self, name: str) -> Optional[list[dict]]:
        preset = self._presets.get(name)
        if not preset:
            console.print(f"  [red]Preset '{name}' not found.[/red]")
            return None
        return preset["filters"]

    def list_presets(self):
        if not self._presets:
            console.print("  [dim]No saved presets.[/dim]")
            return
        t = Table(box=box.SIMPLE, header_style="bold cyan")
        t.add_column("Name")
        t.add_column("Saved At")
        t.add_column("Filters")
        for name, data in self._presets.items():
            n_filters = len(data.get("filters", []))
            t.add_row(name, data.get("saved_at","")[:19], str(n_filters))
        console.print(t)

    def delete(self, name: str):
        if name in self._presets:
            del self._presets[name]
            self._save_all()
            console.print(f"  [yellow]Preset '{name}' deleted.[/yellow]")


# ─────────────────────────────────────────────────────────────────────────────
# Main interactive filter UI
# ─────────────────────────────────────────────────────────────────────────────

FILTER_MENU = [
    ("1",  "Price Range",             build_price_filter),
    ("2",  "Percentage Change",       build_pct_filter),
    ("3",  "Volume",                  build_volume_filter),
    ("4",  "Category",                build_category_filter),
    ("5",  "Source",                  build_source_filter),
    ("6",  "Symbol / Name Search",    build_symbol_search),
    ("7",  "Sector",                  None),    # needs config
    ("8",  "Date Range",              build_date_filter),
    ("9",  "Top N",                   build_topn_filter),
    ("10", "Bottom N",                build_bottomn_filter),
    ("11", "Positive Change Only",    build_positive_filter),
    ("12", "Negative Change Only",    build_negative_filter),
    ("13", "Near 52-Week High",       build_52w_high_filter),
    ("14", "Near 52-Week Low",        build_52w_low_filter),
    ("15", "Custom Expression",       build_custom_expression),
    ("16", "Multi-Column Sort",       build_sort_filter),
]


class FilterUI:
    """
    Full interactive terminal UI for building, applying,
    previewing, and saving filter pipelines.
    """

    def __init__(self, config: ScraperConfig):
        self.config   = config
        self.pipeline = FilterPipeline()
        self.presets  = PresetManager()

    def _show_main_menu(self):
        console.print(Panel(
            "[bold]Filter Menu[/bold]\n"
            "[dim]Build a filter pipeline step by step[/dim]",
            border_style="bright_blue",
        ))

        t = Table(box=box.SIMPLE_HEAD, header_style="bold cyan", show_lines=False)
        t.add_column("#",    width=4,  style="bold yellow")
        t.add_column("Filter Type",    style="white")
        t.add_column("#",    width=4,  style="bold yellow")
        t.add_column("Filter Type",    style="white")

        rows = FILTER_MENU.copy()
        # Pad to even
        if len(rows) % 2:
            rows.append(("", "", None))

        for i in range(0, len(rows), 2):
            a = rows[i]
            b = rows[i+1]
            t.add_row(a[0], a[1], b[0], b[1])

        console.print(t)
        console.print("[bold cyan]Actions:[/bold cyan]")
        console.print("  [bold yellow]A[/bold yellow] – Apply pipeline to data")
        console.print("  [bold yellow]P[/bold yellow] – Preview active pipeline")
        console.print("  [bold yellow]C[/bold yellow] – Clear all filters")
        console.print("  [bold yellow]S[/bold yellow] – Save preset")
        console.print("  [bold yellow]L[/bold yellow] – Load preset")
        console.print("  [bold yellow]D[/bold yellow] – Show statistics")
        console.print("  [bold yellow]E[/bold yellow] – Export filtered data to Excel")
        console.print("  [bold yellow]Q[/bold yellow] – Quit filter menu\n")

    def _show_pipeline_preview(self):
        if self.pipeline.is_empty:
            console.print("[dim]  Pipeline is empty — no filters added yet.[/dim]")
            return
        console.print(Panel("[bold cyan]Active Filter Pipeline[/bold cyan]", border_style="cyan"))
        for i, f in enumerate(self.pipeline._filters, 1):
            console.print(f"  [{i}] {f.describe()}")

    def _build_filter(self, key: str) -> Optional[object]:
        """Dispatch to the correct builder function."""
        for num, label, builder in FILTER_MENU:
            if num == key:
                if num == "7":
                    return build_sector_filter(self.config)
                elif num == "4":
                    return build_category_filter()
                elif num == "5":
                    return build_source_filter()
                elif builder:
                    return builder()
        return None

    def _serialize_pipeline(self) -> list[dict]:
        """Convert active pipeline to JSON-serialisable list."""
        result = []
        for f in self.pipeline._filters:
            result.append({
                "type" : type(f).__name__,
                "desc" : f.describe(),
            })
        return result

    def run(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Launch the interactive filter UI.
        Returns the filtered DataFrame after the user exits.
        """
        filtered_df = df.copy()

        print_header("🔍  Indian Stock Filter Studio")
        console.print(f"  [dim]Dataset loaded: {len(df)} rows, {len(df.columns)} columns[/dim]\n")

        while True:
            self._show_main_menu()
            choice = Prompt.ask(
                "  Enter filter number or action",
                default="Q"
            ).strip().upper()

            # ── Actions ───────────────────────────────────────────────────────
            if choice == "Q":
                if Confirm.ask("  Exit filter menu?", default=True):
                    break

            elif choice == "A":
                console.print("\n[bold green]Applying pipeline…[/bold green]")
                if self.pipeline.is_empty:
                    console.print("  [yellow]No filters added — showing all data.[/yellow]")
                    filtered_df = df.copy()
                else:
                    filtered_df = self.pipeline.run(df)
                print_dataframe(filtered_df, title=f"Filtered Results ({len(filtered_df)} rows)")
                console.print(self.pipeline.summary())

            elif choice == "P":
                self._show_pipeline_preview()

            elif choice == "C":
                if Confirm.ask("  Clear all filters?", default=False):
                    self.pipeline.clear()
                    filtered_df = df.copy()
                    console.print("  [yellow]Pipeline cleared.[/yellow]")

            elif choice == "S":
                name = Prompt.ask("  Preset name")
                self.presets.save(name, self._serialize_pipeline())

            elif choice == "L":
                self.presets.list_presets()
                name = Prompt.ask("  Enter preset name to load")
                data = self.presets.load(name)
                if data:
                    console.print(f"  [cyan]Loaded preset with {len(data)} filter definitions.[/cyan]")
                    console.print("  [dim]Note: Re-create filters manually or use saved JSON.[/dim]")

            elif choice == "D":
                print_statistics(filtered_df if not self.pipeline.is_empty else df)

            elif choice == "E":
                export_path = Prompt.ask(
                    "  Export path",
                    default="output/filtered_results.xlsx"
                )
                self._export(filtered_df, export_path)

            # ── Filter builders ───────────────────────────────────────────────
            elif choice in [num for num, *_ in FILTER_MENU]:
                f_obj = self._build_filter(choice)
                if f_obj:
                    self.pipeline.add(f_obj)
                    console.print(
                        f"  [green]✔ Added:[/green] {f_obj.describe()}"
                        f"  [dim](Pipeline size: {len(self.pipeline)})[/dim]"
                    )
                    # Live preview after adding
                    if Confirm.ask("  Preview now?", default=True):
                        preview = self.pipeline.run(df)
                        print_dataframe(preview, title="Live Preview", max_rows=15)
                else:
                    console.print("  [dim]Filter skipped (no input).[/dim]")

            else:
                console.print(f"  [red]Unknown choice: '{choice}'[/red]")

        return filtered_df

    @staticmethod
    def _export(df: pd.DataFrame, path: str):
        """Quick export of a filtered DataFrame to Excel."""
        try:
            os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
            with pd.ExcelWriter(path, engine="openpyxl") as writer:
                df.to_excel(writer, index=False, sheet_name="Filtered Data")
            console.print(f"  [green]✔ Exported {len(df)} rows → {path}[/green]")
        except Exception as exc:
            console.print(f"  [red]Export failed: {exc}[/red]")