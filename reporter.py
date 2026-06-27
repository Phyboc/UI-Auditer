"""
reporter.py
-----------
Pretty-print a UIProperties object to the terminal using Rich.
"""

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.columns import Columns
from rich import box
from rich.text import Text
from ui_evaluator.extractor import UIProperties

console = Console()


def _contrast_label(ratio: float | None) -> str:
    if ratio is None:
        return "unknown"
    if ratio >= 7:
        return f"{ratio} ✓ AAA"
    if ratio >= 4.5:
        return f"{ratio} ✓ AA"
    if ratio >= 3:
        return f"{ratio} ⚠ AA Large only"
    return f"{ratio} ✗ Fails WCAG"


def _color_swatch(hex_color: str) -> Text:
    """Return a Rich Text block showing a colored square + hex value."""
    try:
        t = Text()
        t.append("██ ", style=hex_color)
        t.append(hex_color, style="dim")
        return t
    except Exception:
        return Text(hex_color)


def print_report(props: UIProperties) -> None:
    """Render a UIProperties report to the terminal."""

    console.print()
    console.rule(f"[bold]UI Property Report[/bold]")
    console.print(f"[dim]URL:[/dim] {props.url}")
    console.print(f"[dim]Title:[/dim] {props.title or '(none found)'}")
    console.print(f"[dim]Page size:[/dim] {props.page_size_kb} KB")
    console.print()

    # --- Colors table -------------------------------------------------------
    color_table = Table(title="Colors", box=box.SIMPLE_HEAVY, show_header=True)
    color_table.add_column("Property", style="dim", width=20)
    color_table.add_column("Value")

    color_table.add_row("Background", _color_swatch(props.background_color) if props.background_color else Text("not detected", style="dim"))
    color_table.add_row("Text color", _color_swatch(props.text_color) if props.text_color else Text("not detected", style="dim"))
    color_table.add_row("Unique CSS colors", str(props.color_count))

    if props.dominant_colors:
        swatches = Text()
        for c in props.dominant_colors[:5]:
            try:
                swatches.append("██ ", style=c)
            except Exception:
                swatches.append(c + " ")
        color_table.add_row("Palette sample", swatches)

    contrast_str = _contrast_label(props.contrast_ratio)
    style = "green" if props.contrast_ratio and props.contrast_ratio >= 4.5 else "yellow" if props.contrast_ratio else "dim"
    color_table.add_row("Contrast ratio", Text(contrast_str, style=style))

    console.print(color_table)

    # --- Typography table ---------------------------------------------------
    type_table = Table(title="Typography", box=box.SIMPLE_HEAVY)
    type_table.add_column("Property", style="dim", width=20)
    type_table.add_column("Value")

    type_table.add_row("Font families", ", ".join(props.font_families) if props.font_families else Text("none detected", style="dim"))
    type_table.add_row("Font sizes (px)", ", ".join(str(s) for s in props.font_sizes) if props.font_sizes else Text("none detected", style="dim"))
    type_table.add_row("Web fonts", "✓ Yes" if props.uses_web_fonts else "No")

    console.print(type_table)

    # --- Layout table -------------------------------------------------------
    layout_table = Table(title="Layout & Content", box=box.SIMPLE_HEAVY)
    layout_table.add_column("Property", style="dim", width=22)
    layout_table.add_column("Value")

    layout_table.add_row("Total HTML elements", str(props.total_elements))
    layout_table.add_row("Interactive elements", str(props.interactive_elements))
    layout_table.add_row("Images", str(props.image_count))
    layout_table.add_row("Hero image", "✓ Yes" if props.has_hero_image else "No")
    layout_table.add_row("Word count", str(props.word_count))
    layout_table.add_row("CTA elements", str(props.cta_count))

    if props.avg_padding_px is not None:
        layout_table.add_row("Avg CSS padding", f"{props.avg_padding_px}px")
    if props.avg_margin_px is not None:
        layout_table.add_row("Avg CSS margin", f"{props.avg_margin_px}px")

    console.print(layout_table)

    # --- Animation table ----------------------------------------------------
    anim_table = Table(title="Motion & Animation", box=box.SIMPLE_HEAVY)
    anim_table.add_column("Property", style="dim", width=22)
    anim_table.add_column("Value")

    anim_table.add_row("Has animations/transitions", "✓ Yes" if props.has_animations else "No")
    if props.animation_keywords:
        anim_table.add_row("Keywords found", ", ".join(props.animation_keywords))

    console.print(anim_table)
    console.rule()
    console.print()