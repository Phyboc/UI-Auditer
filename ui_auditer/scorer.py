"""
scorer.py
---------
Rule-based heuristic engine. Compares UIProperties against a persona JSON
and returns structured scores + recommendations.

"""

import json
import re
from pathlib import Path

from .extractor import UIProperties

# ---------------------------------------------------------------------------
# Dealbreaker thresholds (module-level so they are easy to calibrate later)
# ---------------------------------------------------------------------------
LARGE_TEXT_BLOCK_CHARS = 800      # one text node longer than this is a wall of text
SPARSE_TEXT_DENSITY = 0.15        # below this the page is mostly whitespace
CLUTTERED_ELEMENT_COUNT = 300     # above this the DOM is "cluttered"
INFINITE_SCROLL_RATIO = 6.0       # page taller than 6 viewports reads as a feed

# Dealbreakers this module can actually observe. Every slug declared in
# persona.json must appear here — tests enforce the match so a persona can
# never declare a red flag that is silently ignored.
HANDLED_DEALBREAKERS = frozenset({
    "low_contrast_text",
    "large_blocks_of_text",
    "excessive_whitespace_padding",
    "cluttered_sidebar_layouts",
    "auto_playing_videos",
    "flashing_banner_animations",
    "infinite_scrolling_feeds",
    "pop_up_advertisements",
    "unskippable_onboarding_modals",
    "hidden_navigation",
})


# ---------------------------------------------------------------------------
# Persona loading
# ---------------------------------------------------------------------------
def load_all_personas(path: str | None = None) -> list[dict]:
    """Load all personas from the bundled persona.json file.

    If path is provided, load from that path instead.
    Otherwise, loads from persona.json next to this module.
    """
    if path is None:
        path = str(Path(__file__).parent / "persona.json")
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return data if isinstance(data, list) else [data]


def _slugify(name: str) -> str:
    """Convert a persona name like 'Gen-Z Tech Early Adopter' to 'gen_z' for matching."""
    return (
        name.lower()
        .replace("-", "_")
        .replace(" ", "_")
    )


def find_persona(personas: list[dict], name: str) -> dict:
    """Find a persona by slug or partial name match (case-insensitive).

    Matching order:
      1. Exact slug match (e.g. 'gen_z' matches 'Gen-Z Tech Early Adopter')
      2. Partial name match (e.g. 'elderly' matches 'Elderly Digital Novice')
    """
    name_lower = name.lower().strip()

    # 1. Exact slug match
    for p in personas:
        if name_lower == _slugify(p["name"]):
            return p

    # 2. Partial slug match (e.g. "gen_z" matches "gen_z_tech_early_adopter")
    for p in personas:
        if name_lower in _slugify(p["name"]):
            return p

    # 3. Partial name match
    for p in personas:
        if name_lower in p["name"].lower():
            return p

    available = [_slugify(p["name"]) for p in personas]
    raise ValueError(
        f"No persona matching '{name}'. "
        f"Available slugs: {available}"
    )


# ---------------------------------------------------------------------------
# Helper: parse "16px" → 16.0
# ---------------------------------------------------------------------------

def _px(value: str) -> float:
    return float(re.sub(r"[^\d.]", "", str(value)))


def _px_list(font_sizes: list[str]) -> list[float]:
    """Convert ['14px', '16px', ...] to [14.0, 16.0, ...]."""
    result = []
    for s in font_sizes:
        try:
            result.append(_px(s))
        except Exception:
            pass
    return result


def _as_float(value, default: float | None = None) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


# ---------------------------------------------------------------------------
# Individual scoring rules
# ---------------------------------------------------------------------------

