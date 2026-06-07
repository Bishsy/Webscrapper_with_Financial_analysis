# company_selector.py
# Interactive UI for selecting companies to scrape

import os
import sys
from typing import Dict, List, Tuple

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
if _THIS_DIR not in sys.path:
    sys.path.insert(0, _THIS_DIR)

from rich.console   import Console
from rich.panel     import Panel
from rich.table     import Table
from rich.prompt    import Confirm, Prompt, IntPrompt
from rich.progress  import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich           import box
from rich.text      import Text
from rich.columns   import Columns

from company_data import (
    NIFTY_50, NIFTY_MIDCAP, NIFTY_SMALLCAP, ALL_COMPANIES,
    get_all_sectors, get_companies_by_sector, symbol_to_info,
)

console = Console()


# ─────────────────────────────────────────────────────────────────────────────
# Display helpers
# ─────────────────────────────────────────────────────────────────────────────

def _print_company_table(companies: Dict, title: str, selected: List[str] = None):
    """Display companies in a formatted table."""
    selected = selected or []

    t = Table(
        title       = title,
        box         = box.ROUNDED,
        border_style= "bright_blue",
        header_style= "bold white on navy_blue",
        show_lines  = True,
    )
    t.add_column("#",       width=4,  justify="right",  style="bold yellow")
    t.add_column("Symbol",  width=14, style="bold cyan")
    t.add_column("Company Name",      style="white")
    t.add_column("Sector",  width=18, style="green")
    t.add_column("Index",   width=16, style="dim")
    t.add_column("✓",       width=3,  justify="center")

    for i, (sym, info) in enumerate(companies.items(), 1):
        chk = "[bold green]✓[/]" if sym in selected else ""
        t.add_row(
            str(i),
            sym,
            info["name"],
            info["sector"],
            info["index"],
            chk,
        )
    console.print(t)
    console.print(f"  Total: [bold]{len(companies)}[/bold] companies\n")


def _print_selection_summary(selected: Dict[str, dict]):
    """Show a summary of currently selected companies."""
    if not selected:
        console.print("  [dim]No companies selected yet.[/dim]\n")
        return

    console.print(Panel(
        f"[bold green]✓ {len(selected)} companies selected[/bold green]",
        border_style="green",
    ))

    # Group by index
    groups: Dict[str, List] = {}
    for sym, info in selected.items():
        idx = info.get("index", "Other")
        groups.setdefault(idx, []).append(f"{sym} ({info['sector']})")

    for idx, syms in groups.items():
        console.print(f"  [bold cyan]{idx}[/bold cyan] ({len(syms)}):")
        # Print in columns
        for i in range(0, len(syms), 4):
            row = syms[i:i+4]
            console.print("    " + "  │  ".join(
                f"[white]{s}[/white]" for s in row
            ))
    console.print()


# ─────────────────────────────────────────────────────────────────────────────
# Selection methods
# ─────────────────────────────────────────────────────────────────────────────

def _select_by_numbers(companies: Dict,
                        selected: Dict[str, dict]) -> Dict[str, dict]:
    """Select companies by entering their row numbers."""
    sym_list = list(companies.keys())
    console.print("\n  [yellow]Enter row numbers (e.g. 1,3,5-10,15 or 'all')[/yellow]")
    raw = Prompt.ask("  Selection").strip().lower()

    if raw == "all":
        selected.update(companies)
        console.print(f"  [green]✔ All {len(companies)} companies added.[/green]")
        return selected

    indices = set()
    for part in raw.split(","):
        part = part.strip()
        if "-" in part:
            try:
                lo, hi = part.split("-")
                indices.update(range(int(lo), int(hi) + 1))
            except ValueError:
                pass
        elif part.isdigit():
            indices.add(int(part))

    added = 0
    for idx in sorted(indices):
        if 1 <= idx <= len(sym_list):
            sym = sym_list[idx - 1]
            if sym not in selected:
                selected[sym] = companies[sym]
                added += 1

    console.print(f"  [green]✔ Added {added} companies.[/green]")
    return selected


