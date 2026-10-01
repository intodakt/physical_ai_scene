"""
S5 - Query Parser
------------------
Sends the user's plain-English question to a LOCAL LLM (via Ollama) and
gets back a strict, structured JSON intent. No internet / API key needed -
the model runs on your own machine.

Setup (one time, in your terminal):
    pip install ollama
    ollama pull qwen3:8b

Run:
    python parser.py "Which free chair is closest to the lidar scanner?"
"""

import json
import os
import re
import sys

import ollama

# Change the model without editing code:  S5_MODEL=llama3.1:8b python main.py "..."
MODEL_NAME = os.environ.get("S5_MODEL", "qwen3:8b")

SYSTEM_PROMPT = """You are a spatial query parser for a robot's scene understanding system.
Convert the user's question into ONLY this exact JSON format, nothing else, no explanation:

{
  "intent": "find_object",
  "target": "...",
  "reference": "...",
  "relations": ["..."],
  "positive_constraints": [],
  "negative_constraints": []
}

Rules:
- "target" is the object type being searched for (e.g. "chair", "mug").
- "reference" is the object the target is being compared to (e.g. "mug", "lidar scanner").
  If there is no reference object, use an empty string "".
- "relations" can include values like "closest_to", "near", "under", "on".
- "negative_constraints" should describe anything the answer must AVOID,
  e.g. ["near the laptop"]. Leave empty if none.
- Output ONLY valid JSON. No markdown, no extra text.
"""


def _clean_llm_text(raw_text: str) -> str:
    """Remove <think>...</think> blocks and ```json fences some models add."""
    raw_text = re.sub(r"<think>.*?</think>", "", raw_text, flags=re.DOTALL).strip()
    if raw_text.startswith("```"):
        raw_text = raw_text.strip("`")
        raw_text = raw_text.replace("json", "", 1).strip()
    return raw_text


def parse_query(question: str, model: str = None) -> dict:
    model = model or MODEL_NAME
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": question},
    ]
    try:
        # format="json" forces valid JSON; think=False turns off qwen3's long thinking.
        response = ollama.chat(model=model, messages=messages, format="json", think=False)
    except TypeError:
        # Older ollama python package without the `think` option.
        response = ollama.chat(model=model, messages=messages, format="json")
    raw_text = _clean_llm_text(response["message"]["content"])

    try:
        return json.loads(raw_text)
    except json.JSONDecodeError:
        return {
            "error": "Could not parse LLM output as JSON",
            "raw_output": raw_text,
        }


if __name__ == "__main__":
    question = " ".join(sys.argv[1:]) or "Which free chair is closest to the lidar scanner?"
    print(f"Question: {question}\n")
    result = parse_query(question)
    print(json.dumps(result, indent=2))
