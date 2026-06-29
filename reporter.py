"""
reporter.py
-----------
Pretty-print a UIProperties object to the terminal using Rich.
Matches the Playwright-based UIProperties dataclass.
"""

from rich.console import Console
from rich.table import Table
from rich import box
from rich.text import Text
from extractor import UIProperties

console = Console()


def _rgb_to_hex(rgb_str: str) -> str | None:
    """Convert 'rgb(r, g, b)' or 'rgba(r,g,b,a)' to #rrggbb. Returns None on failure."""
    try:
        nums = [int(float(x.strip())) for x in
                rgb_str.replace("rgba","").replace("rgb","").strip("()").split(",")]
        return "#{:02x}{:02x}{:02x}".format(nums[0], nums[1], nums[2])
    except Exception:
        return None


def _color_swatch(color_str: str) -> Text:
    """Show a colored block next to the color value. Handles rgb() strings."""
    hex_color = _rgb_to_hex(color_str) if color_str.startswith("rgb") else color_str
    t = Text()
    if hex_color:
        try:
            t.append("██ ", style=hex_color)
        except Exception:
            pass
    t.append(color_str, style="dim")
    return t


def print_report(props: UIProperties) -> None:
    """Render a UIProperties report to the terminal."""

    console.print()
    console.rule("[bold]UI Property Report[/bold]")
    console.print(f"[dim]URL:[/dim]   {props.url}")
    console.print(f"[dim]Title:[/dim] {props.title or '(none found)'}")
    console.print()

    # --- Colors -------------------------------------------------------------
    color_table = Table(title="Colors", box=box.SIMPLE_HEAVY, show_header=True)
    color_table.add_column("Property", style="dim", width=22)
    color_table.add_column("Value")

    color_table.add_row("Total unique colors", str(len(props.colors)))
    color_table.add_row("Dark mode", "✓ Yes" if props.is_dark_mode else "No")

    if props.colors:
        swatches = Text()
        for c in props.colors[:8]:
            try:
                hex_c = _rgb_to_hex(c) if c.startswith("rgb") else c
                if hex_c:
                    swatches.append("██ ", style=hex_c)
            except Exception:
                pass
        color_table.add_row("Palette sample", swatches)

    console.print(color_table)

    # --- Typography ---------------------------------------------------------
    type_table = Table(title="Typography", box=box.SIMPLE_HEAVY)
    type_table.add_column("Property", style="dim", width=22)
    type_table.add_column("Value")

    type_table.add_row(
        "Font families",
        ", ".join(props.fonts) if props.fonts else Text("none detected", style="dim")
    )
    type_table.add_row(
        "Font sizes found",
        ", ".join(props.font_sizes) if props.font_sizes else Text("none detected", style="dim")
    )

    console.print(type_table)

    # --- Layout -------------------------------------------------------------
    layout_table = Table(title="Layout & Structure", box=box.SIMPLE_HEAVY)
    layout_table.add_column("Property", style="dim", width=22)
    layout_table.add_column("Value")

    layout_table.add_row("Total HTML elements", str(props.total_elements))
    layout_table.add_row("Max DOM depth",       str(props.max_dom_depth))
    layout_table.add_row("Buttons",             str(props.buttons_count))
    layout_table.add_row("Links",               str(props.links_count))
    layout_table.add_row("Form inputs",         str(props.inputs_count))

    density_pct = f"{props.text_density:.1%}"
    density_label = (
        "High (text-heavy)" if props.text_density > 0.5
        else "Balanced"     if props.text_density > 0.25
        else "Low (spacious)"
    )
    layout_table.add_row("Text density", f"{density_pct} — {density_label}")

    console.print(layout_table)

    # --- Animation ----------------------------------------------------------
    anim_table = Table(title="Motion & Animation", box=box.SIMPLE_HEAVY)
    anim_table.add_column("Property", style="dim", width=22)
    anim_table.add_column("Value")

    anim_table.add_row(
        "Animations / transitions",
        Text("✓ Detected", style="green") if props.has_animations
        else Text("None found", style="dim")
    )

    console.print(anim_table)
    console.rule()
    console.print()