import io
import json
import sys
from dataclasses import asdict

import click
from rich.console import Console

# Fix UnicodeEncodeError on Windows legacy terminals (cp1252)
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from .advisor import get_suggestions, write_css_fix_file  # noqa: E402
from .extractor import UIProperties, extract  # noqa: E402
from .fixer import verify_fixes  # noqa: E402
from .reporter import (  # noqa: E402
    print_apply_result,
    print_comparison,
    print_crawl_table,
    print_report,
)
from .scorer import find_persona, load_all_personas, score  # noqa: E402

console = Console()


def _normalise_url(url: str) -> str:
    if not url.startswith(("http://", "https://", "file://")):
        return "https://" + url
    return url


def _extract_or_exit(url: str, timeout: int) -> UIProperties:
    try:
        return extract(url, timeout=timeout)
    except RuntimeError as exc:
        # Setup problems (Playwright / Chromium missing) already carry the fix.
        console.print(f"[red]Cannot run the audit:[/red] {exc}")
    except Exception as exc:  # noqa: BLE001 - surfaced to the user, not swallowed
        message = str(exc)
        if "Executable doesn't exist" in message or "playwright install" in message:
            console.print(
                "[red]Chromium is not installed.[/red] "
                "Run: [bold]playwright install chromium[/bold]"
            )
        else:
            console.print(f"[red]Extraction failed:[/red] {message}")
    sys.exit(1)


def _crawl(first: UIProperties, count: int, timeout: int, persona: dict) -> list[dict]:
    """Audit up to ``count`` same-origin links discovered on the start page."""
    pages: list[dict] = []
    for link in first.same_origin_links[:count]:
        try:
            page_props = extract(link, timeout=timeout)
        except Exception as exc:  # noqa: BLE001 - one bad page must not stop the run
            pages.append({"url": link, "error": str(exc).splitlines()[0][:200]})
            continue
        page_result = score(page_props, persona)
        pages.append({
            "url": link,
            "title": page_props.title,
            "score": page_result["overall_score"],
            "grade": page_result["grade"],
            "flags": len(page_result["dealbreakers_triggered"]),
        })
    return pages


@click.command()
@click.argument("url")
@click.option("--persona", "-p", default="gen_z",
              help="Target audience slug: gen_z | elderly | corporate | minimalist | neurodivergent")
@click.option("--timeout", type=click.INT, default=15000, show_default=True,
              help="Page load timeout in milliseconds.")
@click.option("--json", "output_json", is_flag=True,
              help="Output raw JSON instead of the rich report.")
@click.option("--fix", "suggest_fix", is_flag=True, default=False, help="Generate CSS fix suggestions via LLM.")
@click.option("--apply", "apply_fixes", is_flag=True, default=False,
              help="With --fix: render each rule, keep only the ones that do not lower the score.")
@click.option("--compare", is_flag=True, default=False,
              help="Score against all five personas in one run.")
@click.option("--crawl", type=click.INT, default=0, show_default=True,
              help="Also audit up to N same-origin links found on the page.")
@click.option("--fail-under", "fail_under", type=click.INT, default=None,
              help="Exit with status 1 when any audited page scores below this.")
@click.option("--output", "-o", "output_path", default=None,
              help="Output path for suggested CSS fixes (default: suggested_fixes.css).")
def main(url, persona, timeout, output_json, suggest_fix, apply_fixes, compare, crawl,
         fail_under, output_path):
    """Evaluate a webpage's UI against a target audience persona."""

    console.quiet = bool(output_json)  # keep stdout clean for piping

    if apply_fixes and not suggest_fix:
        console.print("[red]--apply requires --fix[/red] to generate the rules it verifies.")
        sys.exit(1)

    url = _normalise_url(url)

    # Load all personas and find the one requested
    try:
        all_personas = load_all_personas()
        persona_data = find_persona(all_personas, persona)
    except Exception as e:
        console.print(f"[red]Persona error:[/red] {e}")
        sys.exit(1)

    with console.status(f"[cyan]Rendering {url}…[/cyan]"):
        props = _extract_or_exit(url, timeout)

    result = score(props, persona_data)
    comparison = None
    if compare:
        comparison = sorted(
            (score(props, p) for p in all_personas),
            key=lambda r: r["overall_score"],
            reverse=True,
        )

    llm_suggestions = None
    apply_result = None
    if suggest_fix:
        with console.status("[yellow]Asking LLM for fix suggestions…[/yellow]"):
            try:
                llm_suggestions = get_suggestions(props, persona_data, result)
            except Exception as e:
                console.print(f"[yellow]⚠ LLM fix failed:[/yellow] {e}")
                console.print("[dim]Set LLM_API_KEY in your .env file to use AI suggestions.[/dim]")

    if llm_suggestions:
        fixes = llm_suggestions.get("css_fixes", [])
        if apply_fixes:
            with console.status("[magenta]Re-rendering each suggested fix…[/magenta]"):
                apply_result = verify_fixes(
                    fixes,
                    result,
                    lambda css: score(extract(url, timeout=timeout, inject_css=css), persona_data),
                )
            css_path = write_css_fix_file(
                {
                    "summary": llm_suggestions.get("summary", ""),
                    "css_fixes": apply_result["kept"],
                },
                output_path=output_path,
            )
            console.print(
                f"[green]✓ {len(apply_result['kept'])}/{len(fixes)} fixes verified[/green] "
                f"[bold]{css_path}[/bold]"
            )
        else:
            css_path = write_css_fix_file(llm_suggestions, output_path=output_path)
            console.print(f"[green]✓ CSS fixes written to[/green] [bold]{css_path}[/bold]")

    pages = _crawl(props, crawl, timeout, persona_data) if crawl else None

    if output_json:
        payload = {
            "properties": asdict(props),
            "score": result,
            "fixes": llm_suggestions,
        }
        if comparison is not None:
            payload["comparison"] = comparison
        if apply_result is not None:
            payload["apply"] = apply_result
        if pages is not None:
            payload["pages"] = pages
        print(json.dumps(payload, indent=2))
    else:
        print_report(props, result, suggestions=llm_suggestions)
        if comparison:
            console.print()
            print_comparison(comparison)
        if apply_result:
            console.print()
            print_apply_result(apply_result)
        if pages:
            console.print()
            print_crawl_table(pages)

    if fail_under is not None:
        scores = [result["overall_score"]]
        if comparison:
            scores += [r["overall_score"] for r in comparison]
        if pages:
            scores += [p["score"] for p in pages if "score" in p]
        worst = min(scores)
        if worst < fail_under:
            console.print(f"[red]Score {worst} is below --fail-under {fail_under}[/red]")
            sys.exit(1)


if __name__ == "__main__":
    main()
