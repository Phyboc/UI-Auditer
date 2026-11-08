"""Tests for ui_auditer.cli — flag wiring without launching a browser.

``extract`` is monkeypatched, so these tests cover the orchestration: which
personas get scored, how --apply calls back into extraction, what the JSON
payload contains and which exit codes the CI flags produce.
"""

import json

import pytest
from click.testing import CliRunner

from ui_auditer import cli as cli_module
from ui_auditer.extractor import UIProperties


def _props(**overrides) -> UIProperties:
    base = {
        "url": "https://example.com",
        "title": "Example",
        "total_elements": 40,
        "max_dom_depth": 6,
        "buttons_count": 4,
        "links_count": 8,
        "inputs_count": 1,
        "text_density": 0.3,
        "font_sizes": ["16px"],
        "font_size_weights": {"16px": 400},
        "contrast_samples": [{"ratio": 12.0, "font_size_px": 16.0, "bold": False}],
        "contrast_ratios": [12.0],
    }
    base.update(overrides)
    return UIProperties(**base)


@pytest.fixture
def extracted(monkeypatch):
    """Record every extract() call and return a plain, scoreable page."""
    calls = []

    def _extract(url, timeout=15000, inject_css=None):
        calls.append({"url": url, "css": inject_css})
        return _props(url=url)

    monkeypatch.setattr(cli_module, "extract", _extract)
    return calls


def _run(*args):
    return CliRunner().invoke(cli_module.main, list(args))


def _payload(output: str) -> dict:
    return json.loads(output[output.index("{"):])


class TestBasics:
    def test_json_payload_keeps_its_shape(self, extracted):
        result = _run("example.com", "--json")
        assert result.exit_code == 0
        payload = _payload(result.output)
        assert set(payload) == {"properties", "score", "fixes"}
        assert payload["properties"]["url"] == "https://example.com"

    def test_bare_host_gets_https(self, extracted):
        _run("example.com", "--json")
        assert extracted[0]["url"] == "https://example.com"


class TestCompare:
    def test_scores_every_persona_from_one_render(self, extracted):
        payload = _payload(_run("example.com", "--json", "--compare").output)
        assert len(payload["comparison"]) == 5
        assert len(extracted) == 1  # one render, five scores
        names = {r["persona_name"] for r in payload["comparison"]}
        assert "Elderly Digital Novice" in names

    def test_comparison_is_sorted_by_score(self, extracted):
        payload = _payload(_run("example.com", "--json", "--compare").output)
        scores = [r["overall_score"] for r in payload["comparison"]]
        assert scores == sorted(scores, reverse=True)


class TestApply:
    def test_apply_requires_fix(self, extracted):
        result = _run("example.com", "--apply")
        assert result.exit_code == 1
        assert "requires --fix" in result.output

    def test_apply_reports_verified_rules(self, extracted, monkeypatch, tmp_path):
        monkeypatch.setattr(
            cli_module,
            "get_suggestions",
            lambda *a, **k: {
                "summary": "Improve contrast",
                "css_fixes": [
                    {
                        "selector": "p",
                        "property": "color",
                        "value": "#000000",
                        "reason": "contrast",
                    }
                ],
                "non_css_suggestions": [],
            },
        )
        target = tmp_path / "fixes.css"
        result = _run("example.com", "--json", "--fix", "--apply", "-o", str(target))
        assert result.exit_code == 0
        payload = _payload(result.output)
        assert payload["apply"]["kept"]
        assert payload["apply"]["steps"][0]["kept"] is True
        assert "#000000" in target.read_text(encoding="utf-8")
        # one render for the audit, one per candidate rule
        assert len(extracted) == 2

    def test_without_apply_the_whole_suggestion_file_is_written(
        self, extracted, monkeypatch, tmp_path
    ):
        monkeypatch.setattr(
            cli_module,
            "get_suggestions",
            lambda *a, **k: {
                "summary": "s",
                "css_fixes": [
                    {"selector": "p", "property": "color", "value": "red", "reason": "r"},
                    {"selector": "h1", "property": "color", "value": "blue", "reason": "r"},
                ],
                "non_css_suggestions": [],
            },
        )
        target = tmp_path / "fixes.css"
        _run("example.com", "--json", "--fix", "-o", str(target))
        text = target.read_text(encoding="utf-8")
        assert "red" in text and "blue" in text
        assert len(extracted) == 1


class TestExitCodes:
    def test_fail_under_too_high_exits_one(self, extracted):
        result = _run("example.com", "--json", "--fail-under", "101")
        assert result.exit_code == 1

    def test_fail_under_zero_passes(self, extracted):
        assert _run("example.com", "--json", "--fail-under", "0").exit_code == 0

    def test_fail_under_sees_the_worst_crawled_page(self, monkeypatch):
        def _extract(url, timeout=15000, inject_css=None):
            return _props(url=url, same_origin_links=["https://example.com/bad"])

        monkeypatch.setattr(cli_module, "extract", _extract)
        # The start page and the crawled page score identically, so a threshold
        # above both must fail through the crawl branch as well.
        assert _run("example.com", "--json", "--crawl", "1", "--fail-under", "101").exit_code == 1

    def test_fail_under_explains_itself_without_json(self, extracted):
        result = _run("example.com", "--fail-under", "101")
        assert result.exit_code == 1
        assert "below --fail-under" in result.output


class TestCrawl:
    def test_scores_discovered_links(self, monkeypatch):
        calls = []

        def _extract(url, timeout=15000, inject_css=None):
            calls.append(url)
            return _props(
                url=url,
                same_origin_links=[
                    "https://example.com/a",
                    "https://example.com/b",
                    "https://example.com/c",
                ],
            )

        monkeypatch.setattr(cli_module, "extract", _extract)
        payload = _payload(_run("example.com", "--json", "--crawl", "2").output)
        assert len(payload["pages"]) == 2
        assert payload["pages"][0]["url"] == "https://example.com/a"
        assert len(calls) == 3  # start page + two links

    def test_a_failing_page_does_not_abort_the_crawl(self, monkeypatch):
        def _extract(url, timeout=15000, inject_css=None):
            if url.endswith("/broken"):
                raise TimeoutError("navigation timed out")
            return _props(url=url, same_origin_links=["https://example.com/broken"])

        monkeypatch.setattr(cli_module, "extract", _extract)
        result = _run("example.com", "--json", "--crawl", "1")
        payload = _payload(result.output)
        assert result.exit_code == 0
        assert payload["pages"][0]["error"].startswith("navigation timed out")
