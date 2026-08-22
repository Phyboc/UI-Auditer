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
- [Testing](#-testing)
- [Project Structure](#-project-structure)
- [Pipeline](#-pipeline)
- [Roadmap](#-roadmap)
- [Contributing](#-contributing)
- [License](#-license)

---

## 📖 Overview

**UI‑Auditer** is a developer‑friendly CLI tool that bridges the gap between shipping code and knowing whether it *feels right* for your users. Point it at any URL — local dev server, staging, or production — tell it who your audience is, and get back a scored, dimension‑by‑dimension report with specific recommendations.

Behind the scenes, it launches a **headless Chromium browser** (via Playwright) to render pages exactly as a real user would see them — including React, Vue, Next.js, Tailwind, or any JavaScript‑driven framework. Computed styles are extracted directly from the browser engine, then compared against **research‑backed audience personas** in a rule‑based heuristic scorer. Optionally, an **LLM** can generate concrete CSS fix suggestions tailored to the selected persona.

---

## ✨ Key Features

| Capability | Description |
|---|---|
| 🖥️ **Real Browser Rendering** | Full Playwright‑powered Chromium — not static HTML parsing. Sees what users see. |
| 🧠 **Audience Personas** | 5 built‑in, research‑backed personas (Gen‑Z, Elderly, Corporate, Minimalist, Neurodivergent) — each with unique preferences & dealbreakers. |
| 📊 **Multi‑Dimension Scoring** | Scores across Color Scheme, Typography, Visual Density, Motion, and Interactivity — with an overall letter grade (A–F). |
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

```bash
# 1. Clone the repository
git clone https://github.com/yourusername/ui-auditer.git
cd ui-auditer

# 2. Install the package (creates the `ui-auditer` CLI command)
pip install .

# 3. Install Chromium browser (one-time)
playwright install chromium

# 4. Verify it works
ui-auditer https://example.com --persona corporate
```

**Development install** (editable mode — changes to source take effect immediately):

```bash
pip install -e ".[dev]"
playwright install chromium
```

**Without installing** (run directly from source):

```bash
pip install playwright click rich requests python-dotenv
playwright install chromium
python -m src https://example.com --persona gen_z
```

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

| Slug | Audience | Color Scheme | Font Range | Density | Animations |
|---|---|---|---|---|---|
| `gen_z` | Gen‑Z Tech Early Adopter | Dark mode preferred | 12–16px | High | ✅ Wants them |
| `elderly` | Elderly Digital Novice | Light mode preferred | 16–24px | Low | ❌ Avoid |
| `corporate` | Corporate Power User | Neutral / system | 11–14px | High | ❌ Avoid |
| `minimalist` | Minimalist Creative | Monochromatic | 13–18px | Very Low | ✅ Subtle |
| `neurodivergent` | Neurodivergent Focus Optimizer | Pastel / low‑stim | 13–16px | Moderate | ❌ Avoid |

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

Example output:

```json
{
  "properties": {
    "url": "https://example.com",
    "is_dark_mode": false,
    "fonts": ["Arial", "Helvetica"],
    "font_sizes": ["14px", "16px"],
    "text_density": 0.34,
    "total_elements": 218
  },
  "score": {
    "overall_score": 72,
    "grade": "B",
    "breakdown": {
      "dark_mode": 70,
      "typography": 88,
      "visual_density": 65,
      "animations": 100,
      "interactivity": 40
    }
  }
}
```

---

## 📊 Scoring Dimensions

| Dimension | Weight | What's Checked |
|---|---|---|
| 🎨 **Color Scheme** | Equal | Dark/light mode match to audience expectation; dealbreakers for contrast & brightness |
| 🔤 **Typography** | Equal | Font size range against persona's min/max requirements (e.g., ≥16px for elderly) |
| 📐 **Visual Density** | Equal | Text‑area / page‑area ratio vs expected density level (very_low → high) |
| 🌀 **Motion** | Equal | Presence/absence of CSS animations & transitions vs persona preference |
| 🔘 **Interactivity** | Equal | Button + link count vs expected interface complexity for the persona |
| 🚩 **Dealbreakers** | Penalty | Each triggered dealbreaker docks **5 points** from the final score |

The final score is a **weighted average** (0–100) mapped to a letter grade:

| Grade | Score Range |
|---|---|
| **A** | 85–100 |
| **B** | 70–84 |
| **C** | 55–69 |
| **D** | 40–54 |
| **F** | 0–39 |

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
| `test_scorer.py` | 49 | Persona loading, slug matching, all 5 scoring functions, dealbreakers, full pipeline |
| `test_extractor.py` | 4 | `UIProperties` dataclass defaults, custom values, instance independence |

---

## 📁 Project Structure

```
ui-auditer/
├── 📄 pyproject.toml         # Package config, dependencies, CLI entry point
├── 📁 src/
│   ├── 📦 __init__.py        # Package init (version)
│   ├── 🚀 __main__.py        # python -m src support
│   ├── ⚙️  cli.py             # Entry point — Click commands, pipeline orchestration
│   ├── 🌐 extractor.py       # Playwright browser engine — renders pages & extracts computed styles
│   ├── 📊 scorer.py          # Heuristic engine — scores properties against persona rules
│   ├── 📄 reporter.py        # Rich terminal renderer — tables, panels, colour bars
│   ├── 🤖 advisor.py         # LLM advisor — generates CSS fix suggestions & writes to file
│   └── 👤 persona.json       # 5 audience personas with preferences & dealbreakers
├── 📁 tests/
│   ├── 📦 __init__.py
│   ├── 🔧 conftest.py        # Shared test fixtures
│   ├── 🧪 test_scorer.py     # Scorer unit tests
│   └── 🧪 test_extractor.py  # Extractor smoke tests
├── 🔒 .env                   # API keys (gitignored)
├── 🔒 .gitignore
└── 📖 README.md              # You are here ✨
```

### Module Responsibilities

| File | Purpose |
|---|---|
| `cli.py` | Click decorators, persona loading, error handling, JSON/terminal output routing |
| `extractor.py` | Launches headless Chromium, evaluates a single JS blob that extracts 12+ UI properties |
| `scorer.py` | 5 scoring functions + dealbreaker checker; clean swap‑in point for ML models ✨ |
| `reporter.py` | Rich‑powered terminal output — responsive to narrow/wide terminals |
| `advisor.py` | Builds prompt, calls OpenRouter API, parses JSON response, writes CSS fix files |
| `persona.json` | 5 personas, each with ~8 preference keys + ~3 dealbreakers + research citation |

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
- [x] Playwright‑based UI property extraction (colors, fonts, density, DOM depth, animations, interactivity)
- [x] 5 research‑backed audience personas with preferences & dealbreakers
- [x] Rule‑based heuristic scoring engine (5 dimensions + dealbreaker penalties)
- [x] Responsive Rich terminal reporter (adapts to wide & narrow terminals)
- [x] `--json` output flag for automation / CI pipelines (Rich output suppressed for clean piping)
- [x] `--fix` flag: AI‑generated CSS fix suggestions via OpenRouter / Groq
- [x] `--output` / `-o` flag: custom CSS fix file path
- [x] pip‑installable package with `ui-auditer` CLI entry point
- [x] 53 unit tests (scorer + extractor)

### 🔜 Planned
- [ ] `--compare` flag — score against all 5 personas in a single run
- [ ] 📸 Screenshot capture for visual documentation in reports
- [ ] 🎨 WCAG contrast ratio calculation from extracted colour values
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
git clone https://github.com/yourusername/ui-auditer.git
cd ui-auditer

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
