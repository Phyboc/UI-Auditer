"""WCAG 2.1 contrast utilities.

The extractor hands us raw ``(foreground, background)`` pairs from the browser's
computed styles; this module turns them into contrast ratios. Keeping the maths
in Python (instead of the injected JS) makes it unit-testable.

Reference: https://www.w3.org/TR/WCAG21/#dfn-contrast-ratio
"""

from __future__ import annotations

import re

_RGB_RE = re.compile(r"rgba?\(([^)]+)\)", re.IGNORECASE)
_HEX_RE = re.compile(r"#([0-9a-fA-F]{3,8})")


def _clamp(value: float) -> float:
    return max(0.0, min(255.0, value))


def parse_css_color(value: str | None) -> tuple[float, float, float, float] | None:
    """Parse ``rgb()`` / ``rgba()`` / hex into ``(r, g, b, alpha)``.

    Returns ``None`` for anything that is not an opaque-enough colour string.
    Computed styles always serialise as ``rgb()``/``rgba()``, so hex support is
    only a convenience for tests and hand-written data.
    """
    if not value or not isinstance(value, str):
        return None

    text = value.strip()
    match = _RGB_RE.search(text)
    if match:
        parts = [p for p in re.split(r"[,\s/]+", match.group(1)) if p]
        if len(parts) < 3:
            return None
        try:
            nums = [float(p.rstrip("%")) for p in parts[:3]]
        except ValueError:
            return None
        alpha = 1.0
        if len(parts) >= 4:
            try:
                alpha = float(parts[3])
            except ValueError:
                alpha = 1.0
        return (_clamp(nums[0]), _clamp(nums[1]), _clamp(nums[2]), max(0.0, min(1.0, alpha)))

    match = _HEX_RE.search(text)
    if match:
        digits = match.group(1)
        if len(digits) in (3, 4):
            digits = "".join(ch * 2 for ch in digits)
        if len(digits) not in (6, 8):
            return None
        r, g, b = (int(digits[i : i + 2], 16) for i in (0, 2, 4))
        alpha = int(digits[6:8], 16) / 255 if len(digits) == 8 else 1.0
        return (float(r), float(g), float(b), alpha)

    if text.lower() == "transparent":
        return (0.0, 0.0, 0.0, 0.0)

    return None


def _linearise(channel: float) -> float:
    channel /= 255.0
    return channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4


def relative_luminance(rgb: tuple[float, float, float, float]) -> float:
    """WCAG relative luminance of an sRGB colour."""
    r, g, b = rgb[:3]
    return 0.2126 * _linearise(r) + 0.7152 * _linearise(g) + 0.0722 * _linearise(b)


def composite(
    fg: tuple[float, float, float, float],
    bg: tuple[float, float, float, float],
) -> tuple[float, float, float, float]:
    """Flatten a translucent foreground over an opaque-ish background."""
    alpha = fg[3]
    if alpha >= 1.0:
        return fg
    return (
        fg[0] * alpha + bg[0] * (1 - alpha),
        fg[1] * alpha + bg[1] * (1 - alpha),
        fg[2] * alpha + bg[2] * (1 - alpha),
        1.0,
    )


def contrast_ratio(fg: tuple[float, float, float, float],
                   bg: tuple[float, float, float, float]) -> float:
    """Contrast ratio between text and background, from 1.0 to 21.0."""
    foreground = composite(fg, bg)
    background = bg if bg[3] >= 1.0 else (255.0, 255.0, 255.0, 1.0)
    lighter, darker = sorted(
        (relative_luminance(foreground), relative_luminance(background)), reverse=True
    )
    return (lighter + 0.05) / (darker + 0.05)


def ratios_from_pairs(pairs: list[tuple[str, str]] | list[list[str]]) -> list[float]:
    """Convert ``(foreground, background)`` CSS strings into ratios.

    Pairs that cannot be parsed, or whose background is fully transparent, are
    skipped rather than guessed at.
    """
    ratios: list[float] = []
    for pair in pairs or []:
        if not pair or len(pair) < 2:
            continue
        fg = parse_css_color(pair[0])
        bg = parse_css_color(pair[1])
        if fg is None or bg is None or bg[3] <= 0:
            continue
        ratios.append(round(contrast_ratio(fg, bg), 2))
    return ratios
