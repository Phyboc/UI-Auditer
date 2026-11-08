"""fixer.py
--------
Closed-loop verification of CSS fix suggestions.

The advisor proposes up to five rules, but a suggestion is only a guess until it
is rendered. This module applies the rules one at a time, re-scores the page
after each one, and keeps a rule only when it does not lower the score.

The caller supplies ``rescore(css) -> score dict``, so this module never touches
a browser and can be unit-tested with a fake.
"""

from __future__ import annotations

from collections.abc import Callable

from .scorer import grade_for


def css_block(fix: dict) -> str:
    """Render one suggestion as a CSS rule, or ``""`` when it is incomplete."""
    selector = (fix.get("selector") or "").strip()
    prop = (fix.get("property") or "").strip()
    value = (fix.get("value") or "").strip()
    if not selector or not prop or not value:
        return ""

    lines: list[str] = []
    reason = (fix.get("reason") or "").strip().replace("*/", "* /")
    if reason:
        lines.append(f"/* {reason} */")
    lines.append(f"{selector} {{ {prop}: {value}; }}")
    return "\n".join(lines)


def build_css(fixes: list[dict]) -> str:
    """Concatenate every complete rule into one stylesheet fragment."""
    blocks = [block for block in (css_block(f) for f in fixes or []) if block]
    return "\n".join(blocks)


def _dedupe(fixes: list[dict]) -> list[dict]:
    """Collapse duplicates by selector+property; the last value wins."""
    by_key: dict[tuple[str, str], dict] = {}
    order: list[tuple[str, str]] = []
    for fix in fixes:
        key = ((fix.get("selector") or "").strip(), (fix.get("property") or "").strip())
        if key not in by_key:
            order.append(key)
        by_key[key] = fix
    return [by_key[key] for key in order]


def verify_fixes(
    fixes: list[dict] | None,
    baseline: dict,
    rescore: Callable[[str], dict],
    min_gain: int = 0,
) -> dict:
    """Apply fixes cumulatively and keep the ones that hold the score up.

    Args:
        fixes: CSS suggestions (``selector`` / ``property`` / ``value``).
        baseline: Score dict for the unmodified page.
        rescore: Callable that renders a page with the given CSS and scores it.
        min_gain: Points a rule must add to be kept. ``0`` keeps rules that are
            neutral, so a fix that removes a real defect without moving the
            score (because the dimension is already capped) is not thrown away.

    Returns:
        ``{baseline_score, baseline_grade, final_score, final_grade,
        kept, dropped, steps, css}``.
    """
    baseline_score = int(baseline.get("overall_score", 0))
    best_score = baseline_score
    kept_css = ""
    kept: list[dict] = []
    dropped: list[dict] = []
    steps: list[dict] = []

    candidates = [f for f in (fixes or []) if isinstance(f, dict)]
    for fix in _dedupe(candidates):
        block = css_block(fix)
        if not block:
            dropped.append({"fix": fix, "reason": "incomplete rule (selector/property/value)"})
            continue

        candidate = f"{kept_css}\n{block}".strip()
        try:
            rescored = rescore(candidate)
            after = int(rescored.get("overall_score", 0))
        except Exception as exc:  # noqa: BLE001 - a broken rule is just a drop
            dropped.append({"fix": fix, "reason": f"re-render failed: {exc}"})
            steps.append({
                "selector": fix.get("selector", ""),
                "property": fix.get("property", ""),
                "value": fix.get("value", ""),
                "score_before": best_score,
                "score_after": None,
                "kept": False,
            })
            continue

        keep = after >= best_score + min_gain
        steps.append({
            "selector": fix.get("selector", ""),
            "property": fix.get("property", ""),
            "value": fix.get("value", ""),
            "score_before": best_score,
            "score_after": after,
            "kept": keep,
        })

        if keep:
            kept.append(fix)
            kept_css = candidate
            best_score = after
        else:
            reason = (
                f"score fell from {best_score} to {after}"
                if after < best_score
                else f"no measurable gain (needs +{min_gain})"
            )
            dropped.append({"fix": fix, "reason": reason})

    return {
        "baseline_score": baseline_score,
        "baseline_grade": baseline.get("grade", grade_for(baseline_score)),
        "final_score": best_score,
        "final_grade": grade_for(best_score),
        "kept": kept,
        "dropped": dropped,
        "steps": steps,
        "css": kept_css,
    }
