"""
cli.py
------
Entry point: `python -m web_auditer <url>`
"""

import sys
import click
from rich.console import Console
from web_auditer.extractor import extract
from web_auditer.reporter import print_report

console = Console()


@click.command()
@click.argument("url")
@click.option("--json", "output_json", is_flag=True, default=False,
              help="Output raw properties as JSON instead of the rich report.")
@click.option("--timeout", default=10, show_default=True,
              help="Request timeout in seconds.")
def main(url: str, output_json: bool, timeout: int) -> None:
    """
    Analyze the UI of a webpage at URL and print a property report.

    Example:\n
        python -m web_auditer https://stripe.com\n
        python -m web_auditer https://github.com --json
    """
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    with console.status(f"[bold green]Fetching {url}…[/bold green]"):
        try:
            props = extract(url, timeout=timeout)
        except Exception as e:
            console.print(f"[bold red]Error:[/bold red] {e}")
            sys.exit(1)

    if output_json:
        import json
        from dataclasses import asdict
        print(json.dumps(asdict(props), indent=2))
    else:
        print_report(props)


if __name__ == "__main__":
    main()