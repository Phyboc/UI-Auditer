#!/usr/bin/env python3
"""Score a sample of real pages before and after the scoring changes.

The "before" numbers are not simulated: the script checks out the pre-fix
commit into a temporary git worktree and runs that code with the same browser,
the same personas and the same viewport.

Usage::

    python scripts/distribution.py
    python scripts/distribution.py --legacy-ref 3834a44 --limit 10
    python scripts/distribution.py https://example.com https://python.org

Extraction happens once per page per version, then every persona is scored
in the same process, so 28 pages cost 56 browser launches rather than 280.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from ui_auditer.scorer import _slugify, load_all_personas  # noqa: E402

DEFAULT_URLS = [
    "https://example.com",
    "https://python.org",
    "https://pypi.org",
    "https://github.com",
    "https://gitlab.com",
    "https://stackoverflow.com",
    "https://wikipedia.org",
    "https://mozilla.org",
    "https://developer.mozilla.org",
    "https://w3.org",
    "https://gov.uk",
    "https://bbc.co.uk",
    "https://theguardian.com",
    "https://nytimes.com",
    "https://cnn.com",
    "https://apple.com",
    "https://microsoft.com",
    "https://stripe.com",
    "https://vercel.com",
    "https://react.dev",
    "https://tailwindcss.com",
    "https://npmjs.com",
    "https://reddit.com",
    "https://notion.so",
    "https://linear.app",
    "https://figma.com",
    "https://dribbble.com",
    "https://css-tricks.com",
]

# Runs one extraction + all personas inside the subprocess, against whichever
# checkout it is pointed at (``ui_auditer`` today, ``src`` before the rename).
RUNNER = r'''
import json, sys
package, url, timeout = sys.argv[1], sys.argv[2], int(sys.argv[3])
module = __import__(package, fromlist=["extractor", "scorer"])
extractor = getattr(module, "extractor")
scorer = getattr(module, "scorer")
try:
    props = extractor.extract(url, timeout=timeout)
except Exception as exc:
    print(json.dumps({"ok": False, "error": f"{type(exc).__name__}: {exc}"[:300]}))
    raise SystemExit(0)
scores = {}
for persona in scorer.load_all_personas():
    result = scorer.score(props, persona)
    scores[scorer._slugify(persona["name"])] = {
        "score": result["overall_score"],
        "grade": result["grade"],
        "dealbreakers": result["dealbreakers_triggered"],
    }
print(json.dumps({"ok": True, "scores": scores}))
'''


def run_version(root: Path, package: str, url: str, page_timeout: int, budget: int) -> dict:
    try:
        proc = subprocess.run(
            [sys.executable, "-c", RUNNER, package, url, str(page_timeout)],
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=budget,
        )
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": f"timed out after {budget}s"}

    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout).strip().splitlines()
        return {"ok": False, "error": (detail[-1] if detail else f"exit {proc.returncode}")[:300]}

    for line in reversed(proc.stdout.strip().splitlines()):
        try:
            return json.loads(line)
        except json.JSONDecodeError:
            continue
    return {"ok": False, "error": "no JSON on stdout"}


def make_worktree(ref: str) -> Path:
    directory = Path(tempfile.mkdtemp(prefix="ui-auditer-legacy-"))
    subprocess.run(
        ["git", "worktree", "add", "--detach", str(directory), ref],
        cwd=str(ROOT),
        check=True,
        capture_output=True,
        text=True,
    )
    return directory


def drop_worktree(directory: Path) -> None:
    subprocess.run(
        ["git", "worktree", "remove", "--force", str(directory)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    if directory.exists():
        shutil.rmtree(directory, ignore_errors=True)


def _find_cell(result: dict, slug: str) -> dict | None:
    if not result or not result.get("ok"):
        return None
    return result["scores"].get(slug)


def build_report(rows: list[dict], slugs: list[str], legacy_ref: str | None) -> str:
    ok_rows = [r for r in rows if r["after"].get("ok")]
    failed = [r for r in rows if not r["after"].get("ok")]

    lines = [
        "# Scoring distribution: before vs after",
        "",
        f"Generated {date.today().isoformat()} from `scripts/distribution.py`.",
        "",
        f"- Pages attempted: **{len(rows)}**, scored successfully: **{len(ok_rows)}**",
        "- Viewport 1280x800, headless Chromium, page-load timeout 25s.",
    ]
    if legacy_ref:
        lines.append(
            f"- \"Before\" = commit `{legacy_ref}` (pre-fix) run from a temporary git worktree."
        )
    lines.append("- \"After\" = current working tree.")
    lines.append("")

    lines += ["## Per persona", ""]
    lines.append(
        "| Persona | Mean before | Mean after | Delta | Improved | Regressed | "
        "Dealbreakers before | Dealbreakers after |"
    )
    lines.append("|---|---|---|---|---|---|---|---|")

    for slug in slugs:
        before_scores, after_scores = [], []
        improved = regressed = 0
        db_before = db_after = 0
        for row in ok_rows:
            before = _find_cell(row["before"], slug)
            after = _find_cell(row["after"], slug)
            if after is None:
                continue
            after_scores.append(after["score"])
            db_after += len(after["dealbreakers"])
            if before is None:
                continue
            before_scores.append(before["score"])
            db_before += len(before["dealbreakers"])
            if after["score"] > before["score"]:
                improved += 1
            elif after["score"] < before["score"]:
                regressed += 1

        if not after_scores:
            continue
        mean_before = sum(before_scores) / len(before_scores) if before_scores else 0
        mean_after = sum(after_scores) / len(after_scores)
        delta = mean_after - mean_before if before_scores else 0
        lines.append(
            f"| `{slug}` | {mean_before:.1f} | {mean_after:.1f} | {delta:+.1f} | "
            f"{improved} | {regressed} | {db_before} | {db_after} |"
        )

    lines += ["", "## Per page", ""]
    lines.append("| Page | " + " | ".join(f"`{s}`" for s in slugs) + " |")
    lines.append("|---|" + "---|" * len(slugs))

    for row in rows:
        url = row["url"]
        cells = []
        for slug in slugs:
            before = _find_cell(row["before"], slug)
            after = _find_cell(row["after"], slug)
            if after is None:
                cells.append("—")
            elif before is None:
                cells.append(f"{after['score']} {after['grade']}")
            else:
                change = after["score"] - before["score"]
                arrow = "" if change == 0 else f" ({change:+d})"
                cells.append(f"{before['score']} → {after['score']} {after['grade']}{arrow}")
        lines.append(f"| {url} | " + " | ".join(cells) + " |")

    if failed:
        lines += ["", "## Could not be scored", ""]
        for row in failed:
            reason = row["after"].get("error", "unknown error")
            lines.append(f"- {row['url']} — `{reason}`")

    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("urls", nargs="*", help="URLs to audit (defaults to a fixed sample).")
    parser.add_argument("--legacy-ref", default="3834a44",
                        help="Commit to use for the 'before' numbers (default: 3834a44).")
    parser.add_argument("--no-legacy", action="store_true", help="Only score the current tree.")
    parser.add_argument("--limit", type=int, default=0, help="Audit at most N pages.")
    parser.add_argument("--page-timeout", type=int, default=25000, help="Per-page load timeout (ms).")
    parser.add_argument("--budget", type=int, default=120, help="Per-page subprocess budget (s).")
    parser.add_argument("--out", default="distribution_report.md", help="Markdown output path.")
    args = parser.parse_args()

    urls = args.urls or DEFAULT_URLS
    if args.limit:
        urls = urls[: args.limit]

    slugs = [_slugify(p["name"]) for p in load_all_personas()]

    legacy_root: Path | None = None
    if not args.no_legacy:
        try:
            legacy_root = make_worktree(args.legacy_ref)
            print(f"legacy worktree: {legacy_root}")
        except subprocess.CalledProcessError as exc:
            print(f"Could not create a worktree for {args.legacy_ref}: {exc.stderr}")
            return 1

    rows = []
    try:
        for index, url in enumerate(urls, 1):
            print(f"[{index}/{len(urls)}] {url}")
            before = (
                run_version(legacy_root, "src", url, args.page_timeout, args.budget)
                if legacy_root else {"ok": False, "error": "not run"}
            )
            after = run_version(ROOT, "ui_auditer", url, args.page_timeout, args.budget)
            status = "ok" if after.get("ok") else f"error: {after.get('error')}"
            print(f"    after: {status}")
            rows.append({"url": url, "before": before, "after": after})
    finally:
        if legacy_root:
            drop_worktree(legacy_root)

    report = build_report(rows, slugs, None if args.no_legacy else args.legacy_ref)
    out_path = Path(args.out)
    if not out_path.is_absolute():
        out_path = ROOT / out_path
    out_path.write_text(report, encoding="utf-8")
    print(f"\nwrote {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
