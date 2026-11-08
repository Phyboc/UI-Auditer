"""Tests for ui_auditer.scorer — persona loading, slug matching, and scoring functions."""

from pathlib import Path

from pytest import approx

from ui_auditer.extractor import UIProperties
from ui_auditer.scorer import (
    HANDLED_DEALBREAKERS,
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
    is_large_text,
    required_contrast,
    score,
)


# ---------------------------------------------------------------------------
# WCAG large-text exception
# ---------------------------------------------------------------------------

class TestLargeTextException:
    def test_24px_is_large(self):
        assert is_large_text(24.0) is True

    def test_body_text_is_not_large(self):
        assert is_large_text(16.0) is False

    def test_bold_19px_is_large(self):
        assert is_large_text(19.0, bold=True) is True

    def test_bold_16px_is_not_large(self):
        assert is_large_text(16.0, bold=True) is False

    def test_unknown_size_is_treated_as_body_text(self):
        assert is_large_text(None) is False

    def test_required_ratio_relaxes_by_two_thirds(self):
        assert required_contrast(4.5, 32.0) == approx(3.0, abs=1e-6)
        assert required_contrast(4.5, 16.0) == 4.5

    def test_elderly_floor_scales_too(self):
        assert required_contrast(7.0, 30.0) == approx(4.667, abs=0.01)

    def test_large_heading_at_three_to_one_passes(self):
        props = UIProperties(url="https://example.com", contrast_samples=[
            {"ratio": 3.03, "font_size_px": 32.0, "bold": False},
            {"ratio": 12.0, "font_size_px": 16.0, "bold": False},
        ])
        triggered = _check_dealbreakers(
            props, ["low_contrast_text"], {"min_contrast_ratio": 4.5}
        )
        assert triggered == []

    def test_same_ratio_at_body_size_fails(self):
        props = UIProperties(url="https://example.com", contrast_samples=[
            {"ratio": 3.03, "font_size_px": 16.0, "bold": False},
        ])
        triggered = _check_dealbreakers(
            props, ["low_contrast_text"], {"min_contrast_ratio": 4.5}
        )
        assert len(triggered) == 1

    def test_dealbreaker_names_the_failing_element(self):
        props = UIProperties(url="https://example.com", contrast_samples=[
            {"ratio": 2.5, "font_size_px": 16.0, "bold": False, "targets": ["p.low"]},
        ])
        triggered = _check_dealbreakers(
            props, ["low_contrast_text"], {"min_contrast_ratio": 4.5}
        )
        assert "at p.low" in triggered[0]

    def test_dimension_scores_the_relaxed_style_as_passing(self):
        props = UIProperties(
            url="https://example.com",
            is_dark_mode=False,
            contrast_samples=[
                {"ratio": 3.03, "font_size_px": 32.0, "bold": False},
                {"ratio": 12.0, "font_size_px": 16.0, "bold": False},
            ],
        )
        value, _, rec = _score_dark_mode(
            props, {"color_scheme": "light_mode_preferred", "min_contrast_ratio": 4.5}
        )
        assert value == 100
        assert rec is None

    def test_dimension_still_docks_a_body_text_failure(self):
        props = UIProperties(
            url="https://example.com",
            is_dark_mode=False,
            contrast_samples=[
                {"ratio": 3.03, "font_size_px": 32.0, "bold": False},
                {"ratio": 2.5, "font_size_px": 16.0, "bold": False},
            ],
        )
        value, _, rec = _score_dark_mode(
            props, {"color_scheme": "light_mode_preferred", "min_contrast_ratio": 4.5}
        )
        assert value == 80
        assert rec is not None and "large-text exception" in rec

    def test_contrast_samples_keep_typography(self):
        from ui_auditer.contrast import contrast_samples_from_pairs

        samples = contrast_samples_from_pairs([["#000000", "#ffffff", 32, False]])
        assert samples == [{"ratio": 21.0, "font_size_px": 32.0, "bold": False}]


