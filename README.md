# UI-Auditer

> A CLI tool that evaluates any webpage's UI against target audience preferences — and tells you exactly what to fix.

---

## The Problem

When I built my hackathon project, the UI was functional but was terrible. I'd designed it for myself, not for the actual audience. I had no way to know that until it was too late.

Most developers face this. You can't afford a UX researcher. Lighthouse only checks performance and accessibility. Nothing tells you *"this interface feels wrong for a 60-year-old"* or *"Gen-Z users will bounce because you used light mode."*

UI-Audit fills that gap.

---

## What It Does

Point it at any URL. Tell it who your audience is. Get a scored report with specific, actionable recommendations.

```bash
python cli.py https://yoursite.com --persona gen_z
python cli.py https://yoursite.com --persona elderly
python cli.py http://localhost:3000 --persona corporate
```

It uses a **headless Chromium browser** (via Playwright) to fully render the page — including React, Next.js, Vue, Tailwind, anything — then extracts computed styles the way a real browser sees them. No static HTML parsing tricks that miss 90% of the styles.

---

## Personas Included

| Slug | Audience | Key Preferences |
|------|----------|-----------------|
| `gen_z` | Gen-Z Tech Early Adopter | Dark mode, animations, high density, minimal text |
| `elderly` | Elderly Digital Novice | Light mode, large fonts (≥16px), no animations, low density |
| `corporate` | Corporate Power User | Neutral theme, compact fonts (11–14px), no animations, high density |
| `minimalist` | Minimalist Creative | Monochromatic, very low density, subtle animations |
| `neurodivergent` | Neurodivergent Focus Optimizer | Pastel/low-stimulation, no animations, moderate density, no flashing |

Each persona has a preferences profile and a list of dealbreakers — patterns that immediately tank the score regardless of other factors.

---

## What Gets Scored

| Dimension | What It Checks |
|-----------|----------------|
| **Color Scheme** | Dark/light mode match to audience expectation |
| **Typography** | Font size range against persona's min/max requirements |
| **Visual Density** | Text area vs page area ratio against expected density level |
| **Motion** | Presence/absence of CSS animations vs persona preference |
| **Interactivity** | Button + link count vs expected interface complexity |
| **Dealbreakers** | Persona-specific red flags (e.g. animations for neurodivergent audience = penalty) |

Final score: 0–100 with a letter grade (A/B/C/D/F). Each triggered dealbreaker docks 5 points.

---

## Installation

```bash
# 1. Clone
git clone https://github.com/yourusername/ui-audit.git
cd ui-audit

# 2. Install dependencies
pip install playwright click rich

# 3. Install Chromium (one-time)
playwright install chromium
```

---

## Usage

```bash
# Basic audit
python cli.py <url> --persona <slug>

# With extended timeout (for slow local dev servers)
python cli.py http://localhost:3000 --persona gen_z --timeout 30000

# Raw JSON output (for piping or automation)
python cli.py https://example.com --persona corporate --json
```

---

## Project Structure

```
ui-auditer/
├── extractor.py          # Playwright browser engine — extracts computed UI properties
├── scorer.py             # Heuristic engine — scores properties against persona rules
├── reporter.py           # Rich terminal renderer — responsive to terminal width
├── cli.py                # Entry point (Click)
├── persona.json          # All audience persona definitions
└── requirements.txt
```

### How the pipeline works

```
URL
 │
 ▼
extractor.py  ──  Playwright renders page, getComputedStyle() extracts real values
 │                (colors, fonts, DOM depth, density, animations, interactivity)
 ▼
scorer.py     ──  Rule engine compares UIProperties against persona JSON
 │                Each dimension scored 0–100, dealbreakers apply penalties
 ▼
reporter.py   ──  Rich tables + color bars, responsive to terminal width
```

---

## Architecture Decisions

**Why Playwright instead of BeautifulSoup?**
BeautifulSoup reads raw HTML text. It cannot see computed styles from external CSS, Tailwind classes, or JavaScript-rendered components. Playwright launches a real browser, so `getComputedStyle()` returns the actual values the user sees. A React app with Tailwind returns zero useful data to BeautifulSoup.

**Why rule-based heuristics instead of ML?**
Rules ship fast, are fully explainable, and need zero training data. The scoring architecture is deliberately designed so the rule functions can be replaced with ML model predictions later without touching the CLI, reporter, or persona files. See the ML upgrade path below.

**Why a CLI instead of a web app?**
The target users are developers. Developers live in the terminal. A CLI is also pipeable, scriptable, and CI-friendly. A web interface can be added later as a thin wrapper.

---

## Roadmap

### Done
- [x] Playwright-based UI property extraction (colors, fonts, density, DOM, animations)
- [x] 5 research-backed audience personas
- [x] Rule-based heuristic scoring engine with dealbreaker system
- [x] Responsive Rich terminal reporter (wide and narrow terminal layouts)
- [x] JSON output flag for automation

### Next
- [ ] `--fix` flag: generate corrected CSS suggestions via Gemini API
- [ ] `--compare` flag: score against all personas at once
- [ ] Screenshot capture for visual documentation
- [ ] WCAG contrast ratio calculation from extracted colors

### ML Upgrade Path
The scoring engine is structured for a clean ML swap:

```python
# Current: hand-written rules
def score(props: UIProperties, persona: dict) -> dict:
    checks = {
        "dark_mode":  _score_dark_mode(props, prefs),
        "typography": _score_font_sizes(props, prefs),
        ...
    }

# Future: replace _score_*() functions with model predictions
feature_vector = [
    1 if props.is_dark_mode else 0,
    props.text_density,
    props.buttons_count / 100,
    min(font_sizes),
    max(font_sizes),
    1 if props.has_animations else 0,
    props.total_elements / 500,
    props.max_dom_depth / 30,
]
prediction = model.predict([feature_vector])  # sklearn / PyTorch
```

Collect ~200 human-rated (URL, persona, score) examples → train a RandomForest or small MLP → drop it in. CLI, reporter, and personas stay unchanged.

---

## Origin

Built after failing at a Microsoft Agents League Hackathon with a half-finished UI that had zero wow factor. 

---

## Tech Stack

- **Python 3.12**
- **Playwright** — headless Chromium, computed style extraction
- **Rich** — terminal UI, responsive layout
- **Click** — CLI argument parsing
- **JSON** — persona definition format (human-editable, no database needed)
