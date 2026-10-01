# S5 — Vision-Language Spatial Reasoning (Language Verifier)

**Owner:** Student 5
**Status:** Built and tested against sample/fake data. Will switch to S4's real Scene Graph output once it's ready.

## What this module does
Takes a plain-English spatial question (e.g. "Which free chair is closest to the lidar scanner?"),
parses it into structured JSON using a local LLM, then verifies the answer against the real 3D
positions in the Scene Graph — so the final answer is backed by geometry, not just an AI guess.

## Files
- `sample_scene_graph.json` — fake Scene Graph data (stand-in for S4's real output), used for testing.
- `parser.py` — sends the question to a local LLM (via Ollama) and returns structured JSON.
- `verifier.py` — the geometry math: finds candidate nodes, computes real distances, handles
  negative constraints (e.g. "not near X").
- `main.py` — runs the full pipeline: question → parsed JSON → verified answer.
- `requirements.txt` — Python dependencies for this module.

## Setup
```bash
pip install -r requirements.txt
ollama pull qwen3:8b
```

## Run
```bash
python main.py "Which free chair is closest to the lidar scanner?"
python main.py "Find a chair that is not near the laptop"
```

## Input contract (from S4)
Scene Graph JSON with `nodes` (id, names, pose_map, state, confidence) and `edges`
(source, predicate, target, evidence, confidence). See `sample_scene_graph.json` for the exact shape
this module expects — once S4's real output matches this shape, just point `GRAPH_PATH` in
`verifier.py` at the real file.

## Output contract (to S6)
```json
{
  "target_id": "chair_03",
  "computed_facts": "distance to mug_01: 1.35m",
  "verification_status": true,
  "final_answer": "The closest chair to the mug is chair_03, verified at 1.35 meters."
}
```