# ---------------------------------------------------------------------------
# Persona loading
# ---------------------------------------------------------------------------

class TestLoadAllPersonas:
    def test_loads_all_five_personas(self):
        personas = load_all_personas()
        assert len(personas) == 5

    def test_loads_from_explicit_path(self):
        persona_path = str(Path(__file__).resolve().parent.parent / "ui_auditer" / "persona.json")
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

class TestScoreFontSizesWeighted:
    def test_compliance_is_weighted_by_characters(self, elderly_persona):
        props = UIProperties(url="https://e.com", font_sizes=["10px", "18px"],
                             font_size_weights={"10px": 5, "18px": 95})
        earned, _, rec = _score_font_sizes(props, elderly_persona["preferences"])
        assert earned == 95
        assert rec is not None and "5%" in rec

    def test_without_weights_keeps_distinct_size_behaviour(self, light_page_props, gen_z_persona):
        earned, _, _ = _score_font_sizes(light_page_props, gen_z_persona["preferences"])
        assert earned == 50


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
    def test_scheme_mismatch_is_not_a_duplicate_dealbreaker(self):
        # The colour-scheme dimension already penalises a light page for a
        # dark-mode persona; a separate dealbreaker would charge it twice.
        props = UIProperties(url="https://example.com", is_dark_mode=False)
        assert _check_dealbreakers(props, ["light_mode_only_design"]) == []

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


class TestContrastDealbreaker:
    def test_low_contrast_uses_measured_ratio(self):
        props = UIProperties(url="https://example.com", contrast_ratios=[2.1, 2.6, 8.0])
        triggered = _check_dealbreakers(
            props, ["low_contrast_text"], {"min_contrast_ratio": 4.5}
        )
        assert len(triggered) == 1
        assert "2/3" in triggered[0]
        assert "2.1" in triggered[0]

    def test_few_colors_alone_no_longer_triggers(self):
        props = UIProperties(
            url="https://example.com",
            colors=["rgb(0,0,0)"],
            contrast_ratios=[14.0],
        )
        assert _check_dealbreakers(props, ["low_contrast_text"]) == []

    def test_persona_min_ratio_is_respected(self):
        props = UIProperties(url="https://example.com", contrast_ratios=[4.8])
        assert _check_dealbreakers(
            props, ["low_contrast_text"], {"min_contrast_ratio": 7.0}
        )
        assert not _check_dealbreakers(
            props, ["low_contrast_text"], {"min_contrast_ratio": 4.5}
        )


class TestColorSchemeContrast:
    def test_without_contrast_data_scheme_score_is_unchanged(
        self, dark_page_props, gen_z_persona
    ):
        earned, _, rec = _score_dark_mode(dark_page_props, gen_z_persona["preferences"])
        assert earned == 100
        assert rec is None

    def test_failing_contrast_lowers_the_dimension(self, gen_z_persona):
        props = UIProperties(
            url="https://example.com", is_dark_mode=True, contrast_ratios=[2.0, 2.5]
        )
        prefs = {**gen_z_persona["preferences"], "min_contrast_ratio": 4.5}
        earned, _, rec = _score_dark_mode(props, prefs)
        assert earned == 60
        assert rec is not None and "contrast" in rec.lower()

    def test_passing_contrast_keeps_full_marks(self, gen_z_persona):
        props = UIProperties(
            url="https://example.com", is_dark_mode=True, contrast_ratios=[7.0, 12.0]
        )
        prefs = {**gen_z_persona["preferences"], "min_contrast_ratio": 4.5}
        earned, _, rec = _score_dark_mode(props, prefs)
        assert earned == 100
        assert rec is None


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
        # Light page with genuinely failing contrast triggers low_contrast_text
        props = UIProperties(
            url="https://example.com",
            is_dark_mode=False,
            autoplay_media=1,  # triggers auto_playing_videos
            contrast_ratios=[2.1, 2.6],  # both below elderly's 4.5:1 floor
            text_density=0.1,  # below 0.15
        )
        result = score(props, elderly_persona)
        assert len(result["dealbreakers_triggered"]) >= 1
        # Score should be penalized
        assert result["overall_score"] < 85

    def test_dark_site_scores_high_for_gen_z(self, dark_page_props, gen_z_persona):
        result = score(dark_page_props, gen_z_persona)
        assert result["overall_score"] >= 70


