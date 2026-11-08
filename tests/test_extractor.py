"""Tests for ui_auditer.extractor — UIProperties dataclass and helper logic.

Note: Full browser extraction tests require Playwright + Chromium installed.
These tests validate the dataclass and non-browser logic only.
"""

from ui_auditer.extractor import UIProperties


class TestUIProperties:
    def test_default_values(self):
        props = UIProperties(url="https://example.com")
        assert props.url == "https://example.com"
        assert props.title == ""
        assert props.colors == []
        assert props.fonts == []
        assert props.font_sizes == []
        assert props.is_dark_mode is False
        assert props.has_animations is False
        assert props.total_elements == 0
        assert props.max_dom_depth == 0
        assert props.buttons_count == 0
        assert props.links_count == 0
        assert props.inputs_count == 0
        assert props.text_density == 0.0
        assert props.contrast_ratios == []
        assert props.contrast_samples == []
        assert props.font_size_weights == {}
        assert props.running_animations == 0
        assert props.keyframe_animations == 0
        assert props.longest_text_block == 0
        assert props.scroll_depth_ratio == 0.0
        assert props.blocking_overlay is False
        assert props.autoplay_media == 0
        assert props.hidden_navigation is False
        assert props.same_origin_links == []

    def test_custom_values(self):
        props = UIProperties(
            url="https://test.com",
            title="Test Page",
            is_dark_mode=True,
            has_animations=True,
            fonts=["Inter", "Fira Code"],
            font_sizes=["14px", "16px"],
            total_elements=300,
            max_dom_depth=15,
            buttons_count=10,
            links_count=25,
            inputs_count=3,
            text_density=0.42,
            colors=["rgb(0,0,0)", "rgb(255,255,255)"],
        )
        assert props.url == "https://test.com"
        assert props.title == "Test Page"
        assert props.is_dark_mode is True
        assert len(props.fonts) == 2
        assert props.text_density == 0.42

    def test_dataclass_is_hashable_via_url(self):
        """Ensure we can use props in dicts/sets by URL."""
        props = UIProperties(url="https://example.com")
        d = {props.url: props}
        assert "https://example.com" in d

    def test_multiple_instances_independent(self):
        p1 = UIProperties(url="https://a.com")
        p2 = UIProperties(url="https://b.com")
        p1.fonts.append("Arial")
        assert p2.fonts == []  # no shared state
