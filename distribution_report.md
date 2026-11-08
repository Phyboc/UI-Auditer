# Scoring distribution: before vs after

Generated 2026-11-08 from `scripts/distribution.py`.

- Pages attempted: **24**, scored successfully: **22**
- Viewport 1280x800, headless Chromium, page-load timeout 25s.
- "Before" = commit `3834a44` (pre-fix) run from a temporary git worktree.
- "After" = current working tree.

## Per persona

| Persona | Mean before | Mean after | Delta | Improved | Regressed | Dealbreakers before | Dealbreakers after |
|---|---|---|---|---|---|---|---|
| `gen_z_tech_early_adopter` | 54.1 | 58.8 | +4.7 | 20 | 1 | 20 | 1 |
| `elderly_digital_novice` | 49.6 | 49.8 | +0.2 | 11 | 3 | 20 | 22 |
| `corporate_power_user` | 55.7 | 55.2 | -0.5 | 6 | 4 | 21 | 24 |
| `minimalist_creative` | 65.2 | 64.9 | -0.3 | 9 | 4 | 18 | 21 |
| `neurodivergent_focus_optimizer` | 57.1 | 57.7 | +0.5 | 11 | 3 | 20 | 20 |

## Per page

| Page | `gen_z_tech_early_adopter` | `elderly_digital_novice` | `corporate_power_user` | `minimalist_creative` | `neurodivergent_focus_optimizer` |
|---|---|---|---|---|---|
| https://example.com | 51 → 56 C (+5) | 82 → 82 B | 71 → 71 B | 77 → 77 B | 92 → 92 A |
| https://python.org | 65 → 66 C (+1) | 38 → 38 F | 58 → 59 C (+1) | 60 → 61 C (+1) | 68 → 69 C (+1) |
| https://pypi.org | 51 → 57 C (+6) | 55 → 50 D (-5) | 60 → 61 C (+1) | 58 → 59 C (+1) | 64 → 65 C (+1) |
| https://github.com | 63 → 68 C (+5) | 34 → 36 F (+2) | 56 → 56 C | 73 → 73 B | 46 → 47 D (+1) |
| https://gitlab.com | 59 → 65 C (+6) | 39 → 35 F (-4) | 50 → 50 D | 69 → 69 C | 44 → 45 D (+1) |
| https://stackoverflow.com | 65 → 70 B (+5) | 42 → 43 D (+1) | 59 → 55 C (-4) | 70 → 66 C (-4) | 46 → 52 D (+6) |
| https://wikipedia.org | 56 → 61 C (+5) | 47 → 48 D (+1) | 72 → 73 B (+1) | 64 → 64 C | 75 → 75 B |
| https://mozilla.org | 67 → 73 B (+6) | 51 → 52 D (+1) | 46 → 46 D | 75 → 76 B (+1) | 52 → 58 C (+6) |
| https://developer.mozilla.org | 50 → 55 C (+5) | 59 → 59 C | 62 → 62 C | 52 → 52 D | 62 → 62 C |
| https://w3.org | 55 → 60 C (+5) | 64 → 65 C (+1) | 55 → 55 C | 64 → 64 C | 74 → 74 B |
| https://gov.uk | 37 → 43 D (+6) | 61 → 63 C (+2) | 54 → 55 C (+1) | 45 → 46 D (+1) | 56 → 52 D (-4) |
| https://bbc.co.uk | 50 → 55 C (+5) | 51 → 51 D | 68 → 68 C | 63 → 63 C | 67 → 62 C (-5) |
| https://theguardian.com | 42 → 48 D (+6) | 53 → 55 C (+2) | 59 → 54 D (-5) | 56 → 51 D (-5) | 58 → 60 C (+2) |
| https://nytimes.com | 21 → 26 F (+5) | 74 → 74 B | 43 → 43 D | 72 → 72 B | 64 → 64 C |
| https://cnn.com | — | — | — | — | — |
| https://apple.com | 64 → 64 C | 33 → 34 F (+1) | 58 → 58 C | 58 → 59 C (+1) | 34 → 35 F (+1) |
| https://microsoft.com | 48 → 53 D (+5) | 53 → 53 D | 62 → 62 C | 57 → 58 C (+1) | 67 → 67 C |
| https://stripe.com | 56 → 62 C (+6) | 40 → 41 D (+1) | 43 → 44 D (+1) | 64 → 66 C (+2) | 39 → 41 D (+2) |
| https://vercel.com | 64 → 70 B (+6) | 34 → 35 F (+1) | 57 → 53 D (-4) | 72 → 68 C (-4) | 49 → 50 D (+1) |
| https://react.dev | 54 → 60 C (+6) | 38 → 40 D (+2) | 46 → 47 D (+1) | 63 → 64 C (+1) | 37 → 39 F (+2) |
| https://tailwindcss.com | 77 → 75 B (-2) | 25 → 23 F (-2) | 54 → 51 D (-3) | 71 → 68 C (-3) | 47 → 44 D (-3) |
| https://npmjs.com | — | — | — | — | — |
| https://reddit.com | 34 → 39 F (+5) | 77 → 77 B | 39 → 39 F | 79 → 79 B | 71 → 71 B |
| https://notion.so | 61 → 67 C (+6) | 41 → 41 D | 53 → 53 D | 72 → 73 B (+1) | 45 → 45 D |

## Could not be scored

- https://cnn.com — `TimeoutError: Page.goto: Timeout 25000ms exceeded.
Call log:
  - navigating to "https://cnn.com/", waiting until "networkidle"
`
- https://npmjs.com — `TimeoutError: Page.goto: Timeout 25000ms exceeded.
Call log:
  - navigating to "https://npmjs.com/", waiting until "networkidle"
`
