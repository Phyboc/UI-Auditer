"""
extractor.py
------------
Uses Playwright to render a real webpage and extract computed UI properties.
Works with React, Vue, Tailwind, Next.js — anything a browser can render.

Install:
    pip install playwright
    playwright install chromium
"""

from dataclasses import dataclass, field
from playwright.sync_api import sync_playwright


@dataclass
class UIProperties:
    url: str
    colors: list[str] = field(default_factory=list)
    fonts: list[str] = field(default_factory=list)
    font_sizes: list[str] = field(default_factory=list)
    is_dark_mode: bool = False
    has_animations: bool = False
    total_elements: int = 0
    max_dom_depth: int = 0
    buttons_count: int = 0
    links_count: int = 0
    inputs_count: int = 0
    text_density: float = 0.0
    title: str = ""


def extract(url: str, timeout: int = 15000) -> UIProperties:
    """
    Launch a headless browser, render the URL, and extract all UI properties
    using the browser's own computed style engine.

    Args:
        url: Full URL including https://
        timeout: Page load timeout in milliseconds (default 15s)

    Returns:
        UIProperties dataclass with all extracted values
    """
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # Wait until network is idle so JS frameworks finish rendering
        page.goto(url, wait_until="networkidle", timeout=timeout)

        title = page.title()

        # Single JS call extracts everything — faster than multiple round trips
        features = page.evaluate("""() => {

            // 1. COLORS
            const colors = new Set();
            document.querySelectorAll('body *').forEach(el => {
                const s = getComputedStyle(el);
                const bg = s.backgroundColor;
                if (bg && bg !== 'rgba(0, 0, 0, 0)') colors.add(bg);
                const color = s.color;
                if (color) colors.add(color);
                const border = s.borderColor;
                if (border && border !== 'rgba(0, 0, 0, 0)') colors.add(border);
            });

            // 2. FONTS
            const fonts = new Set();
            document.querySelectorAll('body *').forEach(el => {
                const family = getComputedStyle(el).fontFamily;
                if (family) {
                    const first = family.split(',')[0].replace(/['"]/g, '').trim();
                    if (first) fonts.add(first);
                }
            });

            // 3. FONT SIZES
            const fontSizes = new Set();
            document.querySelectorAll('p, h1, h2, h3, h4, h5, h6, span, a, button, li').forEach(el => {
                if (el.textContent.trim().length > 3) {
                    fontSizes.add(getComputedStyle(el).fontSize);
                }
            });

            // 4. DARK MODE
            const bodyBg = getComputedStyle(document.body).backgroundColor;
            const rgb = bodyBg.match(/\\d+/g) || [];
            const isDark = rgb.length >= 3
                && parseInt(rgb[0]) < 80
                && parseInt(rgb[1]) < 80
                && parseInt(rgb[2]) < 80;

            // 5. ANIMATIONS
            let hasAnimations = false;
            document.querySelectorAll('body *').forEach(el => {
                const s = getComputedStyle(el);
                if (
                    (s.animationName && s.animationName !== 'none') ||
                    (s.transitionDuration && s.transitionDuration !== '0s')
                ) { hasAnimations = true; }
            });

            // 6. DOM STRUCTURE
            const allElements = document.querySelectorAll('*');
            let maxDepth = 0;
            allElements.forEach(el => {
                let depth = 0;
                let parent = el.parentElement;
                while (parent) { depth++; parent = parent.parentElement; }
                if (depth > maxDepth) maxDepth = depth;
            });

            // 7. INTERACTIVE ELEMENTS
            const buttons = document.querySelectorAll(
                'button, [role="button"], input[type="submit"], input[type="button"]'
            ).length;
            const links = document.querySelectorAll('a[href]').length;
            const inputs = document.querySelectorAll(
                'input:not([type="submit"]):not([type="button"]):not([type="hidden"]), textarea, select'
            ).length;

            // 8. TEXT DENSITY
            const totalArea = document.body.offsetWidth * document.body.offsetHeight;
            let textArea = 0;
            document.querySelectorAll('p, h1, h2, h3, h4, h5, h6, li, span').forEach(el => {
                if (el.textContent.trim().length > 10 && el.offsetParent !== null) {
                    const rect = el.getBoundingClientRect();
                    textArea += rect.width * rect.height;
                }
            });
            const textDensity = totalArea > 0 ? textArea / totalArea : 0;

            return {
                colors:         [...colors],
                fonts:          [...fonts],
                font_sizes:     [...fontSizes],
                is_dark_mode:   isDark,
                has_animations: hasAnimations,
                total_elements: allElements.length,
                max_dom_depth:  maxDepth,
                buttons_count:  buttons,
                links_count:    links,
                inputs_count:   inputs,
                text_density:   textDensity,
            };
        }""")

        browser.close()

    return UIProperties(url=url, title=title, **features)


# Quick test — run: python extractor.py https://yoursite.com
if __name__ == "__main__":
    import sys
    test_url = sys.argv[1] if len(sys.argv) > 1 else "https://github.com"
    print(f"Extracting from {test_url}...\n")
    props = extract(test_url)
    print(f"Title:        {props.title}")
    print(f"Dark mode:    {props.is_dark_mode}")
    print(f"Animations:   {props.has_animations}")
    print(f"Colors found: {len(props.colors)} → {props.colors[:3]}")
    print(f"Fonts:        {props.fonts}")
    print(f"Font sizes:   {props.font_sizes}")
    print(f"Elements:     {props.total_elements}, depth {props.max_dom_depth}")
    print(f"Interactive:  {props.buttons_count} buttons, {props.links_count} links, {props.inputs_count} inputs")
    print(f"Text density: {props.text_density:.1%}")