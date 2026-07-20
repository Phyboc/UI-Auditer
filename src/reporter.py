from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box
from extractor import UIProperties
 
console = Console()
 
 
# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
 
def _rgb_to_hex(rgb_str: str) -> str | None:
    try:
        nums = [int(float(x.strip()))
                for x in rgb_str.replace("rgba","").replace("rgb","").strip("()").split(",")]
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
    filled = round((score / 100) * width)
    empty  = width - filled
    color  = "green" if score >= 70 else "yellow" if score >= 45 else "red"
    t = Text()
    t.append("█" * filled, style=color)
    t.append("░" * empty,  style="bright_black")
    t.append(f" {score}%", style=color + " bold")
    return t
 
 
def _grade_style(grade: str) -> str:
    return {"A": "bold green", "B": "green", "C": "yellow",
            "D": "red", "F": "bold red"}.get(grade, "white")
 
 
# ---------------------------------------------------------------------------
# Sections
# ---------------------------------------------------------------------------
 
def _print_extraction_table(props: UIProperties) -> None:
    t = Table(box=box.SIMPLE, show_header=False, expand=True, padding=(0, 1))
    t.add_column("Key",   style="dim",   ratio=1)
    t.add_column("Value", style="white", ratio=3)
 
    t.add_row("Dark mode",    "✓ Yes" if props.is_dark_mode else "No")
    t.add_row("Animations",   "✓ Yes" if props.has_animations else "No")
    t.add_row("Colors",       str(len(props.colors)))
    t.add_row("Palette",      _swatches(props.colors))
    t.add_row("Fonts",        ", ".join(props.fonts[:4]) or "—")
    t.add_row("Font sizes",   ", ".join(props.font_sizes[:6]) or "—")
    t.add_row("Elements",     str(props.total_elements))
    t.add_row("DOM depth",    str(props.max_dom_depth))
    t.add_row("Buttons",      str(props.buttons_count))
    t.add_row("Links",        str(props.links_count))
    t.add_row("Inputs",       str(props.inputs_count))
    t.add_row("Text density", f"{props.text_density:.1%}")
 
    console.print(Panel(t, title="[bold cyan]Extracted Properties[/bold cyan]",
                        border_style="cyan", expand=True))
 
 
def _print_score_table(result: dict) -> None:
    grade   = result["grade"]
    overall = result["overall_score"]
 
    labels = {
        "dark_mode":      "Color Scheme",
        "typography":     "Typography",
        "visual_density": "Visual Density",
        "animations":     "Motion",
        "interactivity":  "Interactivity",
    }
 
    t = Table(
        title=f"[bold]{result['persona_name']}[/bold]",
        box=box.ROUNDED, expand=True, show_header=True,
    )
    t.add_column("Category",  style="dim", min_width=16)
    t.add_column("Score Bar", min_width=26)
    t.add_column("%", justify="right", min_width=5)
 
    for key, label in labels.items():
        s = result["breakdown"].get(key, 0)
        t.add_row(label, _bar(s), str(s))
 
    t.add_section()
    t.add_row(
        "[bold]Overall[/bold]",
        _bar(overall),
        f"[{_grade_style(grade)} bold]{overall} ({grade})[/{_grade_style(grade)} bold]"
    )
    console.print(t)
 
 
def _print_findings(result: dict) -> None:
    recs = result.get("recommendations", [])
    dbs  = result.get("dealbreakers_triggered", [])
    if not recs and not dbs:
        return
 
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
 
    console.print(Panel(lines, title="[bold]Findings[/bold]",
                        border_style="yellow", expand=True))
 
 
def _print_llm_suggestions(suggestions: dict) -> None:
    provider = suggestions.get("provider", "LLM")
    summary  = suggestions.get("summary", "")
    css_fixes = suggestions.get("css_fixes", [])
    non_css   = suggestions.get("non_css_suggestions", [])
 
    # Summary panel
    console.print(Panel(
        Text(summary, style="white"),
        title=f"[bold green]🔧 AI Fix Suggestions[/bold green] [dim]via {provider}[/dim]",
        border_style="green", expand=True,
    ))
 
    # CSS fixes table
    if css_fixes:
        t = Table(box=box.ROUNDED, expand=True, show_header=True)
        t.add_column("Selector",  style="cyan",  min_width=14)
        t.add_column("Property",  style="dim",   min_width=18)
        t.add_column("New Value", style="green", min_width=14)
        t.add_column("Reason",    style="white")
        for fix in css_fixes:
            t.add_row(
                fix.get("selector", ""),
                fix.get("property", ""),
                fix.get("value", ""),
                fix.get("reason", ""),
            )
        console.print(t)
 
    # Non-CSS suggestions
    if non_css:
        lines = Text()
        for i, s in enumerate(non_css, 1):
            lines.append(f"  {i}. {s}\n", style="white")
        console.print(Panel(lines, title="[bold]Non-CSS Suggestions[/bold]",
                            border_style="dim", expand=True))
 
 
# ---------------------------------------------------------------------------
# Public entry point — called directly from cli.py
# ---------------------------------------------------------------------------
 
def print_report(
    props: UIProperties,
    result: dict | None = None,
    suggestions: dict | None = None,
) -> None:
    """
    Print the full terminal report.
 
    Args:
        props:       UIProperties from extractor.py
        result:      scoring dict from scorer.py
        suggestions: LLM fix dict from llm_advisor.py (only if --fix was passed)
    """
    console.print()
    console.rule(f"[bold]UI-Auditer[/bold]  [dim]{props.url}[/dim]")
    console.print(f"  [dim]Title:[/dim] {props.title or '—'}\n")
 
    _print_extraction_table(props)
 
    if result:
        console.print()
        _print_score_table(result)
        console.print()
        _print_findings(result)
 
    if suggestions:
        console.print()
        _print_llm_suggestions(suggestions)
 
    console.print()
    console.rule()