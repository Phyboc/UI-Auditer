"""Tests for src.scorer — persona loading, slug matching, and scoring functions."""

import json
from pathlib import Path
from src.extractor import UIProperties
from src.scorer import (
    load_all_personas,
    find_persona,
    _slugify,
    _px,
    _px_list,
    _score_dark_mode,
    _score_font_sizes,
    _score_visual_density,
    _score_animations,
    _score_interactivity,
    _check_dealbreakers,
    score,
)


# ---------------------------------------------------------------------------
# Persona loading
# ---------------------------------------------------------------------------

class TestLoadAllPersonas:
    def test_loads_all_five_personas(self):
        personas = load_all_personas()
        assert len(personas) == 5

    def test_loads_from_explicit_path(self):
        persona_path = str(Path(__file__).resolve().parent.parent / "src" / "persona.json")
        personas = load_all_personas(persona_path)
        assert len(personas) == 5

    def test_each_persona_has_required_fields(self):
        personas = load_all_personas()
        for p in personas:
            assert "name" in p
            assert "preferences" in p
            assert "dealbreakers" in p

    def test_nonexistent_path_raises(self):
        import pytest
        with pytest.raises(FileNotFoundError):
            load_all_personas("/nonexistent/path.json")


# ---------------------------------------------------------------------------
# Slug matching
# ---------------------------------------------------------------------------

class TestSlugify:
    def test_simple_name(self):
        assert _slugify("Elderly Digital Novice") == "elderly_digital_novice"

    def test_hyphenated_name(self):
        assert _slugify("Gen-Z Tech Early Adopter") == "gen_z_tech_early_adopter"

    def test_all_lowercase(self):
        assert _slugify("Corporate Power User") == "corporate_power_user"


class TestFindPersona:
    def test_exact_slug_match(self):
        personas = load_all_personas()
        result = find_persona(personas, "gen_z")
        assert result["name"] == "Gen-Z Tech Early Adopter"

    def test_exact_slug_match_elderly(self):
        personas = load_all_personas()
        result = find_persona(personas, "elderly_digital_novice")
        assert result["name"] == "Elderly Digital Novice"

    def test_partial_name_match(self):
        personas = load_all_personas()
        result = find_persona(personas, "elderly")
        assert result["name"] == "Elderly Digital Novice"

    def test_case_insensitive(self):
        personas = load_all_personas()
        result = find_persona(personas, "CORPORATE")
        assert result["name"] == "Corporate Power User"

    def test_no_match_raises(self):
        import pytest
        personas = load_all_personas()
        with pytest.raises(ValueError, match="No persona matching"):
            find_persona(personas, "nonexistent")


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

class TestPx:
    def test_parse_px(self):
        assert _px("16px") == 16.0

    def test_parse_rem(self):
        assert _px("1.5rem") == 1.5

    def test_parse_bare_number(self):
        assert _px("24") == 24.0


class TestPxList:
    def test_normal_sizes(self):
        assert _px_list(["12px", "14px", "16px"]) == [12.0, 14.0, 16.0]

    def test_empty_list(self):
        assert _px_list([]) == []

    def test_invalid_values_skipped(self):
        result = _px_list(["12px", "invalid", "16px"])
        assert result == [12.0, 16.0]


# ---------------------------------------------------------------------------
# Dark mode scoring
# ---------------------------------------------------------------------------

class TestScoreDarkMode:
    def test_dark_page_with_dark_persona(self, dark_page_props, gen_z_persona):
        prefs = gen_z_persona["preferences"]
        earned, maximum, rec = _score_dark_mode(dark_page_props, prefs)
        assert earned == 100
        assert rec is None

    def test_light_page_with_dark_persona(self, light_page_props, gen_z_persona):
        prefs = gen_z_persona["preferences"]
        earned, maximum, rec = _score_dark_mode(light_page_props, prefs)
        assert earned == 20
        assert rec is not None
        assert "dark mode" in rec.lower()

    def test_light_page_with_light_persona(self, light_page_props, elderly_persona):
        prefs = elderly_persona["preferences"]
        earned, maximum, rec = _score_dark_mode(light_page_props, prefs)
        assert earned == 100
        assert rec is None

    def test_dark_page_with_light_persona(self, dark_page_props, elderly_persona):
        prefs = elderly_persona["preferences"]
        earned, maximum, rec = _score_dark_mode(dark_page_props, prefs)
        assert earned == 20
        assert rec is not None

    def test_neutral_scheme_scores_70(self, dark_page_props):
        prefs = {"color_scheme": "neutral_system_default"}
        earned, maximum, rec = _score_dark_mode(dark_page_props, prefs)
        assert earned == 70


