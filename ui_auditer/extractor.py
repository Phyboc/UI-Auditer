"""
extractor.py
------------
Uses Playwright to render a real webpage and extract computed UI properties.
Works with React, Vue, Tailwind, Next.js — anything a browser can render.

Install:
    pip install playwright
    playwright install chromium

Run the extractor on its own:
    python -m ui_auditer.extractor https://yoursite.com
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .contrast import ratios_from_pairs


@dataclass
class UIProperties:
    url: str
    colors: list[str] = field(default_factory=list)
    fonts: list[str] = field(default_factory=list)
    font_sizes: list[str] = field(default_factory=list)
    font_size_weights: dict[str, int] = field(default_factory=dict)
    contrast_ratios: list[float] = field(default_factory=list)
    is_dark_mode: bool = False
    has_animations: bool = False
    running_animations: int = 0
    keyframe_animations: int = 0
    total_elements: int = 0
    max_dom_depth: int = 0
    buttons_count: int = 0
    links_count: int = 0
    inputs_count: int = 0
    text_density: float = 0.0
    title: str = ""
    # Dealbreaker signals — each one is observable from the rendered page.
    longest_text_block: int = 0
    scroll_depth_ratio: float = 0.0
    blocking_overlay: bool = False
    autoplay_media: int = 0
    hidden_navigation: bool = False


def extract(url: str, timeout: int = 15000) -> UIProperties:
    """
    Launch a headless browser, render the URL, and extract all UI properties
    using the browser's own computed style engine.

    Args:
        url: Full URL including https://
        timeout: Page load timeout in milliseconds (default 15s)

    Returns:
        UIProperties dataclass with all extracted values

    Raises:
        RuntimeError: for the two common setup failures (Playwright missing,
            Chromium not downloaded) with the command that fixes them.
    """
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    # Imported here so the CLI, scorer and reporter can be imported (and
    # --help can run) on a machine where Playwright is not installed yet.
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RuntimeError(
            "Playwright is not installed. Run: pip install playwright "
            "then: playwright install chromium"
        ) from exc

    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(headless=True)
        except Exception as exc:
            if "Executable doesn't exist" in str(exc):
                raise RuntimeError(
                    "Chromium is not installed for Playwright. "
                    "Run: playwright install chromium"
                ) from exc
            raise
        try:
            page = browser.new_page()

            # Wait until network is idle so JS frameworks finish rendering
            page.goto(url, wait_until="networkidle", timeout=timeout)

            title = page.title()

            # Single JS call extracts everything — faster than multiple round trips
            features = page.evaluate(r"""() => {

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

            // 1b. CONTRAST PAIRS — text colour vs effective background.
            // The ratio is computed in Python (contrast.py) so it is testable.
            const parseColor = (c) => {
                const m = (c || '').match(/rgba?\(([^)]+)\)/);
                if (!m) return null;
                const p = m[1].split(/[,\s\/]+/).filter(Boolean).map(parseFloat);
                if (p.length < 3 || p.some(isNaN)) return null;
                return [p[0], p[1], p[2], p.length > 3 ? p[3] : 1];
            };
            const over = (fg, bg) => {
                const a = fg[3];
                if (a >= 0.999) return fg;
                return [
                    fg[0] * a + bg[0] * (1 - a),
                    fg[1] * a + bg[1] * (1 - a),
                    fg[2] * a + bg[2] * (1 - a),
                    1,
                ];
            };
            const toCss = (c) => 'rgba(' + Math.round(c[0]) + ', ' + Math.round(c[1]) + ', '
                + Math.round(c[2]) + ', ' + c[3] + ')';
            const effectiveBg = (el) => {
                let acc = null;
                let cur = el;
                while (cur) {
                    const c = parseColor(getComputedStyle(cur).backgroundColor);
                    if (c && c[3] > 0) {
                        acc = acc ? over(acc, c) : c;
                        if (acc[3] >= 0.999) return toCss(acc);
                    }
                    cur = cur.parentElement;
                }
                return acc ? toCss(over(acc, [255, 255, 255, 1])) : 'rgba(255, 255, 255, 1)';
            };
            const contrastPairs = [];
            const seenContrast = new Set();
            const textWalker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
            let textNode;
            while ((textNode = textWalker.nextNode()) && contrastPairs.length < 500) {
                const value = (textNode.nodeValue || '').trim();
                if (value.length < 3) continue;
                const el = textNode.parentElement;
                if (!el) continue;
                const tag = el.tagName;
                if (tag === 'SCRIPT' || tag === 'STYLE' || tag === 'NOSCRIPT'
                    || tag === 'TEMPLATE') continue;
                const style = getComputedStyle(el);
                if (style.display === 'none' || style.visibility === 'hidden'
                    || parseFloat(style.opacity) === 0) continue;
                const fg = style.color;
                const bg = effectiveBg(el);
                const key = fg + '|' + bg;
                if (seenContrast.has(key)) continue;
                seenContrast.add(key);
                contrastPairs.push([fg, bg]);
            }

            // 2. FONTS
            const fonts = new Set();
            document.querySelectorAll('body *').forEach(el => {
                const family = getComputedStyle(el).fontFamily;
                if (family) {
                    const first = family.split(',')[0].replace(/['"]/g, '').trim();
                    if (first) fonts.add(first);
                }
            });

            // 3. FONT SIZES — weighted by visible character count
            const fontSizeWeights = {};
            document.querySelectorAll('body *').forEach(el => {
                let own = '';
                for (const child of el.childNodes) {
                    if (child.nodeType === 3) own += child.nodeValue;
                }
                const text = own.trim();
                if (text.length < 2 || el.offsetParent === null) return;
                const style = getComputedStyle(el);
                if (style.visibility === 'hidden' || parseFloat(style.opacity) === 0) return;
                const size = style.fontSize;
                fontSizeWeights[size] = (fontSizeWeights[size] || 0) + text.length;
            });
            const fontSizes = Object.keys(fontSizeWeights);

            // 4. DARK MODE — root first, body second, color-scheme as fallback
            const alphaOf = (c) => {
                const m = (c || '').match(/rgba?\(([^)]+)\)/);
                if (!m) return 0;
                const p = m[1].split(/[,\s\/]+/).filter(Boolean).map(parseFloat);
                return p.length > 3 ? p[3] : 1;
            };
            const htmlBg = getComputedStyle(document.documentElement).backgroundColor;
            const bodyBg = getComputedStyle(document.body).backgroundColor;
            const pageBg = alphaOf(htmlBg) > 0 ? htmlBg
                : (alphaOf(bodyBg) > 0 ? bodyBg : 'rgb(255, 255, 255)');
            const rgb = pageBg.match(/\d+/g) || [];
            const brightness = rgb.length >= 3
                ? (0.2126 * parseInt(rgb[0]) + 0.7152 * parseInt(rgb[1])
                   + 0.0722 * parseInt(rgb[2])) / 255
                : 1;
            const schemeHint = getComputedStyle(document.documentElement).colorScheme || '';
            const isDark = brightness < 0.35
                || (alphaOf(htmlBg) === 0 && alphaOf(bodyBg) === 0
                    && /\bdark\b/.test(schemeHint));

            // 5. ANIMATIONS
            // A CSS transition is a hover/focus style, not motion the user
            // sees, so it no longer counts. Only running animations and
            // declared keyframe animations are treated as motion.
            let runningAnimations = 0;
            if (document.getAnimations) {
                document.getAnimations().forEach(a => {
                    if (a.playState !== 'running') return;
                    let duration = 0;
                    try {
                        const timing = a.effect && a.effect.getComputedTiming();
                        duration = timing && typeof timing.duration === 'number'
                            ? timing.duration : 0;
                    } catch (e) { duration = 0; }
                    if (duration > 100) runningAnimations++;
                });
            }
            let keyframeAnimations = 0;
            document.querySelectorAll('body *').forEach(el => {
                const s = getComputedStyle(el);
                if (s.animationName && s.animationName !== 'none'
                    && parseFloat(s.animationDuration) > 0) {
                    keyframeAnimations++;
                }
            });
            const hasAnimations = runningAnimations > 0 || keyframeAnimations > 0;

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
            // Measured from text-node line boxes, so nested elements cannot be
            // counted twice, clipped to the viewport and capped at 1.0.
            const bodyRect = document.body.getBoundingClientRect();
            const pageArea = Math.max(1, bodyRect.width * bodyRect.height);
            let textArea = 0;
            const densityWalker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
            let densityNode;
            while ((densityNode = densityWalker.nextNode())) {
                const value = (densityNode.nodeValue || '').trim();
                if (value.length < 2) continue;
                const el = densityNode.parentElement;
                if (!el) continue;
                const tag = el.tagName;
                if (tag === 'SCRIPT' || tag === 'STYLE' || tag === 'NOSCRIPT'
                    || tag === 'TEMPLATE') continue;
                const style = getComputedStyle(el);
                if (style.display === 'none' || style.visibility === 'hidden'
                    || parseFloat(style.opacity) === 0) continue;
                const range = document.createRange();
                range.selectNodeContents(densityNode);
                const rects = range.getClientRects();
                for (let i = 0; i < rects.length; i++) {
                    const r = rects[i];
                    if (r.width <= 0 || r.height <= 0) continue;
                    if (r.bottom < 0 || r.top > window.innerHeight) continue;
                    textArea += r.width * r.height;
                }
            }
            const textDensity = Math.min(1, textArea / pageArea);

            // 9. LONGEST TEXT BLOCK — proxy for a wall of text
            let longestTextBlock = 0;
            const blockWalker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
            let blockNode;
            while ((blockNode = blockWalker.nextNode())) {
                const tag = blockNode.parentElement ? blockNode.parentElement.tagName : '';
                if (tag === 'SCRIPT' || tag === 'STYLE' || tag === 'NOSCRIPT'
                    || tag === 'TEMPLATE') continue;
                const value = (blockNode.nodeValue || '').trim();
                if (value.length > longestTextBlock) longestTextBlock = value.length;
            }

            // 10. SCROLL DEPTH — proxy for an endlessly scrolling feed
            const viewportHeight = window.innerHeight || 1;
            const scrollDepthRatio = document.documentElement.scrollHeight / viewportHeight;

            // 11. BLOCKING OVERLAY — fixed/sticky layer covering half the viewport
            let blockingOverlay = false;
            const viewportArea = (window.innerWidth || 1) * viewportHeight;
            document.querySelectorAll('body *').forEach(el => {
                if (blockingOverlay) return;
                const s = getComputedStyle(el);
                if (s.position !== 'fixed' && s.position !== 'sticky') return;
                if (s.display === 'none' || s.visibility === 'hidden'
                    || parseFloat(s.opacity) === 0) return;
                const z = parseInt(s.zIndex, 10);
                if (!isNaN(z) && z < 100) return;
                const r = el.getBoundingClientRect();
                if (r.width * r.height >= 0.5 * viewportArea) blockingOverlay = true;
            });

            // 12. AUTOPLAY MEDIA
            const autoplay = new Set();
            document.querySelectorAll('video[autoplay], audio[autoplay]')
                .forEach(el => autoplay.add(el));
            document.querySelectorAll('video').forEach(v => {
                if (!v.paused && !v.ended) autoplay.add(v);
            });

            // 13. HIDDEN NAVIGATION — nav exists but is collapsed at desktop width
            let hiddenNavigation = false;
            document.querySelectorAll('nav, [role="navigation"]').forEach(el => {
                const s = getComputedStyle(el);
                if (s.display === 'none' || s.visibility === 'hidden'
                    || el.getBoundingClientRect().width === 0) hiddenNavigation = true;
            });

            return {
                colors:         [...colors],
                contrast_pairs: contrastPairs,
                fonts:          [...fonts],
                font_sizes:     [...fontSizes],
                font_size_weights: fontSizeWeights,
                is_dark_mode:   isDark,
                has_animations: hasAnimations,
                running_animations: runningAnimations,
                keyframe_animations: keyframeAnimations,
                total_elements: allElements.length,
                max_dom_depth:  maxDepth,
                buttons_count:  buttons,
                links_count:    links,
                inputs_count:   inputs,
                text_density:   textDensity,
                longest_text_block: longestTextBlock,
                scroll_depth_ratio: scrollDepthRatio,
                blocking_overlay: blockingOverlay,
                autoplay_media: autoplay.size,
                hidden_navigation: hiddenNavigation,
            };
        }""")

            pairs = features.pop("contrast_pairs", [])
            features["contrast_ratios"] = ratios_from_pairs(pairs)

        finally:
            browser.close()

    return UIProperties(url=url, title=title, **features)


# Quick test — run: python -m ui_auditer.extractor https://yoursite.com
if __name__ == "__main__":
    import sys

    test_url = sys.argv[1] if len(sys.argv) > 1 else "https://github.com"
    print(f"Extracting from {test_url}...\n")
    props = extract(test_url)
    print(f"Title:        {props.title}")
    print(f"Dark mode:    {props.is_dark_mode}")
    print(f"Animations:   {props.has_animations}")
    print(f"Colors found: {len(props.colors)}")
    print(f"Fonts:        {props.fonts}")
    print(f"Font sizes:   {props.font_sizes}")
    print(f"Elements:     {props.total_elements}, depth {props.max_dom_depth}")
    print(f"Interactive:  {props.buttons_count} buttons, {props.links_count} links, {props.inputs_count} inputs")
    print(f"Text density: {props.text_density:.1%}")
    print(f"Longest text block: {props.longest_text_block} chars")
    print(f"Scroll depth:       {props.scroll_depth_ratio:.1f}x viewport")
    print(f"Blocking overlay:   {props.blocking_overlay}")
    print(f"Autoplay media:     {props.autoplay_media}")
    print(f"Hidden navigation:  {props.hidden_navigation}")
