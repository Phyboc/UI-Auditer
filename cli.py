import sys
import click
from rich.console import Console
from extractor import extract
from scorer import load_all_personas, find_persona, score
from reporter import print_report
from advisor import get_suggestions 

console = Console()

@click.command()
@click.argument("url")
@click.option("--persona", "-p", default="gen_z",
              help="Target audience slug: gen_z | elderly | corporate | minimalist | neurodivergent")
@click.option("--timeout", default=15000, show_default=True,
              help="Page load timeout in milliseconds.")
@click.option("--json", "output_json", is_flag=True,
              help="Output raw JSON instead of the rich report.")
@click.option("--fix", "suggest_fix",  is_flag=True, default=False, help="Apply automatic fixes to the webpage.")
def main(url, persona, timeout, output_json, suggest_fix):
    """Evaluate a webpage's UI against a target audience persona."""

    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    # Load all personas and find the one requested
    try:
        all_personas = load_all_personas("persona.json")
        persona_data = find_persona(all_personas, persona)
    except Exception as e:
        console.print(f"[red]Persona error:[/red] {e}")
        sys.exit(1)

    with console.status(f"[cyan]Rendering {url}…[/cyan]"):
        try:
            props = extract(url, timeout=timeout)
        except Exception as e:
            console.print(f"[red]Extraction failed:[/red] {e}")
            sys.exit(1)

    result = score(props, persona_data)

    llm_suggestions = None
    if suggest_fix and result:
        suggestions = get_suggestions(props, persona_data, result)

    if output_json:
        import json
        from dataclasses import asdict
        print(json.dumps({"properties": asdict(props), "score": result}, indent=2))
    else:
        print_report(props, result)

    


if __name__ == "__main__":
    main()