# ---------------------------------------------------------------------------
# Typography scoring
# ---------------------------------------------------------------------------

class TestScoreFontSizes:
    def test_sizes_in_range(self, dark_page_props, gen_z_persona):
        prefs = gen_z_persona["preferences"]
        earned, maximum, rec = _score_font_sizes(dark_page_props, prefs)
        # 12px, 14px, 16px — all within 12–16 range
        assert earned == 100
        assert rec is None

    def test_sizes_out_of_range(self, light_page_props, gen_z_persona):
        prefs = gen_z_persona["preferences"]
        earned, maximum, rec = _score_font_sizes(light_page_props, prefs)
        # 14px, 16px, 18px, 22px — 18 and 22 exceed 16px max
        assert earned < 100
        assert rec is not None

    def test_empty_sizes_returns_50(self):
        props = UIProperties(url="https://example.com", font_sizes=[])
        prefs = {"min_font_size": "12px", "max_font_size": "16px"}
        earned, _, rec = _score_font_sizes(props, prefs)
        assert earned == 50
        assert rec is not None


# ---------------------------------------------------------------------------
# Visual density scoring
# ---------------------------------------------------------------------------

class TestScoreVisualDensity:
    def test_density_in_range(self, dark_page_props):
        prefs = {"visual_density": "high"}
        earned, _, rec = _score_visual_density(dark_page_props, prefs)
        # text_density=0.45 is in high range (0.4–0.75)
        assert earned == 100

    def test_density_too_sparse(self):
        props = UIProperties(url="https://example.com", text_density=0.05)
        prefs = {"visual_density": "moderate"}
        earned, _, rec = _score_visual_density(props, prefs)
        assert earned < 100
        assert rec is not None
        assert "sparse" in rec.lower() or "density" in rec.lower()

    def test_density_too_high(self):
        props = UIProperties(url="https://example.com", text_density=0.9)
        prefs = {"visual_density": "very_low"}
        earned, _, rec = _score_visual_density(props, prefs)
        assert earned < 100
        assert rec is not None


# ---------------------------------------------------------------------------
# Animation scoring
# ---------------------------------------------------------------------------

class TestScoreAnimations:
    def test_wants_and_has(self, dark_page_props, gen_z_persona):
        prefs = gen_z_persona["preferences"]
        earned, _, rec = _score_animations(dark_page_props, prefs)
        assert earned == 100

    def test_wants_but_doesnt_have(self, light_page_props, minimalist_persona):
        # Minimalist wants animations but light_page_props has none... wait
        # light_page_props.has_animations = False, minimalist wants True
        prefs = minimalist_persona["preferences"]
        earned, _, rec = _score_animations(light_page_props, prefs)
        assert earned == 40
        assert rec is not None

    def test_doesnt_want_and_has(self, dark_page_props, elderly_persona):
        prefs = elderly_persona["preferences"]
        earned, _, rec = _score_animations(dark_page_props, prefs)
        assert earned == 40
        assert "motion" in rec.lower() or "animation" in rec.lower()

    def test_doesnt_want_and_doesnt_have(self, light_page_props, elderly_persona):
        prefs = elderly_persona["preferences"]
        earned, _, rec = _score_animations(light_page_props, prefs)
        assert earned == 100


# ---------------------------------------------------------------------------
# Interactivity scoring
# ---------------------------------------------------------------------------

