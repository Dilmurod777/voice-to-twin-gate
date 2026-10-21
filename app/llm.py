"""One call to a local model, constrained to the action vocabulary.

If no model answers, a keyword matcher stands in and the page says which one parsed the
command — an arm that looks like an LLM and is a lookup table would be a lie.
"""

import json
import os
import re
import urllib.request

from app.schema import Action

ENDPOINT = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434/api/chat")
MODEL = os.environ.get("OLLAMA_MODEL", "qwen3.8-27b")

VERB_WORDS = {
    "remove": "remove",
    "take": "remove",
    "pull": "remove",
    "unscrew": "remove",
    "open": "open",
    "crack": "open",
    "depressurise": "depressurise",
    "depressurize": "depressurise",
    "bleed": "depressurise",
    "fit": "fit",
    "install": "fit",
    "replace": "fit",
    "show": "inspect",
    "inspect": "inspect",
    "display": "inspect",
    "look": "inspect",
    "close": "close",
}

NOUNS = {
    "panel": "access_panel",
    "filter": "fuel_filter",
    "element": "fuel_filter",
    "valve": "fuel_valve",
    "pump": "hydraulic_pump",
    "gear": "landing_gear",
    "cowl": "engine_cowl",
    "system": "fuel_system",
    "wing": "wing",
    "door": "cargo_door",
}

# What a pair of plain words maps to in the policy. Absent here means the gate should see
# the words as spoken, not a guess.
PAIRS = {
    ("open", "access_panel"): ("open_panel", "access_panel"),
    ("remove", "access_panel"): ("open_panel", "access_panel"),
    ("open", "fuel_valve"): ("open_valve", "fuel_valve"),
    ("close", "access_panel"): ("close_panel", "access_panel"),
    ("remove", "fuel_filter"): ("remove_filter", "fuel_filter"),
    ("remove", "hydraulic_pump"): ("remove_pump", "hydraulic_pump"),
    ("fit", "fuel_filter"): ("fit_filter", "fuel_filter"),
    ("depressurise", "fuel_system"): ("depressurise", "fuel_system"),
    ("inspect", "landing_gear"): ("inspect", "landing_gear"),
    ("inspect", "engine_cowl"): ("inspect", "engine_cowl"),
}

SYSTEM = """You turn one spoken aircraft-maintenance command into JSON: {{"verb": ..., "part": ...}}.

These are the actions the aircraft knows, as verb|part — the words a person uses:
{vocabulary}

Pick the entry that matches what the person asked, and answer with exactly its verb and
part. If nothing in the list matches, return the words they actually used, so the
validator can refuse it. Never invent a part that was not mentioned. Never add fields."""


def keyword_parse(text: str) -> Action:
    words = re.findall(r"[a-z]+", text.lower())
    verb = next((VERB_WORDS[w] for w in words if w in VERB_WORDS), None)
    noun = next((NOUNS[w] for w in words if w in NOUNS), None)
    if verb and noun:
        mapped = PAIRS.get((verb, noun), (verb, noun))
        return Action(verb=mapped[0], part=mapped[1])
    return Action(verb=verb or "unknown", part=noun)


def llm_parse(text: str, actions: dict) -> Action:
    vocabulary = "\n".join(
        f"- {key} — {spec['label']}" for key, spec in sorted(actions.items())
    )
    body = json.dumps(
        {
            "model": MODEL,
            "stream": False,
            "format": {
                "type": "object",
                "properties": {"verb": {"type": "string"}, "part": {"type": "string"}},
                "required": ["verb", "part"],
            },
            "messages": [
                {
                    "role": "system",
                    "content": SYSTEM.format(vocabulary=vocabulary),
                },
                {"role": "user", "content": text},
            ],
            "options": {"temperature": 0, "num_predict": 80},
            "think": False,
        }
    ).encode()
    request = urllib.request.Request(
        ENDPOINT, data=body, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        payload = json.loads(response.read())
    answer = json.loads(payload["message"]["content"])
    return Action(verb=answer["verb"], part=answer.get("part") or None)


def parse(text: str, actions: dict) -> tuple[Action, str]:
    try:
        return llm_parse(text, actions), "model"
    except Exception:
        return keyword_parse(text), "keyword"
