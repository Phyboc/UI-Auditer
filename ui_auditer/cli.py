import io
import sys

import click
from rich.console import Console

# Fix UnicodeEncodeError on Windows legacy terminals (cp1252)
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from .advisor import get_suggestions, write_css_fix_file
from .extractor import extract
from .reporter import print_report
from .scorer import find_persona, load_all_personas, score

console = Console()


@click.command()
@click.argument("url")
@click.option("--persona", "-p", default="gen_z",
              help="Target audience slug: gen_z | elderly | corporate | minimalist | neurodivergent")
@click.option("--timeout", type=click.INT, default=15000, show_default=True,
              help="Page load timeout in milliseconds.")
@click.option("--json", "output_json", is_flag=True,
              help="Output raw JSON instead of the rich report.")
@click.option("--fix", "suggest_fix", is_flag=True, default=False, help="Generate CSS fix suggestions via LLM.")
@click.option("--output", "-o", "output_path", default=None,
              help="Output path for suggested CSS fixes (default: suggested_fixes.css).")
def main(url, persona, timeout, output_json, suggest_fix, output_path):
    """Evaluate a webpage's UI against a target audience persona."""

    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    # Load all personas and find the one requested
    try:
        all_personas = load_all_personas()
        persona_data = find_persona(all_personas, persona)
    except Exception as e:
        console.print(f"[red]Persona error:[/red] {e}")
        sys.exit(1)

    # In JSON mode, suppress Rich output to keep stdout clean for piping
    if output_json:
        console.quiet = True

    with console.status(f"[cyan]Rendering {url}…[/cyan]"):
        try:
            props = extract(url, timeout=timeout)
        except RuntimeError as e:
            # Setup problems (Playwright / Chromium missing) already carry the fix.
            console.print(f"[red]Cannot run the audit:[/red] {e}")
            sys.exit(1)
        except Exception as e:
            message = str(e)
            if "Executable doesn't exist" in message or "playwright install" in message:
                console.print(
                    "[red]Chromium is not installed.[/red] "
                    "Run: [bold]playwright install chromium[/bold]"
                )
            else:
                console.print(f"[red]Extraction failed:[/red] {message}")
            sys.exit(1)

    result = score(props, persona_data)

    llm_suggestions = None
    if suggest_fix and result:
        with console.status("[yellow]Asking LLM for fix suggestions…[/yellow]"):
            try:
                llm_suggestions = get_suggestions(props, persona_data, result)
                css_path = write_css_fix_file(llm_suggestions, output_path=output_path)
                console.print(f"[green]✓ CSS fixes written to[/green] [bold]{css_path}[/bold]")
            except Exception as e:
                console.print(f"[yellow]⚠ LLM fix failed:[/yellow] {e}")
                console.print("[dim]Set LLM_API_KEY in your .env file to use AI suggestions.[/dim]")

    if output_json:
        import json as _json
        from dataclasses import asdict
        print(_json.dumps({
            "properties": asdict(props),
            "score": result,
            "fixes": llm_suggestions,
        }, indent=2))
    else:
        print_report(props, result, suggestions=llm_suggestions)


if __name__ == "__main__":
    main()