class TestScoreInteractivity:
    def test_high_density_enough_elements(self):
        props = UIProperties(url="https://example.com", buttons_count=20, links_count=50)
        prefs = {"visual_density": "high"}
        earned, _, rec = _score_interactivity(props, prefs)
        assert earned == 100

    def test_high_density_too_few(self):
        props = UIProperties(url="https://example.com", buttons_count=2, links_count=3)
        prefs = {"visual_density": "high"}
        earned, _, rec = _score_interactivity(props, prefs)
        assert earned < 100
        assert rec is not None

    def test_low_density_clean(self):
        props = UIProperties(url="https://example.com", buttons_count=3, links_count=5)
        prefs = {"visual_density": "very_low"}
        earned, _, _ = _score_interactivity(props, prefs)
        assert earned == 100

    def test_low_density_cluttered(self):
        props = UIProperties(url="https://example.com", buttons_count=15, links_count=20)
        prefs = {"visual_density": "low"}
        earned, _, rec = _score_interactivity(props, prefs)
        assert earned < 100
        assert rec is not None

    def test_neutral_density(self):
        props = UIProperties(url="https://example.com", buttons_count=10, links_count=10)
        prefs = {"visual_density": "moderate"}
        earned, _, _ = _score_interactivity(props, prefs)
        assert earned == 80


# ---------------------------------------------------------------------------
# Dealbreakers
# ---------------------------------------------------------------------------

class TestCheckDealbreakers:
    def test_light_mode_triggered(self):
        props = UIProperties(url="https://example.com", is_dark_mode=False)
        triggered = _check_dealbreakers(props, ["light_mode_only_design"])
        assert len(triggered) == 1
        assert "light_mode" in triggered[0]

    def test_light_mode_not_triggered_when_dark(self):
        props = UIProperties(url="https://example.com", is_dark_mode=True)
        triggered = _check_dealbreakers(props, ["light_mode_only_design"])
        assert len(triggered) == 0

    def test_cluttered_layout_triggered(self):
        props = UIProperties(url="https://example.com", total_elements=500)
        triggered = _check_dealbreakers(props, ["cluttered_sidebar_layouts"])
        assert len(triggered) == 1

    def test_no_dealbreakers_returns_empty(self):
        props = UIProperties(url="https://example.com")
        triggered = _check_dealbreakers(props, [])
        assert triggered == []

    def test_unknown_dealbreaker_ignored(self):
        props = UIProperties(url="https://example.com")
        triggered = _check_dealbreakers(props, ["some_future_dealbreaker"])
        assert triggered == []


# ---------------------------------------------------------------------------
# Full scoring pipeline
# ---------------------------------------------------------------------------

class TestScore:
    def test_returns_expected_keys(self, dark_page_props, gen_z_persona):
        result = score(dark_page_props, gen_z_persona)
        assert "persona_name" in result
        assert "overall_score" in result
        assert "grade" in result
        assert "breakdown" in result
        assert "recommendations" in result
        assert "dealbreakers_triggered" in result

    def test_score_is_0_to_100(self, dark_page_props, gen_z_persona):
        result = score(dark_page_props, gen_z_persona)
        assert 0 <= result["overall_score"] <= 100

    def test_grade_matches_score(self, dark_page_props, gen_z_persona):
        result = score(dark_page_props, gen_z_persona)
        s = result["overall_score"]
        g = result["grade"]
        if s >= 85:
            assert g == "A"
        elif s >= 70:
            assert g == "B"
        elif s >= 55:
            assert g == "C"
        elif s >= 40:
            assert g == "D"
        else:
            assert g == "F"

    def test_breakdown_has_five_dimensions(self, dark_page_props, gen_z_persona):
        result = score(dark_page_props, gen_z_persona)
        expected_keys = {"dark_mode", "typography", "visual_density", "animations", "interactivity"}
        assert set(result["breakdown"].keys()) == expected_keys

    def test_dealbreaker_reduces_score(self, elderly_persona):
        # Light page triggers elderly's dealbreakers (low_contrast_text with only 2 colors)
        props = UIProperties(
            url="https://example.com",
            is_dark_mode=False,
            has_animations=True,  # triggers auto_playing_videos
            colors=["rgb(0,0,0)", "rgb(255,255,255)"],  # only 2 colors
            text_density=0.1,  # below 0.15
        )
        result = score(props, elderly_persona)
        assert len(result["dealbreakers_triggered"]) >= 1
        # Score should be penalized
        assert result["overall_score"] < 85

    def test_dark_site_scores_high_for_gen_z(self, dark_page_props, gen_z_persona):
        result = score(dark_page_props, gen_z_persona)
        assert result["overall_score"] >= 70
