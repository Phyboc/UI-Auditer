import os
import json
from dotenv import load_dotenv
from extractor import UIProperties
import requests
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
    llm_url = os.getenv("LLM_URL")
    llm_api_key = os.getenv("LLM_API_KEY")
    if not llm_url or not llm_api_key:
        raise ValueError("LLM_URL and LLM_API_KEY must be set in the environment variables.")
    
    