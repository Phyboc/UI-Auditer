"""Tests for src.advisor — LLM response parsing and fallback suggestions."""

import pytest
from src.advisor import _parse_json, _build_fallback_suggestions
from src.extractor import UIProperties


class TestParseJson:
    def test_raw_json(self):
        raw = '{"summary": "test", "css_fixes": [], "non_css_suggestions": []}'
        result = _parse_json(raw)
        assert result["summary"] == "test"

    def test_json_in_code_block(self):
        raw = '```json\n{"summary": "test", "css_fixes": [], "non_css_suggestions": []}\n```'
        result = _parse_json(raw)
        assert result["summary"] == "test"

    def test_json_in_plain_code_block(self):
        raw = '```\n{"summary": "test", "css_fixes": [], "non_css_suggestions": []}\n```'
        result = _parse_json(raw)
        assert result["summary"] == "test"

    def test_json_with_text_before(self):
        raw = 'Here are the fixes:\n```json\n{"summary": "biggest issue", "css_fixes": [], "non_css_suggestions": []}\n```'
        result = _parse_json(raw)
        assert result["summary"] == "biggest issue"

    def test_json_with_text_before_and_after(self):
        raw = 'Here are the fixes:\n```json\n{"summary": "issue", "css_fixes": [], "non_css_suggestions": []}\n```\nLet me know if you need more.'
        result = _parse_json(raw)
        assert result["summary"] == "issue"

    def test_json_with_think_tags(self):
        raw = '<think>Let me analyze this...</think>{"summary": "test", "css_fixes": [], "non_css_suggestions": []}'
        result = _parse_json(raw)
        assert result["summary"] == "test"

    def test_json_with_think_and_code_block(self):
        raw = '<think>Analyzing the UI...</think>```json\n{"summary": "found it", "css_fixes": [], "non_css_suggestions": []}\n```'
        result = _parse_json(raw)
        assert result["summary"] == "found it"

    def test_json_with_surrounding_text_and_think(self):
        raw = '<think>Let me think about this.</think>Based on my analysis, here is the JSON:\n```json\n{"summary": "analysis complete", "css_fixes": [], "non_css_suggestions": []}\n```\nHope this helps!'
        result = _parse_json(raw)
        assert result["summary"] == "analysis complete"

    def test_json_with_nested_braces(self):
        raw = '```json\n{"summary": "test", "css_fixes": [{"selector": "body", "property": "color", "value": "red", "reason": "fix"}], "non_css_suggestions": []}\n```'
        result = _parse_json(raw)
        assert len(result["css_fixes"]) == 1
        assert result["css_fixes"][0]["selector"] == "body"

    def test_no_json_raises(self):
        with pytest.raises(ValueError, match="No valid JSON found"):
            _parse_json("This is just plain text with no JSON.")

    def test_empty_string_raises(self):
        with pytest.raises(ValueError, match="No valid JSON found"):
            _parse_json("")

    def test_whitespace_only_raises(self):
        with pytest.raises(ValueError, match="No valid JSON found"):
            _parse_json("   \n  \n  ")


class TestBuildFallbackSuggestions:
    def _make_props(self, **kwargs):
        defaults = {
            "url": "https://example.com",
            "is_dark_mode": False,
            "has_animations": True,
            "fonts": ["Arial"],
            "font_sizes": ["14px", "16px"],
            "total_elements": 200,
            "max_dom_depth": 10,
            "buttons_count": 5,
            "links_count": 10,
            "inputs_count": 2,
            "text_density": 0.3,
            "colors": ["rgb(0,0,0)", "rgb(255,255,255)", "rgb(128,128,128)"],
        }
        defaults.update(kwargs)
        return UIProperties(**defaults)

    def test_fallback_returns_all_keys(self):
        props = self._make_props()
        persona = {
            "name": "Test Persona",
            "preferences": {"color_scheme": "dark", "min_font_size": "14px", "visual_density": "high"},
        }
        result = {
            "overall_score": 50,
            "grade": "D",
            "breakdown": {"dark_mode": 30, "typography": 80, "visual_density": 40, "animations": 60, "interactivity": 70},
            "recommendations": ["Fix color scheme"],
            "dealbreakers_triggered": ["light_mode_only_design"],
        }
        suggestions = _build_fallback_suggestions(props, persona, result)
        assert "summary" in suggestions
        assert "css_fixes" in suggestions
        assert "non_css_suggestions" in suggestions

    def test_fallback_includes_worst_dimension(self):
        props = self._make_props()
        persona = {
            "name": "Test Persona",
            "preferences": {"color_scheme": "dark", "min_font_size": "14px", "visual_density": "high"},
        }
        result = {
            "overall_score": 50,
            "grade": "D",
            "breakdown": {"dark_mode": 20, "typography": 80, "visual_density": 60, "animations": 70, "interactivity": 70},
            "recommendations": [],
            "dealbreakers_triggered": [],
        }
        suggestions = _build_fallback_suggestions(props, persona, result)
        assert "Color scheme" in suggestions["summary"]

    def test_fallback_empty_breakdown(self):
        props = self._make_props()
        persona = {"name": "Test", "preferences": {}}
        result = {"overall_score": 0, "grade": "F", "breakdown": {}, "recommendations": [], "dealbreakers_triggered": []}
        suggestions = _build_fallback_suggestions(props, persona, result)
        assert suggestions["summary"] is not None

    def test_css_fixes_limited_to_five(self):
        props = self._make_props(has_animations=True)
        persona = {
            "name": "Test",
            "preferences": {
                "color_scheme": "dark",
                "min_font_size": "16px",
                "max_font_size": "18px",
                "visual_density": "very_low",
                "prefers_animations": False,
            },
        }
        result = {
            "overall_score": 30,
            "grade": "F",
            "breakdown": {"dark_mode": 20, "typography": 30, "visual_density": 20, "animations": 20, "interactivity": 80},
            "recommendations": [],
            "dealbreakers_triggered": [],
        }
        suggestions = _build_fallback_suggestions(props, persona, result)
        assert len(suggestions["css_fixes"]) <= 5

    def test_non_css_suggestions_limited_to_three(self):
        props = self._make_props()
        persona = {"name": "Test", "preferences": {}}
        result = {
            "overall_score": 50,
            "grade": "D",
            "breakdown": {"dark_mode": 50, "typography": 50, "visual_density": 50, "animations": 50, "interactivity": 50},
            "recommendations": ["Rec 1", "Rec 2", "Rec 3", "Rec 4", "Rec 5"],
            "dealbreakers_triggered": ["db1", "db2", "db3"],
        }
        suggestions = _build_fallback_suggestions(props, persona, result)
        assert len(suggestions["non_css_suggestions"]) <= 3
