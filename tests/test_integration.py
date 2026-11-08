"""End-to-end extraction test with a real browser.

Runs the actual Playwright pipeline against a local fixture page, so the
injected JS, the contrast maths and the scorer are exercised together rather
than only the dataclass. Skips when Playwright or Chromium is missing, which
keeps the suite usable on a machine that has not run ``playwright install``.

The fixture encodes known values:

* ``#999`` on white at 16px is 2.85:1 and must fail a 4.5:1 floor.
* ``#949494`` on white at 32px is 3.03:1 and is legal large text (3:1).
"""

from pathlib import Path

import pytest

pytest.importorskip("playwright", reason="Playwright is not installed")

from ui_auditer.extractor import extract  # noqa: E402
from ui_auditer.scorer import (  # noqa: E402
    _check_dealbreakers,
    find_persona,
    load_all_personas,
    score,
)

FIXTURE = Path(__file__).parent / "fixtures" / "audit_page.html"


@pytest.fixture(scope="module")
def props():
    try:
        return extract(FIXTURE.as_uri(), timeout=20000)
    except RuntimeError as exc:
        if "Chromium is not installed" in str(exc):
            pytest.skip("Chromium is not installed: run 'playwright install chromium'")
        raise


class TestFixtureExtraction:
    def test_title(self, props):
        assert props.title == "Audit Fixture"

    def test_interactive_counts(self, props):
        assert props.buttons_count == 2
        assert props.links_count == 3
        assert props.inputs_count == 1

    def test_light_page(self, props):
        assert props.is_dark_mode is False

    def test_keyframe_animation_detected(self, props):
        assert props.keyframe_animations >= 1
        assert props.has_animations is True

    def test_dealbreaker_signals(self, props):
        assert props.longest_text_block >= 800
        assert props.blocking_overlay is True
        assert props.autoplay_media >= 1
        assert props.hidden_navigation is True

    def test_text_density_is_measured(self, props):
        assert 0 < props.text_density <= 1

    def test_contrast_samples_carry_typography(self, props):
        assert props.contrast_samples
        assert len(props.contrast_ratios) == len(props.contrast_samples)

        large = [s for s in props.contrast_samples if s["font_size_px"] >= 24]
        assert large, "the 32px heading should have been sampled"
        assert min(s["ratio"] for s in large) == pytest.approx(3.03, abs=0.1)

    def test_contrast_samples_are_annotated_with_elements(self, props):
        assert all(s.get("targets") for s in props.contrast_samples)
        joined = " ".join(t for s in props.contrast_samples for t in s["targets"])
        assert "p.low" in joined, joined

    def test_injected_css_changes_the_measurement(self):
        """The mechanism --apply relies on: render again with a stylesheet."""
        try:
            fixed = extract(
                FIXTURE.as_uri(),
                timeout=20000,
                inject_css=".low { color: #000000 !important; }",
            )
        except RuntimeError as exc:
            if "Chromium is not installed" in str(exc):
                pytest.skip("Chromium is not installed")
            raise
        triggered = _check_dealbreakers(
            fixed, ["low_contrast_text"], {"min_contrast_ratio": 4.5}
        )
        assert triggered == []
        # The 32px heading stays at ~3.03:1 (legal large text); the failing
        # 16px paragraph must be gone.
        assert min(s["ratio"] for s in fixed.contrast_samples) >= 3.0
        assert not [s for s in fixed.contrast_samples if s["ratio"] < 3.0]


class TestFixtureScoring:
    def test_large_text_exception_avoids_false_positive(self, props):
        # Two failing styles would appear without the exception: the 16px #999
        # paragraph and the 32px #949494 heading. Only the first is a real fail.
        triggered = _check_dealbreakers(
            props, ["low_contrast_text"], {"min_contrast_ratio": 4.5}
        )
        assert len(triggered) == 1
        assert triggered[0].startswith("low_contrast_text")

    def test_full_pipeline_flags_wall_of_text(self, props):
        persona = find_persona(load_all_personas(), "gen_z")
        result = score(props, persona)
        assert any("large_blocks_of_text" in d for d in result["dealbreakers_triggered"])
        assert 0 <= result["overall_score"] <= 100
