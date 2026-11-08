"""Tests for WCAG contrast maths."""

from ui_auditer.contrast import (
    contrast_ratio,
    parse_css_color,
    ratios_from_pairs,
    relative_luminance,
)


class TestParseCssColor:
    def test_rgb(self):
        assert parse_css_color("rgb(18, 18, 18)") == (18.0, 18.0, 18.0, 1.0)

    def test_rgba_keeps_alpha(self):
        assert parse_css_color("rgba(0, 0, 0, 0.5)")[3] == 0.5

    def test_short_hex(self):
        assert parse_css_color("#fff") == (255.0, 255.0, 255.0, 1.0)

    def test_transparent(self):
        assert parse_css_color("transparent")[3] == 0.0

    def test_invalid_returns_none(self):
        assert parse_css_color("not-a-colour") is None
        assert parse_css_color("") is None
        assert parse_css_color(None) is None


class TestContrastRatio:
    def test_black_on_white_is_21(self):
        ratio = contrast_ratio(parse_css_color("rgb(0,0,0)"), parse_css_color("#ffffff"))
        assert round(ratio) == 21

    def test_same_colour_is_1(self):
        ratio = contrast_ratio(parse_css_color("rgb(40,40,40)"), parse_css_color("rgb(40,40,40)"))
        assert round(ratio, 2) == 1.0

    def test_order_does_not_matter(self):
        black, white = parse_css_color("rgb(0,0,0)"), parse_css_color("rgb(255,255,255)")
        assert round(contrast_ratio(black, white), 4) == round(contrast_ratio(white, black), 4)

    def test_translucent_text_is_composited(self):
        solid = contrast_ratio(parse_css_color("rgb(0,0,0)"), parse_css_color("rgb(255,255,255)"))
        faded = contrast_ratio(
            parse_css_color("rgba(0,0,0,0.5)"), parse_css_color("rgb(255,255,255)")
        )
        assert 1.0 < faded < solid


class TestRelativeLuminance:
    def test_white_is_1(self):
        assert round(relative_luminance((255.0, 255.0, 255.0, 1.0)), 4) == 1.0

    def test_black_is_0(self):
        assert relative_luminance((0.0, 0.0, 0.0, 1.0)) == 0.0


class TestRatiosFromPairs:
    def test_converts_valid_pairs(self):
        ratios = ratios_from_pairs([["rgb(0,0,0)", "rgb(255,255,255)"]])
        assert ratios == [21.0]

    def test_skips_unparseable_pairs(self):
        ratios = ratios_from_pairs([["nope", "rgb(255,255,255)"], ["rgb(0,0,0)", "nope"]])
        assert ratios == []

    def test_skips_fully_transparent_background(self):
        ratios = ratios_from_pairs([["rgb(0,0,0)", "rgba(0,0,0,0)"]])
        assert ratios == []

    def test_handles_empty_input(self):
        assert ratios_from_pairs([]) == []