def _select_by_sector(companies: Dict,
                       selected: Dict[str, dict]) -> Dict[str, dict]:
    """Select all companies in a sector."""
    # Get unique sectors in this company list
    sectors = sorted(set(v["sector"] for v in companies.values()))

    t = Table(box=box.SIMPLE, header_style="bold cyan")
    t.add_column("#",       width=4, style="bold yellow")
    t.add_column("Sector",  style="white")
    t.add_column("Count",   width=8, justify="right")

    for i, sec in enumerate(sectors, 1):
        cnt = sum(1 for v in companies.values() if v["sector"] == sec)
        t.add_row(str(i), sec, str(cnt))
    console.print(t)

    raw = Prompt.ask("  Enter sector numbers (comma-separated)", default="")
    chosen_sectors = set()
    for part in raw.split(","):
        part = part.strip()
        if part.isdigit():
            idx = int(part) - 1
            if 0 <= idx < len(sectors):
                chosen_sectors.add(sectors[idx])
        elif part in sectors:
            chosen_sectors.add(part)

    added = 0
    for sym, info in companies.items():
        if info["sector"] in chosen_sectors and sym not in selected:
            selected[sym] = info
            added += 1

    console.print(f"  [green]✔ Added {added} companies from {chosen_sectors}.[/green]")
    return selected


def _search_and_select(all_cos: Dict,
                        selected: Dict[str, dict]) -> Dict[str, dict]:
    """Search companies by name or symbol."""
    query = Prompt.ask("  Search (symbol or company name)").strip().lower()
    if not query:
        return selected

    matches = {
        sym: info for sym, info in all_cos.items()
        if query in sym.lower() or query in info["name"].lower()
    }

    if not matches:
        console.print(f"  [red]No matches for '{query}'[/red]")
        return selected

    _print_company_table(matches, f"Search Results for '{query}'", list(selected.keys()))
    return _select_by_numbers(matches, selected)


# ─────────────────────────────────────────────────────────────────────────────
# Main Company Selector UI
# ─────────────────────────────────────────────────────────────────────────────

