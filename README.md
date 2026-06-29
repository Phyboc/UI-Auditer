# 🎯 UI-Audit

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue)](https://python.org)
[![Playwright](https://img.shields.io/badge/Playwright-✓-green)](https://playwright.dev/python)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> **Know your audience before they even see your UI.**  
> A CLI tool that evaluates any website's UI against target audience preferences – instantly.

---

## 📌 The Problem

Solo developers, hackathon participants, and indie hackers often build UIs that **look fine to them** but **miss the mark** for their actual users.  
You don't have a UX researcher – but you _do_ have this tool.

## 🚀 What It Does

- **Audits any live website** (React, Vue, Next.js, plain HTML – anything a browser can render)
- **Scores** the UI against 5 pre‑built audience personas (Gen‑Z, Elderly, Corporate, etc.)
- **Gives actionable recommendations** – not just numbers, but what to fix
- **Detects dealbreakers** – patterns that will instantly turn off a specific audience

## ✨ Features

- 🎨 **Rendered‑style extraction** – uses a real browser (Playwright) so you get _actual_ computed colors, fonts, and layout – no static code guessing.
- 📊 **Rich terminal reports** – beautiful tables, progress bars, and color swatches.
- 🔌 **Supports any framework** – because it renders the page, not parses source code.
- 🧠 **Rule‑based scoring** – transparent and explainable; can be extended with ML later.
- ⚡ **Fast** – 3–5 seconds per audit.

---

## 📦 Installation

```bash
# 1. Clone the repo
git clone https://github.com/yourusername/ui-audit.git
cd ui-audit

# 2. Install dependencies
pip install playwright typer rich click
playwright install chromium