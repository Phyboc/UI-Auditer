import os
import json
from dotenv import load_dotenv
from extractor import UIProperties
import requests
from rich.console import Console
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
    # llm_url = os.getenv("LLM_URL")
    llm_api_key = os.getenv("LLM_API_KEY")
    if not llm_api_key:
        raise ValueError("LLM_URL and LLM_API_KEY must be set in the environment variables.")
    
    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {llm_api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/Phyboc/UI-Auditer",
        },
        json={
            "model": "qwen/qwen3-coder:free", #meta-llama/llama-3.3-70b-instruct:free
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
    if raw.startswith("```"):
        lines = raw.split("\n")
        raw = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
    return json.loads(raw.strip())

def get_suggestions(props: UIProperties, persona: dict, result: dict) -> dict:

    prompt = build_prompt(props, persona, result)

    try: 
        raw_response = call_llm(prompt)
        suggestions = _parse_json(raw_response)
    except Exception as fallback_error:
        console.print(f"[yellow]Warning: LLM call failed: {fallback_error}. Using fallback suggestions.[/yellow]")
        suggestions = {
            "summary": "The UI has multiple issues that make it hard to use for this audience.",
            "css_fixes": [],
            "non_css_suggestions": ["Consider a complete redesign to better suit the target audience."]
        }
    return suggestions


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
