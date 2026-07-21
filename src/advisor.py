import os
import json
from dotenv import load_dotenv
from extractor import UIProperties
import requests
from rich.console import Console
import re 

console = Console()

load_dotenv()


def build_prompt(props: UIProperties, persona: dict, result: dict) -> str:
    return f"""You are a senior UI/UX engineer giving a code review.
        A webpage was evaluated for the audience: "{persona['name']}".
        Overall score: {result['overall_score']}/100 (Grade: {result['grade']})
        
        --- Extracted UI Properties ---
        Dark mode:      {props.is_dark_mode}
        Fonts:          {', '.join(props.fonts[:5]) or 'none detected'}
        Font sizes:     {', '.join(props.font_sizes[:8]) or 'none detected'}
        Text density:   {props.text_density:.1%}
        Has animations: {props.has_animations}
        Buttons:        {props.buttons_count}
        Links:          {props.links_count}
        DOM elements:   {props.total_elements}
        
        --- Issues Found ---
        {chr(10).join(f'- {r}' for r in result['recommendations']) or 'None'}
        
        --- Dealbreakers Triggered ---
        {chr(10).join(f'- {d}' for d in result['dealbreakers_triggered']) or 'None'}
        
        --- Audience Preferences ---
        {json.dumps(persona.get('preferences', {}), indent=2)}
        
        Respond with ONLY valid JSON, no markdown, no explanation outside the JSON:
        {{
        "summary": "One sentence: what is the biggest problem with this UI for this audience.",
        "css_fixes": [
            {{
            "selector": "CSS selector",
            "property": "CSS property",
            "value": "new value",
            "reason": "why this helps this specific audience"
            }}
        ],
        "non_css_suggestions": [
            "Actionable suggestion that cannot be fixed with CSS alone"
        ]
        }}
        
        Limit to 5 css_fixes and 3 non_css_suggestions. Be specific and audience-aware."""


def call_llm(prompt: str) -> str:
    llm_api_key = os.getenv("LLM_API_KEY")
    if not llm_api_key:
        raise ValueError("LLM_API_KEY must be set in the environment variables.")

    # Use LLM_MODEL from env, default to a known-working free model on OpenRouter
    model = os.getenv("LLM_MODEL", "google/gemini-2.0-flash-exp:free")

    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {llm_api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/Phyboc/UI-Auditer",
        },
        json={
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3,
            "max_tokens": 1024,
        },
        timeout=30,
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]

def _parse_json(raw: str) -> dict:
    raw = raw.strip()
    raw = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()
    if raw.startswith("```"):
        lines = raw.split("\n")
        raw = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
    return json.loads(raw.strip())

def get_suggestions(props: UIProperties, persona: dict, result: dict) -> dict:
    """
    Generate fix suggestions for the audit results.

    Tries the LLM first. If it fails, falls back to generating suggestions
    directly from the scoring results so the user still gets actionable feedback.
    """
    prompt = build_prompt(props, persona, result)

    try:
        raw_response = call_llm(prompt)
        suggestions = _parse_json(raw_response)
    except Exception as fallback_error:
        console.print(f"[yellow]Warning: LLM call failed ({fallback_error}). Using rule-based fallback suggestions.[/yellow]")
        suggestions = _build_fallback_suggestions(props, persona, result)

    return suggestions