# ---------------------------------------------------------------------------
# Dealbreaker coverage and the new observable signals
# ---------------------------------------------------------------------------

class TestDealbreakerCoverage:
    def test_every_declared_dealbreaker_is_handled(self):
        declared = {d for p in load_all_personas() for d in p["dealbreakers"]}
        assert declared <= HANDLED_DEALBREAKERS

    def test_no_persona_duplicates_the_scheme_rule(self):
        for p in load_all_personas():
            assert "light_mode_only_design" not in p["dealbreakers"]


class TestNewDealbreakerSignals:
    def test_large_text_block(self):
        props = UIProperties(url="https://e.com", longest_text_block=1200)
        triggered = _check_dealbreakers(props, ["large_blocks_of_text"])
        assert len(triggered) == 1 and "1200" in triggered[0]

    def test_normal_text_block_is_fine(self):
        props = UIProperties(url="https://e.com", longest_text_block=200)
        assert _check_dealbreakers(props, ["large_blocks_of_text"]) == []

    def test_autoplay_media(self):
        props = UIProperties(url="https://e.com", autoplay_media=2)
        assert len(_check_dealbreakers(props, ["auto_playing_videos"])) == 1

    def test_css_motion_alone_is_not_autoplay(self):
        props = UIProperties(url="https://e.com", has_animations=True, autoplay_media=0)
        assert _check_dealbreakers(props, ["auto_playing_videos"]) == []

    def test_infinite_scroll(self):
        props = UIProperties(url="https://e.com", scroll_depth_ratio=9.5)
        assert len(_check_dealbreakers(props, ["infinite_scrolling_feeds"])) == 1

    def test_short_page_is_not_a_feed(self):
        props = UIProperties(url="https://e.com", scroll_depth_ratio=2.0)
        assert _check_dealbreakers(props, ["infinite_scrolling_feeds"]) == []

    def test_blocking_overlay_triggers_popup(self):
        props = UIProperties(url="https://e.com", blocking_overlay=True)
        assert len(_check_dealbreakers(props, ["pop_up_advertisements"])) == 1

    def test_blocking_overlay_triggers_onboarding_modal(self):
        props = UIProperties(url="https://e.com", blocking_overlay=True)
        assert len(_check_dealbreakers(props, ["unskippable_onboarding_modals"])) == 1

    def test_hidden_navigation(self):
        props = UIProperties(url="https://e.com", hidden_navigation=True)
        assert len(_check_dealbreakers(props, ["hidden_navigation"])) == 1

    def test_flashing_banner_uses_keyframes_only(self):
        props = UIProperties(url="https://e.com", has_animations=True, keyframe_animations=0)
        assert _check_dealbreakers(props, ["flashing_banner_animations"]) == []


class TestInteractivitySignals:
    def test_form_controls_count_as_interactive(self):
        props = UIProperties(url="https://e.com", buttons_count=1, links_count=1, inputs_count=8)
        earned, _, _ = _score_interactivity(props, {"interaction_density": "high"})
        assert earned == 100

    def test_interaction_density_overrides_visual_density(self):
        props = UIProperties(url="https://e.com", buttons_count=2, links_count=2)
        earned, _, _ = _score_interactivity(
            props, {"visual_density": "very_low", "interaction_density": "high"}
        )
        assert earned == 40

    def test_falls_back_to_visual_density(self):
        props = UIProperties(url="https://e.com", buttons_count=2, links_count=3)
        earned, _, _ = _score_interactivity(props, {"visual_density": "high"})
        assert earned == 50