def _score_dark_mode(props: UIProperties, prefs: dict) -> tuple[int, int, str | None]:
    """The colour-scheme dimension.

    Combines the dark/light match with measured WCAG contrast when the
    extractor supplied contrast ratios: 60% scheme match, 40% contrast
    compliance against the persona's ``min_contrast_ratio``. Properties
    without contrast data keep the original scheme-only behaviour.

    This dimension already penalises a scheme mismatch heavily, so personas
    do not also declare a ``light_mode_only_design`` dealbreaker — that would
    dock the same property twice.
    """
    scheme = prefs.get("color_scheme", "")
    wants_dark = "dark" in scheme
    wants_light = "light" in scheme
    is_dark = props.is_dark_mode

    if wants_dark:
        if is_dark:
            scheme_score, rec = 100, None
        else:
            scheme_score, rec = 20, (
                "This audience strongly prefers dark mode. "
                "Consider adding a dark theme or defaulting to one."
            )
    elif wants_light:
        if not is_dark:
            scheme_score, rec = 100, None
        else:
            scheme_score, rec = 20, (
                "This audience prefers light mode. "
                "The current dark background may reduce comfort."
            )
    else:
        # neutral / monochromatic — no strong preference
        scheme_score, rec = 70, None

    ratios = getattr(props, "contrast_ratios", None) or []
    min_ratio = _as_float(prefs.get("min_contrast_ratio"))

    if not ratios or min_ratio is None:
        return scheme_score, 100, rec

    failing = [r for r in ratios if r < min_ratio]
    compliance = 1 - (len(failing) / len(ratios))
    combined = round(0.6 * scheme_score + 0.4 * round(compliance * 100))

    notes = [rec] if rec else []
    if failing:
        pct = round(100 * len(failing) / len(ratios))
        notes.append(
            f"{pct}% of sampled text styles ({len(failing)}/{len(ratios)}) fall below "
            f"this audience's minimum contrast of {min_ratio:g}:1 "
            f"(worst {min(failing):g}:1). Increase text/background contrast."
        )

    return combined, 100, (" ".join(notes) if notes else None)


def _sized_weights(props: UIProperties) -> dict[float, int]:
    """Map font size in px to visible character count."""
    out: dict[float, int] = {}
    for size, chars in (getattr(props, "font_size_weights", None) or {}).items():
        try:
            px, count = _px(size), int(chars)
        except (TypeError, ValueError):
            continue
        if count > 0:
            out[px] = out.get(px, 0) + count
    return out


def _score_font_sizes(props: UIProperties, prefs: dict) -> tuple[int, int, str | None]:
    """Typography: text-weighted when font_size_weights is present."""
    weights = _sized_weights(props)
    sizes = list(weights) if weights else _px_list(props.font_sizes)
    if not sizes:
        return 50, 100, "Could not detect font sizes. Ensure text is rendered on the page."

    min_req = _px(prefs.get("min_font_size", "12px"))
    max_req = _px(prefs.get("max_font_size", "24px"))
    too_small = [s for s in sizes if s < min_req]
    too_large = [s for s in sizes if s > max_req]

    if weights:
        total = sum(weights.values())
        violating = sum(c for px, c in weights.items() if px < min_req or px > max_req)
        compliance = 1 - (violating / total)
    else:
        compliance = 1 - ((len(too_small) + len(too_large)) / len(sizes))
    score = round(compliance * 100)

    parts = []
    if too_small:
        parts.append(f"{len(too_small)} size(s) below {min_req:g}px (smallest {min(too_small):.0f}px)")
    if too_large:
        parts.append(f"{len(too_large)} size(s) above {max_req:g}px (largest {max(too_large):.0f}px)")
    rec = None
    if parts:
        if weights:
            outside = round(100 * (1 - compliance))
            rec = (f"Typography mismatch — {outside}% of visible text is outside "
                   f"{min_req:g}–{max_req:g}px. " + "; ".join(parts) + ".")
        else:
            rec = "Typography mismatch — " + "; ".join(parts) + "."

    return score, 100, rec


