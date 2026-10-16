# S5 — Vision-Language Spatial Reasoning (Language Verifier)

**Owner:** Student 5
**Status:** Built and tested against sample/fake data. Will switch to S4's real Scene Graph output once it's ready.

## What this module does
Takes a plain-English spatial question (e.g. "Which free chair is closest to the lidar scanner?"),
parses it into structured JSON using a local LLM, then verifies the answer against the real 3D
positions in the Scene Graph — so the final answer is backed by geometry, not just an AI guess.

## Files
- `sample_scene_graph.json` — fake Scene Graph (stand-in for S4's real output), used for testing.
- `query_parser.py` — sends the question to a local LLM (Ollama) and returns structured JSON.
- `verifier.py` — the geometry math: closest object, "not near" filtering, object location.
- `main.py` — runs the full pipeline: question → parsed JSON → verified answer.
- `test_verifier.py` — unit tests for the verifier (no LLM needed).
- `test_parser.py` — runs 7 questions through a model and prints PASS/FAIL + seconds (compare models).
- `requirements.txt` — Python dependencies for this module.

## Setup
```bash
pip install -r requirements.txt
ollama pull qwen2.5:3b      # default model (1.9 GB, light enough for a laptop)
```

## Run
```bash
python3 main.py "Which free chair is closest to the lidar scanner?"
python3 main.py "Find a chair that is not near the laptop"
python3 main.py "Where is the red mug?"
python3 main.py --json "Where is the red mug?"   # full ReasoningResult JSON (what S6 gets)
python3 test_verifier.py
python3 test_parser.py                        # 7 parser questions with the default model
S5_MODEL=llama3.2:3b python3 main.py "..."     # try another model
S5_GRAPH=path/to/real_graph.json python3 main.py "..."   # use S4's real graph
```

## Input contract (from S4)
Scene Graph JSON. `sample_scene_graph.json` shows the exact shape (14 nodes, 17 edges: a desk with
laptop, mug, book, apple, pen, soldering iron, multimeter, a new lidar scanner, 4 chairs and a person).
It is marked `"sample": true` and uses one frame (`map`) and meters.

Top level: `schema_version`, `sample`, `session_id`, `frame`, `units`, `size_order`, `timestamp`, `nodes`, `edges`.

**Node:** `id`, `persistent_object_id`, `names` (list of `{text, score}`), `pose_map` `[x, y, z]` (centroid),
`size` `[width_x, depth_y, height_z]`, `state` (`static`, `free`, `occupied`, `occluded`, ...),
`first_seen`, `last_seen`, `confidence`, `depth_confidence`, optional `history` (older poses).

**Edge:** `source`, `predicate`, `target`, `relation_type`, `evidence` (the metric proof, e.g. `distance_m`,
`vertical_gap_m`, `xy_overlap`), `confidence`, `start_time`, `end_time` (`null` = still true;
a number = the relation already ended).

Predicates in the sample: `on`, `near` (< 0.3 m), `left_of`, `occupied_by`, `carried_by`.
"Not near" is checked with the `near` edge AND the real distance (< 0.3 m), so it still works if S4 skips an edge.
Other negative rules ("not on the desk") use the matching edge; if that edge type does not exist, a warning is added.
Object names are matched by whole words ("book" does not match "notebook computer").
The verifier only uses edges whose `end_time` is `null`. When S4's real output has the same shape,
set the `S5_GRAPH` environment variable to the real file.

## Output contract (to S6)
```json
{
  "target_id": "chair_04",
  "computed_facts": "distance to obj_27: chair_04 0.65m, chair_01 0.89m, chair_03 1.36m",
  "verification_status": true,
  "final_answer": "The closest chair to the lidar scanner is chair_04, verified at 0.65 meters.",
  "confidence": 0.82,
  "warnings": []
}
```
If the answer cannot be proven from the graph, `target_id` is `null`, `verification_status` is `false`
and `final_answer` starts with "Cannot determine". `warnings` lists occluded or low-confidence objects
and constraints that could not be checked (for example colors).
