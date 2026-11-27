# S6 — Tracking & Action (reference implementation, to be reviewed by S6)

> **Authorship.** `src/tracking/` and `src/planning/` were written with Claude Code (AI) as a
> reference implementation of the professor's roadmap §11.6, so that the integrated platform no
> longer runs on the placeholder. S6 (Erkinov Shakhzodjon) reviews, changes or replaces it and
> states this in the S6 report. The Week-5 behaviour S6 presented is kept unchanged in
> `src/integration/s6_placeholder.py` and is now the **baseline**.

## Tracking — `src/tracking/tracker.py` (`MultiTermTracker`)

| Roadmap item | Where |
|---|---|
| Multi-term / Hungarian association | cost = position (to the velocity-predicted centre) + label (+ shared label candidates) + size; `assignment.py` (Hungarian, no SciPy) |
| Track states | `observed` → `occluded` (confidence × 0.85 per hidden frame) → `removed` after `max_missed_frames` |
| Re-identification | occluded tracks match up to `reid_gate_m` (60 cm) away: picked up and put down elsewhere |
| Events | `APPEARED`, `MOVED` (rest position changed > 3 cm), `OCCLUDED`, `REAPPEARED`, `PICKED_UP` / `PLACED_ON` (box bottom > 3 cm above the desk, and back), `REMOVED` |
| Deliverables | TrackState JSON per frame (`outputs/pipeline/tracking/<frame>_track_state.json`), `event_log.jsonl`, `history(pid)` for temporal queries |

The output contract is unchanged: `update(objects)` only writes `persistent_id` (format `<label>_NN`).

## Action — `src/planning/action.py` (ActionGoal v2)

Reason codes: `OK`, `OK_DETOUR`, `TARGET_UNVERIFIED`, `TARGET_NOT_IN_GRAPH`, `TARGET_OCCLUDED`
(position only remembered), `TARGET_IN_EXCLUSION_ZONE`, `PATH_BLOCKED`; plus `path`, `clearance_m`
and `warnings` (`LOW_TARGET_CONFIDENCE`). `planner: straight` (default, Week-5 rule) or `detour`
(grid A* around the inflated zones with a clearance) in `configs/s7_integration.yaml`.

## Evaluation

`python scripts/s6_tracking_eval.py` → [tracking_eval/README.md](tracking_eval/README.md):
ID switches, re-identification success and event delay on five synthetic scenarios (static,
relocation, occlusion, slide, crossing), baseline vs multi-term, plus ID stability on the real
static bag. Tests: `tests/test_s6_tracking_planning.py`.

Open items for S6: label the real relocation / occlusion bags with ground-truth identities and
run the same metrics on them; decide whether `planner: detour` should become the default.

## W12–W16 evaluation (S6) — professor's step-by-step guide

- Tracking GT tied to detections, so the baseline (15 cm gate) and the multi-cue tracker (Hungarian: distance + label + size [+ appearance, `w_app`]) are scored on one file:
  `python -m src.evaluation.s6_tracking_eval plan | sheet --run <run> | score --runs <runs> [--frames-root <frames>]`
- 60 action trials (30 safe / 30 unsafe, independent geometric labels): `python -m src.evaluation.s6_tracking_eval actions --graph <graph>`
  First result (real static-bag graph, generated targets): unsafe rejected 100 % (30/30), safe accepted 100 % (30/30) — `eval/results/s6/`
- Done means (§16): ≥ 30 real tracking sequences and 60 action trials with quantitative tracking / safety metrics.

Full workflow and the shared dataset: [`eval/README.md`](../../eval/README.md).
