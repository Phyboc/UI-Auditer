"""Shared test fixtures for UI-Auditer tests."""

import pytest
from src.extractor import UIProperties


@pytest.fixture
def gen_z_persona():
    """A minimal Gen-Z persona for testing."""
    return {
        "name": "Gen-Z Tech Early Adopter",
        "preferences": {
            "color_scheme": "dark_mode_preferred",
            "min_font_size": "12px",
            "max_font_size": "16px",
            "visual_density": "high",
            "prefers_animations": True,
        },
        "dealbreakers": ["light_mode_only_design"],
    }


@pytest.fixture
def elderly_persona():
    """A minimal Elderly persona for testing."""
    return {
        "name": "Elderly Digital Novice",
        "preferences": {
            "color_scheme": "light_mode_preferred",
            "min_font_size": "16px",
            "max_font_size": "24px",
            "visual_density": "low",
            "prefers_animations": False,
        },
        "dealbreakers": ["low_contrast_text", "auto_playing_videos"],
    }


@pytest.fixture
def minimalist_persona():
    """A minimal Minimalist persona for testing."""
    return {
        "name": "Minimalist Creative",
        "preferences": {
            "color_scheme": "monochromatic_ambient",
            "min_font_size": "13px",
            "max_font_size": "18px",
            "visual_density": "very_low",
            "prefers_animations": True,
        },
        "dealbreakers": ["cluttered_sidebar_layouts"],
    }


@pytest.fixture
def dark_page_props():
    """UIProperties for a dark-themed page with animations."""
    return UIProperties(
        url="https://example.com",
        title="Dark Page",
        is_dark_mode=True,
        has_animations=True,
        fonts=["Inter", "Fira Code"],
        font_sizes=["12px", "14px", "16px"],
        total_elements=250,
        max_dom_depth=12,
        buttons_count=15,
        links_count=30,
        inputs_count=5,
        text_density=0.45,
        colors=["rgb(18, 18, 18)", "rgb(224, 224, 224)", "rgb(100, 100, 255)"],
    )


@pytest.fixture
def light_page_props():
    """UIProperties for a light-themed page without animations."""
    return UIProperties(
        url="https://example.com",
        title="Light Page",
        is_dark_mode=False,
        has_animations=False,
        fonts=["Arial", "Helvetica"],
        font_sizes=["14px", "16px", "18px", "22px"],
        total_elements=150,
        max_dom_depth=8,
        buttons_count=5,
        links_count=8,
        inputs_count=2,
        text_density=0.2,
        colors=["rgb(255, 255, 255)", "rgb(0, 0, 0)"],
    )