def _build_fallback_suggestions(props: UIProperties, persona: dict, result: dict) -> dict:
    """Build audience-aware fallback suggestions from the scoring results alone."""
    persona_name = persona.get("name", "this audience")
    recommendations = result.get("recommendations", [])
    dealbreakers = result.get("dealbreakers_triggered", [])
    breakdown = result.get("breakdown", {})

    # Find the worst-scoring dimension
    worst_dim = min(breakdown, key=breakdown.get) if breakdown else "unknown"
    dim_labels = {
        "dark_mode": "Color scheme",
        "typography": "Typography",
        "visual_density": "Visual density",
        "animations": "Motion/animations",
        "interactivity": "Interactivity",
    }
    worst_label = dim_labels.get(worst_dim, worst_dim)

    summary = (
        f"The UI scores {result['overall_score']}/100 (Grade {result['grade']}) "
        f"for {persona_name}. The weakest area is **{worst_label}** "
        f"({breakdown.get(worst_dim, '?')}/100)."
    )

    # Build CSS fix suggestions from recommendations and extracted properties
    css_fixes = []

    # Typography fixes — most common actionable issue
    if breakdown.get("typography", 100) < 70:
        min_size = persona.get("preferences", {}).get("min_font_size", "14px")
        css_fixes.append({
            "selector": "body, p, span, li",
            "property": "font-size",
            "value": min_size,
            "reason": f"{persona_name} needs a minimum font size of {min_size} for readability."
        })
        css_fixes.append({
            "selector": "h1, h2, h3",
            "property": "font-size",
            "value": "clamp(1.25rem, 3vw, 2rem)",
            "reason": "Use responsive headings to avoid oversized text that overwhelms this audience."
        })

    # Color scheme fix
    if breakdown.get("dark_mode", 100) < 70:
        prefers = persona.get("preferences", {}).get("color_scheme", "")
        if "dark" in prefers:
            css_fixes.append({
                "selector": "body",
                "property": "background-color",
                "value": "#121212",
                "reason": f"{persona_name} strongly prefers dark mode."
            })
            css_fixes.append({
                "selector": "body",
                "property": "color",
                "value": "#e0e0e0",
                "reason": "Light text on dark background for comfortable reading."
            })
        elif "light" in prefers:
            css_fixes.append({
                "selector": "body",
                "property": "background-color",
                "value": "#ffffff",
                "reason": f"{persona_name} strongly prefers light mode."
            })

    # Animation fix
    if breakdown.get("animations", 100) < 70:
        css_fixes.append({
            "selector": "*, *::before, *::after",
            "property": "animation",
            "value": "none !important",
            "reason": f"{persona_name} prefers reduced motion. Disabling animations improves focus."
        })
        css_fixes.append({
            "selector": "*, *::before, *::after",
            "property": "transition",
            "value": "none !important",
            "reason": "Remove transitions to eliminate distracting motion."
        })

    # Visual density fix
    if breakdown.get("visual_density", 100) < 70:
        density = persona.get("preferences", {}).get("visual_density", "moderate")
        if density in ("very_low", "low"):
            css_fixes.append({
                "selector": ".container, main, section",
                "property": "max-width",
                "value": "720px",
                "reason": f"{persona_name} prefers low-density layouts. Narrower content width reduces overwhelm."
            })
            css_fixes.append({
                "selector": "p, li",
                "property": "line-height",
                "value": "1.8",
                "reason": "Increased line-height improves readability for sparse, clean layouts."
            })
        else:
            css_fixes.append({
                "selector": ".container, main",
                "property": "max-width",
                "value": "1200px",
                "reason": f"{persona_name} prefers dense, information-rich layouts. Wider container fits more content."
            })

    # Limit to 5 CSS fixes
    css_fixes = css_fixes[:5]

    # Build non-CSS suggestions from the recommendations
    non_css_suggestions = []
    if recommendations:
        for r in recommendations[:3]:
            non_css_suggestions.append(r)
    else:
        non_css_suggestions.append(
            f"Review the UI against {persona_name}'s preferences to identify improvements beyond CSS."
        )

    if dealbreakers:
        for d in dealbreakers[:2]:
            non_css_suggestions.append(f"Resolve dealbreaker: {d}")

    return {
        "summary": summary,
        "css_fixes": css_fixes,
        "non_css_suggestions": non_css_suggestions[:3],
    }


def write_css_fix_file(suggestions: dict, output_path: str = "suggested_fixes.css") -> str:
    """Write CSS fixes to a file the user can drop into their project."""
    lines = [
        "/* UI-Auditer: Suggested CSS Fixes */",
        f"/* {suggestions.get('summary', '')} */",
        "",
    ]
    for fix in suggestions.get("css_fixes", []):
        lines.append(f"/* {fix['reason']} */")
        lines.append(f"{fix['selector']} {{")
        lines.append(f"  {fix['property']}: {fix['value']};")
        lines.append("}")
        lines.append("")
 
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
 
    return output_path
