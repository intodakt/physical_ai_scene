"""
S5 - Query Parser
------------------
Sends the user's plain-English question to a LOCAL LLM (via Ollama) and
gets back a strict, structured JSON intent. No internet / API key needed -
the model runs on your own machine.

Setup (one time, in your terminal):
    pip install ollama
    ollama pull qwen2.5-coder

Run:
    python parser.py "Which free chair is closest to the lidar scanner?"
"""

import json
import sys

import ollama

MODEL_NAME = "qwen2.5-coder"

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


def parse_query(question: str) -> dict:
    response = ollama.chat(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": question},
        ],
    )
    raw_text = response["message"]["content"].strip()

    # Local LLMs sometimes wrap JSON in ```json fences - strip those if present.
    if raw_text.startswith("```"):
        raw_text = raw_text.strip("`")
        raw_text = raw_text.replace("json", "", 1).strip()

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
