"""Query parser (S5): turns a plain-English question into structured JSON with a local Ollama model.
Setup: pip install -r requirements.txt, then: ollama pull qwen2.5:3b
Switch model with the S5_MODEL environment variable. Try: python3 query_parser.py "your question"
"""

import json
import os
import re
import sys
from typing import Optional

import ollama

MODEL_NAME = os.environ.get("S5_MODEL", "qwen2.5:3b")

SYSTEM_PROMPT = """You are a spatial query parser for a robot's scene understanding system.
Convert the user's question into ONLY a JSON object with exactly these keys. No explanation, no markdown.

{
  "intent": "find_object",
  "target": "<object type being searched for, or empty string>",
  "reference": "<object the target is compared to, or empty string>",
  "relations": [],
  "positive_constraints": [],
  "negative_constraints": []
}

Rules:
- "relations" holds positive relations such as "closest_to", "near", "on", "under".
- Anything the answer must AVOID goes in "negative_constraints" as {"relation": "...", "object": "..."}.
  Words like "not", "no", "without", "far from" mean a negative constraint. NEVER write "not_near" in "relations".
- Use an empty string "" when there is no target or no reference. Never write "...".
- Adjectives such as "free" or "red" go in "positive_constraints".

Examples:
Q: Which chair is closest to the mug?
A: {"intent":"find_object","target":"chair","reference":"mug","relations":["closest_to"],"positive_constraints":[],"negative_constraints":[]}
Q: Find a chair that is not near the laptop
A: {"intent":"find_object","target":"chair","reference":"","relations":[],"positive_constraints":[],"negative_constraints":[{"relation":"near","object":"laptop"}]}
Q: Find the book that is not near the mug
A: {"intent":"find_object","target":"book","reference":"","relations":[],"positive_constraints":[],"negative_constraints":[{"relation":"near","object":"mug"}]}
Q: Where is the red mug?
A: {"intent":"find_object","target":"mug","reference":"","relations":[],"positive_constraints":["red"],"negative_constraints":[]}
Q: What is closest to the laptop?
A: {"intent":"find_object","target":"","reference":"laptop","relations":["closest_to"],"positive_constraints":[],"negative_constraints":[]}
"""

_NEG_PATTERN = re.compile(r"(near|under|on|inside|above)\s+(?:the\s+|a\s+|an\s+)?(.+)", re.IGNORECASE)


def _as_list(value):
    if value in (None, ""):
        return []
    return value if isinstance(value, list) else [value]


def _negative_from_dict(item):
    if "object" in item:
        return {"relation": str(item.get("relation") or "near").lower(), "object": item["object"]}
    if len(item) == 1:
        relation, obj = next(iter(item.items()))
        if isinstance(obj, str):
            return {"relation": str(relation).lower().replace("not_", ""), "object": obj}
    return None


def _normalize(parsed):
    for key in ("target", "reference"):
        if parsed.get(key) in (None, "...") or not isinstance(parsed.get(key), str):
            parsed[key] = ""

    negatives = []
    for item in _as_list(parsed.get("negative_constraints")):
        if isinstance(item, dict):
            item = _negative_from_dict(item)
            if item:
                negatives.append(item)
        elif isinstance(item, str):
            m = _NEG_PATTERN.search(item)
            if m:
                negatives.append({"relation": m.group(1).lower(), "object": m.group(2).strip()})

    relations = []
    for rel in _as_list(parsed.get("relations")):
        text = str(rel).lower().replace("_", " ").strip()
        if text.startswith("not "):
            negatives.append({"relation": text[4:].strip(), "object": parsed.get("reference", "")})
            parsed["reference"] = ""
        else:
            relations.append(rel)
    parsed["relations"] = relations

    target = parsed["target"].lower()
    for item in negatives:
        if target and parsed.get("reference") and str(item.get("object", "")).lower() == target:
            item["object"] = parsed["reference"]
            parsed["reference"] = ""
    if parsed["reference"].lower() in {str(n.get("object", "")).lower() for n in negatives}:
        parsed["reference"] = ""
    parsed["negative_constraints"] = negatives

    positives = []
    for item in _as_list(parsed.get("positive_constraints")):
        if isinstance(item, dict):
            positives.extend(k if v is True else f"{k} {v}" for k, v in item.items())
        else:
            positives.append(str(item))
    parsed["positive_constraints"] = positives
    return parsed


def _clean_llm_text(raw_text):
    raw_text = re.sub(r"<think>.*?</think>", "", raw_text, flags=re.DOTALL).strip()
    if raw_text.startswith("```"):
        raw_text = raw_text.strip("`").replace("json", "", 1).strip()
    return raw_text


def _chat(model, messages):
    options = {"temperature": 0}
    try:
        return ollama.chat(model=model, messages=messages, format="json", options=options, think=False)
    except (TypeError, ollama.ResponseError):
        return ollama.chat(model=model, messages=messages, format="json", options=options)


def parse_query(question: str, model: Optional[str] = None) -> dict:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": question},
    ]
    try:
        response = _chat(model or MODEL_NAME, messages)
    except (ollama.ResponseError, ConnectionError, TypeError) as error:
        return {"error": f"Ollama request failed: {error}"}

    raw_text = _clean_llm_text(response["message"]["content"])
    try:
        parsed = json.loads(raw_text)
    except json.JSONDecodeError:
        return {"error": "LLM output is not valid JSON", "raw_output": raw_text}
    if not isinstance(parsed, dict):
        return {"error": "LLM output is not a JSON object", "raw_output": raw_text}
    return _normalize(parsed)


if __name__ == "__main__":
    question = " ".join(sys.argv[1:]) or "Which free chair is closest to the lidar scanner?"
    print(json.dumps(parse_query(question), indent=2))