def _score_visual_density(props: UIProperties, prefs: dict) -> tuple[int, int, str | None]:
    density_pref = prefs.get("visual_density", "moderate")
    actual = props.text_density  # 0.0 – 1.0+

    # Map preference labels to target density ranges
    targets = {
        "very_low":  (0.0,  0.2),
        "low":       (0.1,  0.3),
        "moderate":  (0.25, 0.5),
        "high":      (0.4,  0.75),
    }
    low, high = targets.get(density_pref, (0.25, 0.5))

    if low <= actual <= high:
        return 100, 100, None

    if actual < low:
        score = max(20, round((actual / low) * 100))
        rec = (
            f"Content density ({actual:.0%}) is too sparse for this audience "
            f"who prefers denser layouts ({density_pref}). Add more content or reduce whitespace."
        )
    else:
        score = max(20, round((high / actual) * 100))
        rec = (
            f"Content density ({actual:.0%}) is too high for this audience "
            f"who prefers {density_pref} layouts. Add breathing room and whitespace."
        )

    return score, 100, rec


def _score_animations(props: UIProperties, prefs: dict) -> tuple[int, int, str | None]:
    wants_animations = prefs.get("prefers_animations", True)
    has = props.has_animations

    if wants_animations == has:
        return 100, 100, None
    if wants_animations and not has:
        return 40, 100, (
            "This audience enjoys motion and animations. "
            "Consider adding subtle transitions or micro-interactions."
        )
    # doesn't want animations but has them
    return 40, 100, (
        "This audience prefers distraction-free, static interfaces. "
        "Reduce or disable animations/transitions."
    )


def _score_interactivity(props: UIProperties, prefs: dict) -> tuple[int, int, str | None]:
    """
    How many things the user can act on (buttons + links + form controls)
    compared with the interface complexity this audience expects.

    Uses its own ``interaction_density`` preference, falling back to
    ``visual_density`` for personas that do not declare one, so a single
    preference does not silently drive two dimensions.
    """
    density_pref = prefs.get("interaction_density") or prefs.get("visual_density", "moderate")
    total_interactive = props.buttons_count + props.links_count + props.inputs_count

    if density_pref in ("high",):
        # Expect at least 10 interactive elements
        score = min(100, round((total_interactive / 10) * 100))
        rec = (
            f"Only {total_interactive} interactive elements found. "
            "This audience expects feature-rich, action-dense interfaces."
        ) if total_interactive < 10 else None
    elif density_pref in ("very_low", "low"):
        # Penalise clutter — more than 20 interactive elements is noisy
        if total_interactive <= 20:
            score = 100
            rec = None
        else:
            score = max(30, round((20 / total_interactive) * 100))
            rec = (
                f"{total_interactive} interactive elements may overwhelm this audience. "
                "Simplify the interface."
            )
    else:
        score = 80  # neutral
        rec = None

    return score, 100, rec


def _check_dealbreakers(
    props: UIProperties,
    dealbreakers: list[str],
    prefs: dict | None = None,
) -> list[str]:
    """
    Map dealbreaker strings from the persona JSON to observable properties.
    Returns a list of triggered dealbreaker messages.

    Every slug handled here is listed in HANDLED_DEALBREAKERS; anything else
    is ignored. Signals the DOM/CSS cannot observe are deliberately absent
    from persona.json rather than declared and skipped.
    """
    triggered = []
    db_set = set(dealbreakers)
    prefs = prefs or {}

    if "low_contrast_text" in db_set:
        ratios = getattr(props, "contrast_ratios", None) or []
        min_ratio = _as_float(prefs.get("min_contrast_ratio"), 4.5)
        failing = [r for r in ratios if r < min_ratio]
        if failing:
            triggered.append(
                f"low_contrast_text — {len(failing)}/{len(ratios)} sampled text styles "
                f"below {min_ratio:g}:1 (worst {min(failing):g}:1)"
            )

    if "large_blocks_of_text" in db_set and props.longest_text_block >= LARGE_TEXT_BLOCK_CHARS:
        triggered.append(
            f"large_blocks_of_text — a single text block runs "
            f"{props.longest_text_block} characters"
        )

    if "excessive_whitespace_padding" in db_set and props.text_density < SPARSE_TEXT_DENSITY:
        triggered.append(
            f"excessive_whitespace_padding — text density is only {props.text_density:.0%}"
        )

    if "cluttered_sidebar_layouts" in db_set and props.total_elements > CLUTTERED_ELEMENT_COUNT:
        triggered.append(
            f"cluttered_sidebar_layouts — {props.total_elements} DOM elements "
            "suggests high complexity"
        )

    if "auto_playing_videos" in db_set and props.autoplay_media > 0:
        triggered.append(
            f"auto_playing_videos — {props.autoplay_media} autoplaying media element(s)"
        )

    if "flashing_banner_animations" in db_set and props.keyframe_animations > 0:
        triggered.append(
            f"flashing_banner_animations — {props.keyframe_animations} element(s) run "
            "keyframe animations; verify none flash or strobe"
        )

    if "infinite_scrolling_feeds" in db_set and props.scroll_depth_ratio >= INFINITE_SCROLL_RATIO:
        triggered.append(
            f"infinite_scrolling_feeds — page is {props.scroll_depth_ratio:.1f}x "
            "the viewport height"
        )

    if "pop_up_advertisements" in db_set and props.blocking_overlay:
        triggered.append(
            "pop_up_advertisements — a fixed overlay covers at least half the viewport on load"
        )

    if "unskippable_onboarding_modals" in db_set and props.blocking_overlay:
        triggered.append(
            "unskippable_onboarding_modals — a fixed overlay covers at least half "
            "the viewport on load"
        )

    if "hidden_navigation" in db_set and props.hidden_navigation:
        triggered.append(
            "hidden_navigation — navigation is collapsed behind a toggle at desktop width"
        )

    return triggered


