# S4 - Scene Graph Engine

**Owner:** Student 4 (Jaloliddin). Pure deterministic geometry, no ML. Built with NetworkX.

S2's `ObjectInstance3D` objects become graph nodes. Geometric rules create edges, and every edge
carries the measured numbers that prove it. The result is the Scene Graph JSON that S5 reads.

## Run
```bash
pip install networkx pytest
python -m src.scene_graph.run_scene_graph --objects data/mock/s2_frame_000_objects.json \
       --out outputs/scene_graph/frame_000_scene_graph.json
python -m src.scene_graph.run_scene_graph --objects <S2 file> --watch    # rewrite every second
python -m pytest tests/test_s4_scene_graph.py
```
Use the result in S5 with `S5_GRAPH=outputs/scene_graph/frame_000_scene_graph.json`.

## Input (from S2): `*_objects.json`
Uses the **map frame** (z up): `box_map.center` and `box_map.dimensions` (`[W, H, D]`, H vertical).
Uses `centroid[0]` (camera optical frame, x right) for `left_of`. Node id is `persistent_id` (S6)
when set, else `object_id`.

## Rules (src/scene_graph/rules.py)
| Predicate | Holds when | Evidence |
|---|---|---|
| `near` | centre distance < 0.30 m (one edge per pair) | `distance_m` |
| `on` | A's bottom is within 3 cm of B's top, A is above B, >= 30% of A's footprint is over B | `vertical_gap_m`, `xy_overlap` |
| `left_of` | B is more than 5 cm to the right of A in the camera frame | `dx_m` |

## The desk
**Desk-aligned frame.** If the S2 frame has `support_plane` and `T_map_camera`, S4 measures heights
above the desk plane itself (`levelling.py`), so a wrong or placeholder map TF does not break `on`.
The export says how it was done in `desk_alignment`. Without a support plane it falls back to `desk_top_z`.

S2 removes the desk from the objects (support-plane RANSAC), so S4 adds a **virtual** `desk_01`
node whose top is at `desk_top_z` (default 0.0, the map origin of S2's mock frame). It only takes
part in `on`. Set `--desk-top-z` if S1's real map frame puts the table elsewhere.

## Output (to S5)
Same shape as `src/reasoning/sample_scene_graph.json`: `nodes` (`id`, `persistent_object_id`, `names`,
`pose_map`, `size` as `[width_x, depth_y, height_z]`, `state`, `first_seen`, `last_seen`, `confidence`,
`depth_confidence`) and `edges` (`source`, `predicate`, `target`, `relation_type`, `evidence`,
`confidence`, `start_time`, `end_time`).

Over time: a moved object updates its existing node. A relation that stops holding gets an
`end_time` (S5 ignores ended edges). An object that disappears is kept with `state: "occluded"`.

## Not done yet
- Real S1 data (needs S2's output on the real bag, and S1's map frame / desk height).
- `right_of`, `occupied_by`, `carried_by` (the S5 sample has the last two; S4 only emits `on`, `near`, `left_of`).
