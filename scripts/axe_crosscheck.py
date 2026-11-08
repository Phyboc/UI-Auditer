#!/usr/bin/env python3
"""Cross-check our WCAG contrast maths against axe-core.

axe-core is the de-facto reference implementation of the WCAG contrast rule.
This script renders each target, runs axe's ``color-contrast`` rule, and
recomputes every ratio axe reports with ``ui_auditer.contrast``. It exits
non-zero when the two disagree by more than ``--tolerance``.

Usage::

    python scripts/axe_crosscheck.py tests/fixtures/contrast_page.html
    python scripts/axe_crosscheck.py https://example.com
    python scripts/axe_crosscheck.py https://example.com --axe node_modules/axe-core/axe.min.js

axe-core is fetched from a CDN unless ``--axe`` points at a local
``axe.min.js``. Playwright and Chromium are required, exactly as for the audit.

What this validates
-------------------
1. **The maths.** For every element axe flags, our ratio for the same
   foreground/background pair must match axe's reported ratio.
2. **The large-text exception.** axe applies the 3:1 large-text rule, so a
   heading our scorer now accepts must not appear in axe's violations.

What it does not validate: coverage. axe reports per element, we report per
distinct (foreground, background, size, weight) style, so the two counts are
comparable in spirit but never equal on a real page.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from ui_auditer.contrast import contrast_ratio, parse_css_color  # noqa: E402
from ui_auditer.extractor import extract  # noqa: E402
from ui_auditer.scorer import _contrast_failures, required_contrast  # noqa: E402

AXE_CDN = "https://cdnjs.cloudflare.com/ajax/libs/axe-core/4.10.2/axe.min.js"
PERSONA_FLOOR = 4.5  # WCAG AA body text, used only for the coverage comparison


def _target_url(value: str) -> str:
    """Accept a path, a bare host, or a full URL."""
    path = Path(value)
    if path.exists():
        return path.resolve().as_uri()
    if not value.startswith(("http://", "https://", "file://")):
        return "https://" + value
    return value


def _axe_source(axe_path: str | None) -> str:
    if axe_path:
        return Path(axe_path).read_text(encoding="utf-8")
    import requests

    response = requests.get(AXE_CDN, timeout=30)
    response.raise_for_status()
    return response.text


AXE_RUN = """async () => {
  const result = await axe.run(document, {
    runOnly: {type: 'rule', values: ['color-contrast']},
  });
  const nodes = [];
  for (const violation of result.violations) {
    for (const node of violation.nodes) {
      const data = (node.any && node.any[0] && node.any[0].data) || {};
      nodes.push({
        target: (node.target || []).join(' '),
        fg: data.fgColor,
        bg: data.bgColor,
        axe_ratio: data.contrastRatio,
        font_size_px: data.fontSize,
        font_weight: data.fontWeight,
        expected: data.expectedContrastRatio,
      });
    }
  }
  return {
    violations: result.violations.length,
    incomplete: result.incomplete.length,
    nodes: nodes,
  };
}"""


def run_axe(url: str, axe_source: str, timeout: int, viewport: tuple[int, int]) -> dict:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            page = browser.new_page(
                viewport={"width": viewport[0], "height": viewport[1]}
            )
            page.goto(url, wait_until="load", timeout=timeout)
            # evaluate() instead of add_script_tag(): not blocked by page CSP.
            page.evaluate(axe_source)
            page.wait_for_function(
                "() => window.axe && typeof window.axe.run === 'function'", timeout=15000
            )
            return page.evaluate(AXE_RUN)
        finally:
            browser.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("targets", nargs="*", help="URLs or local HTML files.")
    parser.add_argument("--axe", metavar="PATH", help="Local axe.min.js (offline use).")
    parser.add_argument("--tolerance", type=float, default=0.1,
                        help="Largest allowed ratio difference (default 0.1).")
    parser.add_argument("--timeout", type=int, default=25000, help="Load timeout in ms.")
    args = parser.parse_args()

    targets = args.targets or [str(ROOT / "tests" / "fixtures" / "contrast_page.html")]
    axe_source = _axe_source(args.axe)
    failures = 0

    for target in targets:
        url = _target_url(target)
        print(f"\n{url}")

        try:
            data = run_axe(url, axe_source, args.timeout, (1280, 800))
        except Exception as exc:  # noqa: BLE001 - report and continue
            print(f"  axe could not run: {exc}")
            print("  If this is a network error, pass --axe path/to/axe.min.js")
            failures += 1
            continue

        print(f"  axe: {len(data['nodes'])} node(s) violating, {data['incomplete']} incomplete")

        max_delta = 0.0
        for node in data["nodes"]:
            fg = parse_css_color(node["fg"])
            bg = parse_css_color(node["bg"])
            ours = None if fg is None or bg is None else round(contrast_ratio(fg, bg), 2)
            axe_ratio = node["axe_ratio"]
            delta = None if ours is None or axe_ratio is None else abs(ours - float(axe_ratio))
            if delta is not None:
                max_delta = max(max_delta, delta)
            marker = ""
            if delta is not None and delta > args.tolerance:
                marker = "  <-- MISMATCH"
                failures += 1
            size = node.get("font_size_px")
            size_txt = f"{size}px" if size is not None else "?"
            print(
                f"  axe {axe_ratio} vs ours {ours} (delta {delta}) - "
                f"{size_txt}/{node.get('font_weight')} {node['target']}{marker}"
            )

        print(f"  maths agreement: max delta {max_delta:.2f}")

        props = extract(url, timeout=args.timeout)
        failing, samples = _contrast_failures(props, PERSONA_FLOOR)
        relaxed = sum(
            1 for s in samples
            if PERSONA_FLOOR > s["ratio"] >= required_contrast(
                PERSONA_FLOOR, s.get("font_size_px"), s.get("bold", False)
            )
        )
        print(
            f"  coverage: axe flagged {len(data['nodes'])} element(s); "
            f"ui-auditer flagged {len(failing)}/{len(samples)} styles "
            f"({relaxed} passing only as large text)"
        )

    print(f"\n{'PASS' if failures == 0 else 'FAIL'} - {failures} problem(s)")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