# ---------------------------------------------------------------------------
# Main scoring function
# ---------------------------------------------------------------------------

def score(props: UIProperties, persona: dict) -> dict:
    """
    Score UIProperties against a persona.

    Returns:
        {
          "persona_name": str,
          "overall_score": int,          # 0–100
          "grade": str,                  # A / B / C / D / F
          "breakdown": {
              "dark_mode":      int,
              "typography":     int,
              "visual_density": int,
              "animations":     int,
              "interactivity":  int,
          },
          "recommendations": [str, ...],
          "dealbreakers_triggered": [str, ...],
        }

    ── HOW TO REPLACE WITH ML ──────────────────────────────────────────────
    1. Collect (UIProperties, persona, human_score) training pairs.
    2. Convert UIProperties → numeric feature vector:
           features = [
               1 if props.is_dark_mode else 0,
               props.text_density,
               props.buttons_count / 100,
               props.links_count / 100,
               min(px_sizes) if px_sizes else 0,
               max(px_sizes) if px_sizes else 0,
               1 if props.has_animations else 0,
               props.total_elements / 500,
               props.max_dom_depth / 30,
           ]
    3. Train a model: sklearn RandomForest or a small PyTorch MLP.
    4. Replace each _score_*() call below with model.predict([features]).
    5. The rest of this function, the CLI, and the reporter stay the same.
    ────────────────────────────────────────────────────────────────────────
    """
    prefs = persona.get("preferences", {})
    dealbreakers = persona.get("dealbreakers", [])

    # Run all rules
    checks = {
        "dark_mode":      _score_dark_mode(props, prefs),
        "typography":     _score_font_sizes(props, prefs),
        "visual_density": _score_visual_density(props, prefs),
        "animations":     _score_animations(props, prefs),
        "interactivity":  _score_interactivity(props, prefs),
    }

    breakdown = {}
    recommendations = []
    total_score = total_max = 0

    for key, (earned, maximum, rec) in checks.items():
        breakdown[key] = earned
        total_score += earned
        total_max   += maximum
        if rec:
            recommendations.append(rec)

    overall = round((total_score / total_max) * 100) if total_max else 0

    # Dealbreaker penalty — each triggered one docks 5 points
    db_triggered = _check_dealbreakers(props, dealbreakers, prefs)
    penalty = len(db_triggered) * 5
    overall = max(0, overall - penalty)

    grade = (
        "A" if overall >= 85 else
        "B" if overall >= 70 else
        "C" if overall >= 55 else
        "D" if overall >= 40 else
        "F"
    )

    return {
        "persona_name":          persona["name"],
        "overall_score":         overall,
        "grade":                 grade,
        "breakdown":             breakdown,
        "recommendations":       recommendations,
        "dealbreakers_triggered": db_triggered,
    }
