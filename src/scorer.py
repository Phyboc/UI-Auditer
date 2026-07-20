"""
scorer.py
---------
Rule-based heuristic engine. Compares UIProperties against a persona JSON
and returns structured scores + recommendations.

"""

import json
import re
from pathlib import Path
from extractor import UIProperties


# ---------------------------------------------------------------------------
# Persona loading
# ---------------------------------------------------------------------------

def load_persona(name_or_path: str) -> dict:
    """
    Load a persona by slug name (e.g. 'gen_z') or direct file path.
    Supports both a single-persona JSON and an array of personas.
    """
    p = Path(name_or_path)
    if not p.exists():
        # Try personas/ directory
        p = Path("personas") / f"{name_or_path}.json"
    if not p.exists():
        raise FileNotFoundError(f"Persona not found: {name_or_path}")

    data = json.loads(p.read_text(encoding="utf-8"))

    # Support array format (your current file) or single object
    if isinstance(data, list):
        return data[0]  # default: first persona
    return data


def load_all_personas(path: str = "personas/personas.json") -> list[dict]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return data if isinstance(data, list) else [data]


def find_persona(personas: list[dict], name: str) -> dict:
    """Find a persona by partial name match (case-insensitive)."""
    name_lower = name.lower()
    for p in personas:
        if name_lower in p["name"].lower():
            return p
    raise ValueError(
        f"No persona matching '{name}'. "
        f"Available: {[p['name'] for p in personas]}"
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


# ---------------------------------------------------------------------------
# Individual scoring rules
# ---------------------------------------------------------------------------

def _score_dark_mode(props: UIProperties, prefs: dict) -> tuple[int, int, str | None]:
    """Returns (score_earned, max_score, recommendation_or_None)"""
    scheme = prefs.get("color_scheme", "")
    wants_dark = "dark" in scheme
    wants_light = "light" in scheme
    is_dark = props.is_dark_mode

    if wants_dark:
        if is_dark:
            return 100, 100, None
        return 20, 100, (
            "This audience strongly prefers dark mode. "
            "Consider adding a dark theme or defaulting to one."
        )
    if wants_light:
        if not is_dark:
            return 100, 100, None
        return 20, 100, (
            "This audience prefers light mode. "
            "The current dark background may reduce comfort."
        )
    # neutral / monochromatic — no strong preference
    return 70, 100, None


def _score_font_sizes(props: UIProperties, prefs: dict) -> tuple[int, int, str | None]:
    sizes = _px_list(props.font_sizes)
    if not sizes:
        return 50, 100, "Could not detect font sizes. Ensure text is rendered on the page."

    min_req = _px(prefs.get("min_font_size", "12px"))
    max_req = _px(prefs.get("max_font_size", "24px"))

    too_small = [s for s in sizes if s < min_req]
    too_large = [s for s in sizes if s > max_req]

    violations = len(too_small) + len(too_large)
    compliance = 1 - (violations / len(sizes))
    score = round(compliance * 100)

    rec = None
    parts = []
    if too_small:
        parts.append(
            f"{len(too_small)} text element(s) below {min_req}px "
            f"(smallest: {min(too_small):.0f}px)"
        )
    if too_large:
        parts.append(
            f"{len(too_large)} text element(s) above {max_req}px "
            f"(largest: {max(too_large):.0f}px)"
        )
    if parts:
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
    Higher interactivity (more buttons/links) scores well for high-density personas.
    Lower interactivity scores well for minimalist/low-density personas.
    """
    density_pref = prefs.get("visual_density", "moderate")
    total_interactive = props.buttons_count + props.links_count

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


def _check_dealbreakers(props: UIProperties, dealbreakers: list[str]) -> list[str]:
    """
    Map dealbreaker strings from the persona JSON to observable properties.
    Returns a list of triggered dealbreaker messages.
    """
    triggered = []
    db_set = set(dealbreakers)

    if "light_mode_only_design" in db_set and not props.is_dark_mode:
        triggered.append("light_mode_only_design — page uses light background")

    if "low_contrast_text" in db_set and len(props.colors) < 3:
        triggered.append("low_contrast_text — very few colors detected, contrast may be poor")

    if "excessive_whitespace_padding" in db_set and props.text_density < 0.15:
        triggered.append(
            f"excessive_whitespace_padding — text density is only {props.text_density:.0%}"
        )

    if "auto_playing_videos" in db_set and props.has_animations:
        triggered.append("has_animations — check for auto-playing video or motion")

    if "flashing_banner_animations" in db_set and props.has_animations:
        triggered.append("has_animations — verify no flashing/strobing elements exist")

    if "cluttered_sidebar_layouts" in db_set and props.total_elements > 300:
        triggered.append(
            f"cluttered_sidebar_layouts — {props.total_elements} DOM elements suggests high complexity"
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
    db_triggered = _check_dealbreakers(props, dealbreakers)
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