class CompanySelector:
    """
    Interactive UI to let users choose which companies to scrape.
    Supports:
      - Nifty 50 selection
      - Midcap selection
      - Smallcap selection
      - Sector-based selection
      - Manual symbol entry
      - Search
      - Preset groups
    """

    def __init__(self):
        self.selected: Dict[str, dict] = {}

    def run(self) -> Dict[str, dict]:
        """Launch the company selection UI. Returns {symbol: info} dict."""

        console.print(Panel(
            Text.assemble(
                ("  🏢  Company Selection Studio\n\n", "bold white"),
                ("  Choose companies from Nifty 50, Midcap, Smallcap\n", "cyan"),
                ("  or search by name / sector",                          "dim"),
            ),
            border_style="bright_blue",
            padding=(1, 4),
        ))

        while True:
            self._show_menu()
            choice = Prompt.ask("  Choice", default="Q").strip().upper()

            if choice == "1":
                self._select_from_index("NIFTY 50", NIFTY_50)
            elif choice == "2":
                self._select_from_index("NIFTY MIDCAP", NIFTY_MIDCAP)
            elif choice == "3":
                self._select_from_index("NIFTY SMALLCAP", NIFTY_SMALLCAP)
            elif choice == "4":
                self._select_all_from_index()
            elif choice == "5":
                self._select_by_sector_ui()
            elif choice == "6":
                self.selected = _search_and_select(ALL_COMPANIES, self.selected)
            elif choice == "7":
                self._manual_entry()
            elif choice == "8":
                self._load_preset()
            elif choice == "9":
                self._remove_companies()
            elif choice == "C":
                if Confirm.ask("  Clear all selections?", default=False):
                    self.selected.clear()
                    console.print("  [yellow]Selection cleared.[/yellow]")
            elif choice == "V":
                _print_selection_summary(self.selected)
            elif choice == "D":
                self._show_selection_detail()
            elif choice == "Q":
                if not self.selected:
                    if Confirm.ask(
                        "  No companies selected. Use default Nifty 50?",
                        default=True
                    ):
                        self.selected = dict(NIFTY_50)
                break
            else:
                console.print(f"  [red]Unknown choice '{choice}'[/red]")

        console.print(
            f"\n  [bold green]✅ {len(self.selected)} companies selected "
            f"for scraping.[/bold green]\n"
        )
        return self.selected

    def _show_menu(self):
        status = (
            f"[bold green]{len(self.selected)} selected[/bold green]"
            if self.selected else "[dim]0 selected[/dim]"
        )
        console.print(Panel(
            f"[bold cyan]Company Selection[/bold cyan]  │  {status}",
            border_style="blue", padding=(0, 2),
        ))

        items = [
            ("1", "Browse & Select from NIFTY 50     (50 companies)"),
            ("2", "Browse & Select from NIFTY MIDCAP (47 companies)"),
            ("3", "Browse & Select from NIFTY SMALLCAP (50 companies)"),
            ("4", "Add ENTIRE index at once"),
            ("5", "Select by Sector"),
            ("6", "Search by name / symbol"),
            ("7", "Enter symbols manually"),
            ("8", "Load preset group"),
            ("9", "Remove companies from selection"),
            ("V", "View current selection"),
            ("D", "Detailed selection view"),
            ("C", "Clear all"),
            ("Q", "Done – proceed with selection"),
        ]
        for key, label in items:
            colour = "bold yellow" if key not in ("Q",) else "bold green"
            console.print(f"  [{colour}]{key}[/]  {label}")
        console.print()

    def _select_from_index(self, index_name: str, companies: Dict):
        """Browse and select companies from a specific index."""
        console.print(f"\n[bold]── {index_name} Companies ──[/bold]")
        _print_company_table(companies, index_name, list(self.selected.keys()))

        console.print("  [bold yellow]Options:[/bold yellow]")
        console.print("  [1] Select by row numbers")
        console.print("  [2] Select by sector")
        console.print("  [3] Select ALL")
        console.print("  [B] Back")

        sub = Prompt.ask("  Sub-choice", default="B").strip().upper()
        if sub == "1":
            self.selected = _select_by_numbers(companies, self.selected)
        elif sub == "2":
            self.selected = _select_by_sector(companies, self.selected)
        elif sub == "3":
            before = len(self.selected)
            self.selected.update(companies)
            added = len(self.selected) - before
            console.print(f"  [green]✔ Added {added} companies.[/green]")

    def _select_all_from_index(self):
        """Add all companies from a chosen index."""
        console.print("\n  Which index to add entirely?")
        console.print("  [1] NIFTY 50     (50 companies)")
        console.print("  [2] NIFTY MIDCAP (47 companies)")
        console.print("  [3] NIFTY SMALLCAP (50 companies)")
        console.print("  [4] ALL indices  (147 companies)")

        ch = Prompt.ask("  Choice", choices=["1","2","3","4"], default="1")
        mapping = {
            "1": ("NIFTY 50",    NIFTY_50),
            "2": ("MIDCAP",      NIFTY_MIDCAP),
            "3": ("SMALLCAP",    NIFTY_SMALLCAP),
            "4": ("ALL",         ALL_COMPANIES),
        }
        name, cos = mapping[ch]
        before = len(self.selected)
        self.selected.update(cos)
        added = len(self.selected) - before
        console.print(f"  [green]✔ Added {added} companies from {name}.[/green]")

    def _select_by_sector_ui(self):
        """Select companies by sector across all indices."""
        console.print("\n[bold]── Select by Sector (All Indices) ──[/bold]")
        sectors = get_all_sectors()

        t = Table(box=box.SIMPLE, header_style="bold cyan", show_lines=False)
        t.add_column("#",      width=4, style="bold yellow")
        t.add_column("Sector", style="white")
        t.add_column("Companies", justify="right", style="green")

        for i, sec in enumerate(sectors, 1):
            cnt = sum(1 for v in ALL_COMPANIES.values() if v["sector"] == sec)
            t.add_row(str(i), sec, str(cnt))
        console.print(t)

        raw = Prompt.ask("  Enter sector numbers (e.g. 1,3,5)", default="")
        chosen = set()
        for part in raw.split(","):
            part = part.strip()
            if part.isdigit():
                idx = int(part) - 1
                if 0 <= idx < len(sectors):
                    chosen.add(sectors[idx])

        added = 0
        for sym, info in ALL_COMPANIES.items():
            if info["sector"] in chosen and sym not in self.selected:
                self.selected[sym] = info
                added += 1

        if chosen:
            console.print(
                f"  [green]✔ Added {added} companies "
                f"from sectors: {', '.join(chosen)}[/green]"
            )

    def _manual_entry(self):
        """Allow typing symbols directly."""
        console.print(
            "\n  [yellow]Enter NSE symbols comma-separated "
            "(e.g. RELIANCE,TCS,INFY)[/yellow]"
        )
        raw = Prompt.ask("  Symbols").strip().upper()
        if not raw:
            return

        symbols = [s.strip() for s in raw.split(",") if s.strip()]
        added = 0
        not_found = []

        for sym in symbols:
            if sym in ALL_COMPANIES:
                if sym not in self.selected:
                    self.selected[sym] = ALL_COMPANIES[sym]
                    added += 1
            else:
                # Add as custom even if not in our list
                self.selected[sym] = {
                    "name"  : sym,
                    "sector": "Unknown",
                    "index" : "Custom",
                }
                added += 1

        console.print(f"  [green]✔ Added {added} symbols.[/green]")
        if not_found:
            console.print(
                f"  [yellow]Not in database (added as custom): "
                f"{not_found}[/yellow]"
            )

    def _load_preset(self):
        """Load predefined groups of companies."""
        presets = {
            "1": ("Top IT Companies",   ["TCS","INFY","WIPRO","HCLTECH","TECHM","MPHASIS","COFORGE","PERSISTENT"]),
            "2": ("Top Banks",          ["HDFCBANK","ICICIBANK","AXISBANK","SBIN","KOTAKBANK","INDUSINDBK","FEDERALBNK","BANDHANBNK"]),
            "3": ("Top FMCG",          ["HINDUNILVR","ITC","NESTLEIND","BRITANNIA","TATACONSUM","EMAMILTD","JYOTHYLAB","BIKAJI"]),
            "4": ("Top Pharma",        ["SUNPHARMA","DRREDDY","CIPLA","DIVISLAB","LUPIN","TORNTPHARM","BIOCON","AJANTPHARM"]),
            "5": ("Top Auto",          ["MARUTI","TATAMOTORS","M&M","BAJAJ-AUTO","HEROMOTOCO","EICHERMOT","BALKRISIND","MOTHERSON"]),
            "6": ("Top Energy",        ["RELIANCE","ONGC","BPCL","COALINDIA","NTPC","POWERGRID","SJVN"]),
            "7": ("All Finance",       ["HDFCBANK","ICICIBANK","BAJFINANCE","BAJAJFINSV","SBICARD","LICHSGFIN","IIFL","ANGELONE"]),
            "8": ("Nifty 50 IT Pack",  ["TCS","INFY","WIPRO","HCLTECH","TECHM"]),
            "9": ("Midcap IT Leaders", ["MPHASIS","COFORGE","PERSISTENT","KPITTECH","OFSS"]),
        }

        console.print("\n[bold]── Preset Company Groups ──[/bold]")
        t = Table(box=box.SIMPLE, header_style="bold cyan")
        t.add_column("#",      width=4, style="bold yellow")
        t.add_column("Group",  style="white")
        t.add_column("Count",  width=8, justify="right", style="green")
        for k, (name, syms) in presets.items():
            t.add_row(k, name, str(len(syms)))
        console.print(t)

        ch = Prompt.ask("  Preset number", default="")
        if ch in presets:
            name, symbols = presets[ch]
            added = 0
            for sym in symbols:
                if sym not in self.selected:
                    info = ALL_COMPANIES.get(sym, {
                        "name": sym, "sector": "Unknown", "index": "Custom"
                    })
                    self.selected[sym] = info
                    added += 1
            console.print(f"  [green]✔ Added {added} companies from '{name}'.[/green]")

    def _remove_companies(self):
        """Remove specific companies from selection."""
        if not self.selected:
            console.print("  [dim]Nothing selected to remove.[/dim]")
            return

        _print_company_table(
            self.selected, "Current Selection", list(self.selected.keys())
        )
        console.print("  Enter row numbers to remove (or 'all')")
        raw = Prompt.ask("  Remove").strip().lower()

        sym_list = list(self.selected.keys())
        if raw == "all":
            self.selected.clear()
            console.print("  [yellow]All selections cleared.[/yellow]")
            return

        to_remove = set()
        for part in raw.split(","):
            part = part.strip()
            if "-" in part:
                try:
                    lo, hi = part.split("-")
                    for i in range(int(lo), int(hi) + 1):
                        if 1 <= i <= len(sym_list):
                            to_remove.add(sym_list[i - 1])
                except ValueError:
                    pass
            elif part.isdigit():
                idx = int(part) - 1
                if 0 <= idx < len(sym_list):
                    to_remove.add(sym_list[idx])

        for sym in to_remove:
            self.selected.pop(sym, None)

        console.print(f"  [yellow]Removed {len(to_remove)} companies.[/yellow]")

    def _show_selection_detail(self):
        """Show detailed breakdown of selection."""
        if not self.selected:
            console.print("  [dim]Nothing selected.[/dim]")
            return
        _print_company_table(
            self.selected,
            f"Selected Companies ({len(self.selected)})",
            list(self.selected.keys()),
        )