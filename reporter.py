"""
reporter.py
-----------
Responsive Rich terminal report. Adapts to terminal width automatically.
"""

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.columns import Columns
from rich.text import Text
from rich.padding import Padding
from rich import box
from extractor import UIProperties

console = Console()  # No fixed width — uses actual terminal size


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _rgb_to_hex(rgb_str: str) -> str | None:
    try:
        nums = [int(float(x.strip()))
                for x in rgb_str.replace("rgba","").replace("rgb","")
                                .strip("()").split(",")]
        return "#{:02x}{:02x}{:02x}".format(nums[0], nums[1], nums[2])
    except Exception:
        return None


def _swatches(colors: list[str], limit: int = 10) -> Text:
    t = Text()
    for c in colors[:limit]:
        hex_c = _rgb_to_hex(c) if c.startswith("rgb") else c
        if hex_c:
            try:
                t.append("█", style=hex_c)
            except Exception:
                pass
    return t


def _bar(score: int, width: int = 20) -> Text:
    """Render a score as a coloured progress bar."""
    filled = round((score / 100) * width)
    empty  = width - filled
    color  = "green" if score >= 70 else "yellow" if score >= 45 else "red"
    t = Text()
    t.append("█" * filled, style=color)
    t.append("░" * empty,  style="bright_black")
    t.append(f" {score}%",  style=color + " bold")
    return t


def _grade_style(grade: str) -> str:
    return {"A": "bold green", "B": "green", "C": "yellow",
            "D": "red", "F": "bold red"}.get(grade, "white")


# ---------------------------------------------------------------------------
# Sections
# ---------------------------------------------------------------------------

def _extraction_panel(props: UIProperties) -> Panel:
    t = Table(box=box.SIMPLE, show_header=False, expand=True, padding=(0, 1))
    t.add_column("Key",   style="dim",   ratio=1)
    t.add_column("Value", style="white", ratio=2)

    t.add_row("Dark mode",   "✓ Yes" if props.is_dark_mode else "No")
    t.add_row("Animations",  "✓ Yes" if props.has_animations else "No")
    t.add_row("Colors",      str(len(props.colors)))
    t.add_row("Palette",     _swatches(props.colors))
    t.add_row("Fonts",       ", ".join(props.fonts[:4]) or "—")
    t.add_row("Font sizes",  ", ".join(props.font_sizes[:6]) or "—")
    t.add_row("Elements",    str(props.total_elements))
    t.add_row("DOM depth",   str(props.max_dom_depth))
    t.add_row("Buttons",     str(props.buttons_count))
    t.add_row("Links",       str(props.links_count))
    t.add_row("Inputs",      str(props.inputs_count))
    t.add_row("Text density",f"{props.text_density:.1%}")

    return Panel(t, title="[bold cyan]Extracted Properties[/bold cyan]",
                 border_style="cyan", expand=True)


def _score_panel(result: dict) -> Panel:
    grade = result["grade"]
    overall = result["overall_score"]

    t = Table(box=box.SIMPLE, show_header=False, expand=True, padding=(0, 1))
    t.add_column("Category", style="dim",   ratio=1)
    t.add_column("Score",    style="white", ratio=3)

    labels = {
        "dark_mode":      "Color Scheme",
        "typography":     "Typography",
        "visual_density": "Visual Density",
        "animations":     "Motion",
        "interactivity":  "Interactivity",
    }
    for key, label in labels.items():
        s = result["breakdown"].get(key, 0)
        t.add_row(label, _bar(s))

    overall_text = Text()
    overall_text.append(f"\n  Overall  ", style="dim")
    overall_text.append(_bar(overall, width=24))
    overall_text.append(f"   Grade: ", style="dim")
    overall_text.append(grade, style=_grade_style(grade) + " bold")

    title = f"[bold]{result['persona_name']}[/bold]"
    return Panel(
        Text.assemble(t.__rich_console__(console, console.options).__next__()  # render table inline
                      if False else "") or t,
        title=title, border_style="magenta", expand=True,
        subtitle=overall_text
    )


def _recs_panel(result: dict) -> Panel | None:
    recs = result.get("recommendations", [])
    dbs  = result.get("dealbreakers_triggered", [])
    if not recs and not dbs:
        return None

    lines = Text()
    if dbs:
        lines.append("⚠  Dealbreakers triggered\n", style="bold red")
        for d in dbs:
            lines.append(f"  • {d}\n", style="red")
        if recs:
            lines.append("\n")

    if recs:
        lines.append("💡 Recommendations\n", style="bold yellow")
        for i, r in enumerate(recs, 1):
            lines.append(f"  {i}. {r}\n", style="yellow")

    return Panel(lines, title="[bold]Findings[/bold]",
                 border_style="yellow", expand=True)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def print_report(props: UIProperties, result: dict | None = None) -> None:
    """
    Print the full report.
    - props:  UIProperties from extractor.py
    - result: scoring dict from scorer.py (optional — omit for extraction-only view)
    """
    console.print()
    console.rule(f"[bold]UI-Audit[/bold]  [dim]{props.url}[/dim]")
    console.print(f"  [dim]Title:[/dim] {props.title or '—'}\n")

    if result:
        # Side-by-side on wide terminals, stacked on narrow ones
        width = console.width or 80
        if width >= 120:
            console.print(Columns([
                _extraction_panel(props),
                _score_panel(result),
            ], equal=True, expand=True))
        else:
            console.print(_extraction_panel(props))
            console.print()
            # Score table manually since Panel-in-Panel is tricky
            _print_score_table(result)
    else:
        console.print(_extraction_panel(props))

    recs = _recs_panel(result) if result else None
    if recs:
        console.print()
        console.print(recs)

    console.print()
    console.rule()


def _print_score_table(result: dict) -> None:
    """Fallback score display for narrow terminals."""
    grade = result["grade"]
    t = Table(
        title=f"[bold]{result['persona_name']}[/bold]",
        box=box.ROUNDED, expand=True, show_header=True,
    )
    t.add_column("Category",  style="dim",   min_width=16)
    t.add_column("Score Bar", min_width=24)
    t.add_column("%",         justify="right", min_width=5)

    labels = {
        "dark_mode":      "Color Scheme",
        "typography":     "Typography",
        "visual_density": "Visual Density",
        "animations":     "Motion",
        "interactivity":  "Interactivity",
    }
    for key, label in labels.items():
        s = result["breakdown"].get(key, 0)
        t.add_row(label, _bar(s), str(s))

    overall = result["overall_score"]
    t.add_section()
    t.add_row(
        "[bold]Overall[/bold]",
        _bar(overall),
        f"[{_grade_style(grade)} bold]{overall} ({grade})[/{_grade_style(grade)} bold]"
    )
    console.print(t)