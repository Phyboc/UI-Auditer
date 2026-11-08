"""Tests for ui_auditer.fixer — closed-loop verification of CSS suggestions."""

from ui_auditer.fixer import build_css, css_block, verify_fixes

BASELINE = {"overall_score": 50, "grade": "D"}


def _fix(selector="body", prop="color", value="#000000", reason="better contrast"):
    return {
        "selector": selector,
        "property": prop,
        "value": value,
        "reason": reason,
    }


def _scorer(table):
    """Fake rescore() that looks the CSS up in a dict, defaulting to no change."""

    def _rescore(css: str) -> dict:
        score = table(css)
        grade = "A" if score >= 85 else "B" if score >= 70 else "C" if score >= 55 else "D"
        return {"overall_score": score, "grade": grade}

    return _rescore


class TestCssBlock:
    def test_formats_one_rule_with_comment(self):
        block = css_block(_fix())
        assert "/* better contrast */" in block
        assert "body { color: #000000; }" in block

    def test_missing_value_is_empty(self):
        assert css_block({"selector": "body", "property": "color"}) == ""

    def test_missing_selector_is_empty(self):
        assert css_block({"property": "color", "value": "red"}) == ""

    def test_reason_cannot_close_the_comment(self):
        block = css_block(_fix(reason="oops */ body { color: red }"))
        assert block.count("*/") == 1

    def test_build_css_skips_incomplete_rules(self):
        css = build_css([_fix(), {"selector": "p"}])
        assert css.count("{") == 1


class TestVerifyFixes:
    def test_keeps_a_fix_that_improves_the_score(self):
        fix = _fix()
        result = verify_fixes([fix], BASELINE, _scorer(lambda css: 60))
        assert result["kept"] == [fix]
        assert result["final_score"] == 60
        assert result["final_grade"] == "C"
        assert "color" in result["css"]

    def test_drops_a_fix_that_lowers_the_score(self):
        result = verify_fixes([_fix()], BASELINE, _scorer(lambda css: 40))
        assert result["kept"] == []
        assert result["final_score"] == 50
        assert "fell from 50 to 40" in result["dropped"][0]["reason"]

    def test_neutral_fix_is_kept_by_default(self):
        result = verify_fixes([_fix()], BASELINE, _scorer(lambda css: 50))
        assert len(result["kept"]) == 1
        assert result["final_score"] == 50

    def test_min_gain_requires_a_real_improvement(self):
        result = verify_fixes([_fix()], BASELINE, _scorer(lambda css: 50), min_gain=1)
        assert result["kept"] == []
        assert "no measurable gain" in result["dropped"][0]["reason"]

    def test_rules_are_applied_cumulatively(self):
        held = [_fix("body"), _fix("p")]
        result = verify_fixes(held, BASELINE, _scorer(lambda css: 50 + 5 * css.count("{")))
        assert result["final_score"] == 60
        assert result["css"].count("{") == 2
        assert [s["score_after"] for s in result["steps"]] == [55, 60]

    def test_a_later_bad_rule_does_not_undo_an_earlier_good_one(self):
        def score(css: str) -> int:
            return 50 + 10 * css.count("color: #000000") - 25 * css.count("font-size")

        result = verify_fixes(
            [_fix(), _fix(prop="font-size", value="99px")], BASELINE, _scorer(score)
        )
        assert [f["property"] for f in result["kept"]] == ["color"]
        assert result["final_score"] == 60
        assert "font-size" not in result["css"]

    def test_rescore_failure_is_a_drop(self):
        def boom(css: str) -> dict:
            raise ValueError("page died")

        result = verify_fixes([_fix()], BASELINE, boom)
        assert result["kept"] == []
        assert "re-render failed" in result["dropped"][0]["reason"]
        assert result["steps"][0]["score_after"] is None

    def test_no_fixes_returns_the_baseline(self):
        result = verify_fixes([], BASELINE, _scorer(lambda css: 99))
        assert result["final_score"] == 50
        assert result["css"] == ""
        assert result["steps"] == []

    def test_duplicate_rules_keep_the_last_value(self):
        result = verify_fixes(
            [_fix(value="#111111"), _fix(value="#222222")],
            BASELINE,
            _scorer(lambda css: 50 + 5 * css.count("{")),
        )
        assert result["css"].count("{") == 1
        assert "#222222" in result["css"]
        assert "#111111" not in result["css"]
