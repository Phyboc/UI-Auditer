<div align="center">

# 🎯 UI‑Auditer

### *Real‑world UI review for real audiences*

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)]()
[![License](https://img.shields.io/badge/License-MIT-green)]()
[![Playwright](https://img.shields.io/badge/Playwright-Headless-45ba4b?logo=playwright&logoColor=white)]()
[![CLI](https://img.shields.io/badge/CLI-Click-ff69b4)]()
[![Rich](https://img.shields.io/badge/Reports-Rich-f5c542)]()

---

> **Evaluate any webpage's UI against your target audience — and get a scored report with actionable fixes.**  
> No UX researcher required. No static HTML parsing. Just a real browser, heuristic scoring, and optional AI‑generated CSS suggestions.

<br />

</div>

---

## 📋 Table of Contents

- [Overview](#-overview)
- [Key Features](#-key-features)
- [Architecture & Tech Stack](#-architecture--tech-stack)
- [Getting Started](#-getting-started)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
  - [Environment Variables](#environment-variables)
- [Usage](#-usage)
  - [Basic Audit](#basic-audit)
  - [Personas](#personas)
  - [AI‑Powered Fix Suggestions](#ai-powered-fix-suggestions)
  - [Custom Output Path](#custom-output-path)
  - [JSON Output](#json-output)
- [Scoring Dimensions](#-scoring-dimensions)
- [Measurement & Limitations](#-measurement--limitations)
- [Testing](#-testing)
- [Project Structure](#-project-structure)
- [Pipeline](#-pipeline)
- [Roadmap](#-roadmap)
- [Contributing](#-contributing)
- [License](#-license)

---

## 📖 Overview

**UI‑Auditer** is a developer‑friendly CLI tool that bridges the gap between shipping code and knowing whether it *feels right* for your users. Point it at any URL — local dev server, staging, or production — tell it who your audience is, and get back a scored, dimension‑by‑dimension report with specific recommendations.

Behind the scenes, it launches a **headless Chromium browser** (via Playwright) to render pages exactly as a real user would see them — including React, Vue, Next.js, Tailwind, or any JavaScript‑driven framework. Computed styles are extracted directly from the browser engine, then compared against **literature-informed audience personas** in a rule‑based heuristic scorer. Optionally, an **LLM** can generate concrete CSS fix suggestions tailored to the selected persona.

---

## ✨ Key Features

| Capability | Description |
|---|---|
| 🖥️ **Real Browser Rendering** | Full Playwright‑powered Chromium — not static HTML parsing. Sees what users see. |
| 🧠 **Audience Personas** | 5 built‑in, literature-informed personas (Gen‑Z, Elderly, Corporate, Minimalist, Neurodivergent) — each with unique preferences & dealbreakers. |
| 📊 **Multi-Dimension Scoring** | Colour scheme (including measured contrast), typography, visual density, motion, and interactivity — with an overall letter grade (A–F). |
| 🎨 **Measured Contrast** | WCAG 2.1 ratios from real text/background pairs, checked against each persona's `min_contrast_ratio`. |
| 🚩 **Dealbreaker System** | Audience‑specific red flags that instantly penalise the score (e.g., auto‑playing video for neurodivergent users). |
| 🎨 **Beautiful Terminal Reports** | Rich‑powered tables, color bars, and responsive layouts — looks great in any terminal width. |
| 🤖 **AI‑Generated CSS Fixes** | Pass `--fix` to get audience‑aware CSS suggestions from an LLM (OpenRouter), saved to a CSS file. |
| 🔌 **CI‑Friendly JSON Output** | `--json` flag dumps structured data for piping, automation, or dashboards (Rich output suppressed). |
| 📦 **pip‑installable** | Install globally with `pip install .` — get a `ui-auditer` command available everywhere. |
| ⚡ **Offline‑First** | Base scoring is fully rule‑based — no API keys needed for core functionality. |

---

## 🏗 Architecture & Tech Stack

```
┌─────────────┐    ┌──────────────┐    ┌────────────┐    ┌──────────────┐
│   Browser   │    │  Extractor   │    │   Scorer   │    │   Reporter   │
│  (Playwright│───▶│  (extractor  │───▶│ (scorer.py)│───▶│  (reporter   │
│  Chromium)  │    │   .py)       │    │            │    │   .py)       │
└─────────────┘    └──────────────┘    └────────────┘    └──────────────┘
                                               │              │
                                               ▼              ▼
                                        ┌────────────┐  ┌──────────────┐
                                        │ Persona    │  │   Advisor    │
                                        │ (persona   │  │ (advisor.py) │
                                        │  .json)    │  │   (LLM)      │
                                        └────────────┘  └──────────────┘
```

| Layer | Technology | Role |
|---|---|---|
| **CLI** | [Click](https://click.palletsprojects.com/) | Argument parsing, command orchestration |
| **Browser** | [Playwright](https://playwright.dev/) | Headless Chromium rendering & computed style extraction |
| **Measurement** | Python (`contrast.py`) | Colour parsing, WCAG luminance and contrast ratios |
| **Scoring** | Python (rule‑based heuristics) | Compares extracted properties against persona JSON |
| **Reporting** | [Rich](https://rich.readthedocs.io/) | Terminal UI — tables, panels, colour bars |
| **AI Advisor** | [Requests](https://requests.readthedocs.io/) | HTTP calls to OpenRouter / Groq LLM API |
| **Config** | [python‑dotenv](https://pypi.org/project/python-dotenv/) + JSON | Environment variables + human‑editable persona definitions |
| **Runtime** | Python **3.11+** | Modern Python with dataclasses, type hints, f‑strings |

---

## 🚀 Getting Started

### Prerequisites

- **Python 3.11 or newer**
- **pip** (Python package manager)
- *(Optional)* An LLM API key for `--fix` suggestions

### Installation

Everything runs from this checkout. The package is not published to PyPI, so there is no
`pip install ui-auditer` step — you install **this folder** and its dependencies.

```bash
# 1. Create and activate an isolated environment (recommended)
python -m venv .venv
source .venv/Scripts/activate     # Windows (Git Bash)
# source .venv/bin/activate       # macOS / Linux

# 2. Install this checkout (the package comes from the working tree, not an index)
pip install -e ".[dev]"

# 3. Download the Chromium build Playwright drives (one-time, ~120 MB)
playwright install chromium

# 4. Verify
ui-auditer https://example.com --persona corporate
```

`pip install -e .` only reads `pyproject.toml` from the folder you are standing in; it
never downloads the `ui-auditer` project itself. Editable mode means source edits take
effect immediately.

### Running without installing the package

The tool also runs straight from the checkout. The runtime dependencies still need to
exist, but the package does not:

```bash
pip install playwright click rich requests python-dotenv
playwright install chromium

# must be run from the folder that contains the ui_auditer package
python -m ui_auditer https://example.com --persona gen_z
python -m ui_auditer https://example.com --persona corporate --json
```

`python -m ui_auditer` puts the current directory on `sys.path`, so it works from this
folder and nowhere else. `pip install -e .` is what makes the `ui-auditer` command
available from anywhere. The extractor can be exercised on its own as well:

```bash
python -m ui_auditer.extractor https://example.com
```

> **If a command fails:** `Chromium is not installed for Playwright` means the browser
> step was skipped; `Playwright is not installed` means the dependency step was skipped.
> Both are one-command fixes.

### Environment Variables

The only required variable is for the **optional** AI fix feature:

```bash
# .env — place in project root (automatically loaded)
LLM_API_KEY=sk-or-v1-your-openrouter-api-key-here
```

> **Note:** Without `.env`, the tool runs **fully offline** using rule‑based heuristics. The `--fix` flag simply returns fallback suggestions.

---

## 💻 Usage

### Basic Audit

```bash
# Audit a production site for Gen‑Z users
ui-auditer https://example.com --persona gen_z

# Audit a local dev server for elderly users (with extended timeout)
ui-auditer http://localhost:3000 --persona elderly --timeout 30000

# Evaluate against the corporate persona
ui-auditer https://www.example.com --persona corporate
```

### Personas

| Slug | Audience | Color Scheme | Font Range | Density | Animations | Min contrast |
|---|---|---|---|---|---|---|
| `gen_z` | Gen‑Z Tech Early Adopter | Dark mode preferred | 12–16px | High | ✅ Wants them | 4.5:1 |
| `elderly` | Elderly Digital Novice | Light mode preferred | 16–24px | Low | ❌ Avoid | 7.0:1 |
| `corporate` | Corporate Power User | Neutral / system | 11–14px | High | ❌ Avoid | 4.5:1 |
| `minimalist` | Minimalist Creative | Monochromatic | 13–18px | Very Low | ✅ Subtle | 4.5:1 |
| `neurodivergent` | Neurodivergent Focus Optimizer | Pastel / low‑stim | 13–16px | Moderate | ❌ Avoid | 5.0:1 |

Each persona includes **dealbreakers** — patterns that tank the score (e.g., auto‑playing videos for neurodivergent users, excessive whitespace for corporate).

### AI‑Powered Fix Suggestions

```bash
# Get audience‑aware CSS fixes from an LLM
ui-auditer https://example.com --persona elderly --fix
```

When `--fix` is passed:
1. The extracted properties, scoring results, and persona are sent as a prompt to an LLM via OpenRouter.
2. The LLM returns structured JSON with CSS selectors/properties/values and non‑CSS suggestions.
3. CSS fixes are written to **`suggested_fixes.css`** — ready to drop into your project.
4. The terminal report includes a dedicated AI Suggestions panel.

### Custom Output Path

Use `--output` or `-o` to control where the CSS fixes file is written:

```bash
# Write CSS fixes to a custom path
ui-auditer https://example.com --fix -o ./public/fixes.css

# Combine with --json (JSON to stdout, CSS to file)
ui-auditer https://example.com --json --fix -o ./fixes.css | jq '.score'
```

### JSON Output

```bash
# Pipe structured data to jq or your own tooling
ui-auditer https://example.com --persona corporate --json
```

> **Note:** When `--json` is used, all Rich terminal output is suppressed — only clean JSON hits stdout, making it safe for piping.

Example output (trimmed — `fixes` is `null` unless `--fix` is passed):

```json
{
  "properties": {
    "url": "https://example.com",
    "title": "Example Domain",
    "colors": ["rgb(0, 0, 0)", "rgb(0, 0, 238)"],
    "fonts": ["system-ui"],
    "font_sizes": ["16px", "14px"],
    "font_size_weights": {"16px": 166, "14px": 740},
    "contrast_ratios": [18.1, 8.1],
    "is_dark_mode": false,
    "has_animations": false,
    "running_animations": 0,
    "keyframe_animations": 0,
    "total_elements": 22,
    "max_dom_depth": 4,
    "buttons_count": 0,
    "links_count": 1,
    "inputs_count": 0,
    "text_density": 0.32,
    "longest_text_block": 206,
    "scroll_depth_ratio": 1.08,
    "blocking_overlay": false,
    "autoplay_media": 0,
    "hidden_navigation": false
  },
  "score": {
    "persona_name": "Corporate Power User",
    "overall_score": 71,
    "grade": "B",
    "breakdown": {
      "dark_mode": 82,
      "typography": 82,
      "visual_density": 80,
      "animations": 100,
      "interactivity": 10
    },
    "recommendations": ["Typography mismatch — 18% of visible text is outside 11–14px. …"],
    "dealbreakers_triggered": []
  },
  "fixes": null
}
```

---

## 📊 Scoring Dimensions

| Dimension | Weight | What's Checked |
|---|---|---|
| 🎨 **Color Scheme** | Equal | Dark/light mode match **plus measured WCAG 2.1 contrast** against the persona's `min_contrast_ratio` |
| 🔤 **Typography** | Equal | Font sizes against persona min/max, weighted by visible character count |
| 📐 **Visual Density** | Equal | Text-node area / page area vs expected density (very_low → high), capped at 1.0 |
| 🌀 **Motion** | Equal | Running and keyframe animations vs persona preference; hover transitions are ignored |
| 🔘 **Interactivity** | Equal | Button + link + form-control count vs expected interface complexity (`interaction_density`) |
| 🚩 **Dealbreakers** | Penalty | Each triggered dealbreaker docks **5 points**. Only signals the rendered page can expose are used — see below |

The final score is the **average of the five dimension scores** (20% each, 0–100) mapped to a letter grade:

| Grade | Score Range |
|---|---|
| **A** | 85–100 |
| **B** | 70–84 |
| **C** | 55–69 |
| **D** | 40–54 |
| **F** | 0–39 |

### Dealbreakers

Only red flags the DOM and computed styles can actually measure are declared.
`persona.json` and `ui_auditer/scorer.py` are kept in sync by a test that fails if a
persona declares a slug the scorer does not handle.

| Slug | Measured signal | Persona |
|---|---|---|
| `low_contrast_text` | WCAG ratio below the persona's `min_contrast_ratio` | Elderly |
| `large_blocks_of_text` | one text node >= 800 characters | Gen-Z |
| `excessive_whitespace_padding` | text density < 15% | Corporate |
| `cluttered_sidebar_layouts` | more than 300 DOM elements | Minimalist |
| `auto_playing_videos` | `<video autoplay>`, `<audio autoplay>`, or a playing video | Neurodivergent |
| `flashing_banner_animations` | any element running a keyframe animation | Neurodivergent |
| `infinite_scrolling_feeds` | page height >= 6x the viewport | Neurodivergent |
| `pop_up_advertisements` | fixed overlay covering >= 50% of the viewport on load | Minimalist |
| `unskippable_onboarding_modals` | same overlay signal | Corporate |
| `hidden_navigation` | `nav` hidden at desktop width (hamburger-only) | Elderly |

Removed because a rendered page cannot observe them: `slow_loading_animations`,
`accidental_swipe_gestures`, `lack_of_keyboard_shortcuts`, `bright_saturated_accent_colors`.
`light_mode_only_design` was also removed: the colour-scheme dimension already scores a
light page at 20/100 for a dark-mode persona, so a dealbreaker charged the same property twice.

---

## 📏 Measurement & Limitations

Every dimension is computed from the rendered page rather than estimated from the HTML:

| Signal | How it is measured |
|---|---|
| **Contrast** | For each visible text style, the text colour is paired with the effective background (walking up through transparent ancestors). WCAG 2.1 relative luminance gives a ratio, checked against the persona's `min_contrast_ratio`. The colour-scheme score is 60% dark/light match and 40% contrast compliance. |
| **Typography** | Font sizes are weighted by visible character count, so a small footer cannot outweigh body copy. |
| **Density** | Sum of text-node line boxes divided by page area, clipped to the viewport and capped at 1.0, so nested elements are not counted twice. |
| **Motion** | `document.getAnimations()` plus declared keyframe animations. CSS transitions (hover/focus styling) are ignored. |
| **Dark mode** | Background resolved from `<html>` first, then `<body>`, with `color-scheme` as a fallback. |

### Known limitations

- Large text (>=24px, or >=18.66px bold) is held to the same ratio as body text; the WCAG 3:1 large-text exception is not applied.
- Contrast is sampled per text style, not per element, and there is no axe-core cross-check yet.
- Dealbreaker signals are proxies, not detectors: `large_blocks_of_text` counts the longest single text node (a wall of text split into short paragraphs is missed), `infinite_scrolling_feeds` uses page height >=6x viewport, `pop_up_advertisements` / `unskippable_onboarding_modals` only see fixed overlays covering half the viewport at load, and `hidden_navigation` only sees a hidden `nav` element.
- Personas are literature-informed, not empirically validated; the dimension weights are hand-set rather than calibrated against human ratings.
- One page per run — no crawl, screenshots, or cross-persona comparison yet (`--compare` is planned).

---

## 🧪 Testing

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run all tests
python -m pytest tests/ -v

# Run with coverage
python -m pytest tests/ -v --tb=short
```

**Test coverage:**

| Module | Tests | What's covered |
|---|---|---|
| `test_advisor.py` | 17 | Advisor unit tests |
| `test_contrast.py` | 15 | Colour parsing, WCAG luminance, alpha compositing, contrast ratios |
| `test_extractor.py` | 4 | `UIProperties` dataclass defaults, custom values, instance independence |
| `test_scorer.py` | 71 | Persona loading, slug matching, all five scoring rules, contrast blending, weighted typography, every declared dealbreaker, dealbreaker/persona parity, full pipeline |

---

## 📁 Project Structure

```
web_auditer/                # this checkout
├── 📄 pyproject.toml         # Package config, dependencies, CLI entry point
├── 📁 ui_auditer/
│   ├── 📦 __init__.py        # Package init (version)
│   ├── 🚀 __main__.py        # python -m ui_auditer support
│   ├── ⚙️  cli.py             # Entry point — Click commands, pipeline orchestration
│   ├── 🌐 extractor.py       # Playwright browser engine — renders pages & extracts computed styles
│   ├── 🎨 contrast.py        # WCAG 2.1 colour parsing, luminance and contrast ratios
│   ├── 📊 scorer.py          # Heuristic engine — scores properties against persona rules
│   ├── 📄 reporter.py        # Rich terminal renderer — tables, panels, colour bars
│   ├── 🤖 advisor.py         # LLM advisor — generates CSS fix suggestions & writes to file
│   └── 👤 persona.json       # 5 audience personas with preferences & dealbreakers
├── 📁 tests/
│   ├── 📦 __init__.py
│   ├── 🔧 conftest.py        # Shared test fixtures
│   ├── 🧪 test_scorer.py     # Scoring rules, contrast blending, dealbreakers
│   ├── 🧪 test_contrast.py   # WCAG luminance and ratio maths
│   ├── 🧪 test_extractor.py  # UIProperties dataclass
│   ├── 🧪 test_advisor.py    # LLM advisor parsing and CSS output
├── 🔒 .env                   # API keys (gitignored)
├── 🔒 .gitignore
└── 📖 README.md              # You are here ✨
```

### Module Responsibilities

| File | Purpose |
|---|---|
| `cli.py` | Click decorators, persona loading, error handling, JSON/terminal output routing |
| `extractor.py` | Launches headless Chromium, evaluates a single JS blob that extracts computed styles, text-node density, contrast pairs and weighted font sizes |
| `contrast.py` | WCAG 2.1 colour parsing, relative luminance, alpha compositing and contrast ratios (unit-tested) |
| `scorer.py` | 5 scoring functions + dealbreaker checker; clean swap‑in point for ML models ✨ |
| `reporter.py` | Rich‑powered terminal output — responsive to narrow/wide terminals |
| `advisor.py` | Builds prompt, calls OpenRouter API, parses JSON response, writes CSS fix files |
| `persona.json` | 5 personas, each with ~9 preference keys + only observable dealbreakers + research citation |

---

## 🔄 Pipeline

```
URL  ──▶  🌐 extractor.py
             │
             ▼  (UIProperties dataclass)
           📊 scorer.py  ──  📁 persona.json
             │
             ├── ▶  📄 reporter.py  (terminal output)
             │
             └── ▶  🤖 advisor.py  (if --fix flag)
                        │
                        ▼
                   suggested_fixes.css (or custom --output path)
```

---

## 🗺 Roadmap

### ✅ Implemented
- [x] Playwright-based extraction — computed styles, contrast pairs, text-node density, weighted font sizes, DOM depth, animations, interactivity
- [x] Measured WCAG 2.1 contrast with per-persona minimum ratios
- [x] Text-weighted typography and nested-safe density measurement
- [x] 5 literature-informed audience personas with preferences & dealbreakers
- [x] Rule‑based heuristic scoring engine (5 dimensions + dealbreaker penalties)
- [x] Responsive Rich terminal reporter (adapts to wide & narrow terminals)
- [x] `--json` output flag for automation / CI pipelines (Rich output suppressed for clean piping)
- [x] `--fix` flag: AI‑generated CSS fix suggestions via OpenRouter / Groq
- [x] `--output` / `-o` flag: custom CSS fix file path
- [x] pip‑installable package with `ui-auditer` CLI entry point
- [x] 107 unit tests, including a dealbreaker/persona parity guard

### 🔜 Planned
- [ ] `--compare` flag — score against all 5 personas in a single run
- [ ] 🔍 axe-core cross-check for contrast and tap targets
- [ ] 📊 Calibrate heuristic weights against human ratings (pairwise study)
- [ ] 📸 Screenshot capture for visual documentation in reports
- [ ] 🖥️ Interactive mode — real‑time persona switching
- [ ] 🤖 ML model integration (replace rule functions with a trained classifier)
- [ ] 🌐 Web UI wrapper (Flask/FastAPI)
- [ ] 📦 Publish to PyPI (`pip install ui-auditer`)

### 🧠 ML Upgrade Path

The scoring architecture is designed for a clean swap:

```python
# Current — hand‑written rules
def score(props, persona):
    checks = {
        "dark_mode":  _score_dark_mode(props, prefs),
        "typography": _score_font_sizes(props, prefs),
        ...
    }

# Future — model predictions
feature_vector = [
    1 if props.is_dark_mode else 0,
    props.text_density,
    props.buttons_count / 100,
    min(font_sizes), max(font_sizes),
    1 if props.has_animations else 0,
    props.total_elements / 500,
    props.max_dom_depth / 30,
]
prediction = model.predict([feature_vector])  # sklearn / PyTorch
```

The CLI, reporter, and persona files stay **unchanged**.

---

## 🤝 Contributing

Contributions are welcome! Here's how you can help:

1. **🐛 Report bugs** — Open an issue with the URL, persona, and error output.
2. **💡 Suggest personas** — Have a user segment in mind? Open a PR with a new persona entry in `persona.json`.
3. **🔧 Add features** — Check the [Roadmap](#-roadmap) for planned work. The module boundaries are clean — you can touch just one file.
4. **📚 Improve docs** — Typos, clarifications, or new examples are always appreciated.

### Quick Start for Contributors

```bash
# Fork & clone
git clone https://github.com/Phyboc/UI-Auditer.git
cd web_auditer

# Create a branch
git checkout -b feature/your-idea

# Install in dev mode (editable + test deps)
pip install -e ".[dev]"
playwright install chromium

# Run tests
python -m pytest tests/ -v

# Make your changes & test manually
ui-auditer https://example.com --persona gen_z
ui-auditer https://example.com --persona elderly --json

# Submit a pull request 🚀
```

---

## 📄 License

This project is open source and available under the **MIT License**.

---

<div align="center">
  <br />
  <sub>Built with 💻 after a hackathon that needed better UI feedback.</sub>
  <br />
  <sub>
    <a href="https://github.com/Phyboc/UI-Auditer">GitHub</a> •
    <a href="https://github.com/yourusername/ui-auditer/issues">Issues</a> •
    <a href="https://github.com/yourusername/ui-auditer/pulls">Pull Requests</a>
  </sub>
</div>
