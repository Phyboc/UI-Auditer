import typer
from bs4 import BeautifulSoup
import click
from typing import Optional
import analyser
import requests

app = typer.Typer()

#Validation function to ensure only one input source is provided
def validate_input_sources(ctx: typer.Context):
    """Ensures exactly one input source is provided."""
    file_path = ctx.params.get("filePath")
    file_link = ctx.params.get("fileLink")

    if file_path is not None and file_link is not None:
        raise typer.BadParameter(
            "You cannot provide both --filePath and --fileLink. Choose only one."
        )

    if file_path is None and file_link is None:
        raise typer.BadParameter(
            "You must provide either --filePath or --fileLink."
        )


@app.command()
def analyzeHTML(filePath : Optional[str] = typer.Option(None, help="Enter your html file path"),
                 fileLink : Optional[str] = typer.Option(None, help="Enter your website link"),
                  _validate: Optional[bool] = typer.Option(None, hidden=True, callback=validate_input_sources)):
    
    if filePath:
        typer.echo("Reading local HTML file...")
        try:
            with open(filePath, "r", encoding="utf-8") as file:
                contentText = file.read()
        except FileNotFoundError:
            raise typer.BadParameter(
                f"The file path '{filePath}' does not exist."
            )
        except Exception as e:
            raise typer.BadParameter(f"Error reading file: {e}")

    else:
        typer.echo(f"Fetching remote HTML from {fileLink}...")
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
            response = requests.get(fileLink, headers=headers, timeout=10)
            response.raise_for_status()
            contentText = response.text
        except requests.RequestException as e:
            raise typer.BadParameter(f"Network error: {e}")
    
    soup = BeautifulSoup(contentText, 'html.parser')
    typer.echo(f'Analyzing the HTML content...')

    analysingObject = analyser.UIAnalyzer("persona.json")


if __name__ == "__main__":
    app()