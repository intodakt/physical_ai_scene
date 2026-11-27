# G1 — Weeks 12–16 evaluation (professor's step-by-step guide)

This folder holds the **shared evaluation dataset description, the ground truth, the query / task sets and all
results**. The code is in `src/evaluation/`. Every number in the final report comes from a command below; nothing
is typed by hand except the ground truth itself.

> **Who wrote this toolkit.** The evaluation code in `src/evaluation/` (W12) was written with Claude Code (an AI
> coding assistant) from the professor's guide; each owner reviews and runs their part. The *data* — bags, tape
> measurements, annotations, checked queries — must be produced by the team.

Architecture is frozen (guide §1.1): ZED Mini RGB-D bag → S3 → S2 → S6 tracking → S4 → S5 → S6 action → dashboard.

## Folder layout

| Path | What | Who fills it |
|---|---|---|
| `dataset/recording_plan.csv` | 45 planned bags in 8 families (A–H), difficulty, dev/test split | generated (S1 adjusts) |
| `dataset/splits.json` | frozen dev/test split — tune only on **dev**, report only on **test** | generated |
| `dataset/metadata/<bag_id>.yaml` | §2.4 metadata per bag | S1 on the recording day |
| `dataset/dataset_manifest.csv` | what was actually recorded + measured FPS / gaps / sync | generated from the bags |
| `ground_truth/ground_truth_positions.csv` | tape-measured object centres, table frame (≥ 15 scenes) | S1 (+ S2) |
| `ground_truth/detection_annotations.csv` | 2D boxes, seen / unseen (~260–300 appearances) | S3 (+ helpers) |
| `ground_truth/relation_ground_truth.csv` | relation true/false per keyframe (≥ 250, ≥ 20 % double-checked) | S4 (+ second annotator) |
| `ground_truth/temporal_events_ground_truth.csv` | MOVED / PICKED_UP / REAPPEARED times | S4 + S6 |
| `ground_truth/tracking_ground_truth.csv` | GT object id per detection + occluded rows (30 sequences) | S6 |
| `queries/queries_200.csv` | 200 queries with GT answers (generated, then checked) | S5 |
| `tasks/end_to_end_tasks.csv` | 30 end-to-end tasks (10 easy / 10 medium / 10 hard) | S7 |
| `results/s1 … s7/` | every member's CSV / PNG outputs | generated |
| `report/` | Tables 1–7, Figures 1–9, acceptance checklist | generated |

Each ground-truth template contains **one example row starting with `#`**; the scripts ignore it. Keep it as a
format reminder or delete it.

## The table coordinate frame (guide §3.1)

Origin = one fixed table corner (tape cross), **+X along the long edge, +Y along the short edge, +Z up**. All ground
truth positions, the measured camera pose and S2's outputs use this frame (metres).

## Step by step

### S1 — Muzaffar (W12 first: everything metric depends on it)
```bash
python -m src.evaluation.s1_dataset plan            # recording_plan.csv + splits.json (already in git)
python -m src.evaluation.s1_dataset metadata        # one YAML per planned bag (fill on recording day)
# calibration bag (family A, >= 20 checkerboard poses: centre, corners, near/far, tilts)
python -m src.sensors.calibration --bag <bags>/A01_calibration_easy_rep1 --every 15 --pattern 9x6 --square 0.025 --out configs/sensors/
#   -> camera_intrinsics.yaml, calibration_report.json (mean / median / max px), reprojection_overlay_{best,worst}.png
# camera pose measured with tape + inclinometer app in the table frame (replaces the 0.80 m placeholder)
python -m src.evaluation.s1_dataset tf --height <m> --pitch-deg <deg> --x <m> --y <m> --yaw-deg <deg>
python -m src.sensors.static_tf --frames <frames of a static bag>    # cross-check: desk-plane estimate of height / pitch
python -m src.evaluation.s1_dataset manifest --bags <bags folder>    # dataset_manifest.csv + completeness report
python -m src.evaluation.s1_dataset align --bag <bag>                # 10 frames: RGB edges vs depth edges overlay
```
Done when: calibration measured, all bags have metadata, ≥ 15 GT scenes, another student can replay every bag.

### S2 — Sarvar
```bash
python -m src.evaluation.s2_fusion_eval --frames <frames root> --tf configs/sensors/measured_tf.yaml
python -m src.evaluation.s2_fusion_eval --synthetic       # tool self-check on generated frames (not a result)
```
M1 depth only · M2 mask + desk plane · M3 fixed RGB-D (one rule for all) · M4 adaptive (frozen config).
Needs `<frames root>/<bag_id>/<frame_id>/` with `observation.json` from the frozen S3 run, and GT rows with a
`condition` (normal / shiny / transparent / small / occluded). Minimum: 50 normal + 30 of each other condition.

### S3 — Li Yizhe
```bash
python -m src.evaluation.s3_detection_eval draft   --frames <frames> --images-list keyframes.txt   # detector draft -> people correct it
python -m src.evaluation.s3_detection_eval predict --detector yolo_world     --frames <frames>
python -m src.evaluation.s3_detection_eval predict --detector grounding_dino --frames <frames>    # pip install torch transformers
python -m src.evaluation.s3_detection_eval score   --frames <frames>
python -m src.evaluation.s3_detection_eval prompts --frames <frames>                               # 5 prompt forms per unseen class
python -m src.evaluation.s3_detection_eval clip --run <pipeline run> --frames <its frames> --clip  # real-data CLIP pairs
```
Same frozen prompts / thresholds / frames for both detectors (src/open_vocab/configs/frozen/desk_v1.json). IoU ≥ 0.5 and the
same canonical class (aliases.yaml) = correct.

### S4 — Jaloliddin
```bash
python -m src.evaluation.s4_relation_eval sheet  --runs <runs>/B* <runs>/E* --every 10   # pairs x predicates, pred filled
python -m src.evaluation.s4_relation_eval score
python -m src.evaluation.s4_relation_eval sweep  --runs <runs>/*      # NEAR on dev only -> configs/s4_frozen.yaml
python -m src.evaluation.s4_relation_eval events --runs <runs>/E* <runs>/F*
python -m src.evaluation.s4_relation_eval flips  --runs <runs>/E*     # with / without hysteresis (enter 0.30, leave 0.35)
```

### S5 — Sanjarbek
```bash
python -m src.evaluation.s5_query_eval graphs --tf configs/sensors/measured_tf.yaml   # GT graphs from measured positions
python -m src.evaluation.s5_query_eval generate        # 200 candidates from templates; CHECK each row, set checked=1
python -m src.evaluation.s5_query_eval run --methods A B C D --only-checked             # A/B need Ollama
```
A LLM only · B LLM + scene graph · C LLM + geometry verifier (1 round) · D full propose → verify → correct + history.
Keep the final queries hidden from tuning (guide §8.5).

### S6 — Shakhzodjon
```bash
python -m src.evaluation.s6_tracking_eval plan                         # 30 sequences: 6 scenarios x 5
python -m src.evaluation.s6_tracking_eval sheet --run <runs>/F01 --scenario medium_occlusion_11_20
python -m src.evaluation.s6_tracking_eval score --runs <runs>/E* <runs>/F* <runs>/G* --frames-root <frames>
python -m src.evaluation.s6_tracking_eval actions --graph <a scene graph>   # 30 safe + 30 unsafe trials
```
Baseline = Week-5 greedy 15 cm gate; multi-cue = Hungarian on distance + label + size (+ appearance with --frames-root).

### S7 — Mirzokhidbek
```bash
python -m src.evaluation.s7_e2e_eval tasks                                          # 30-task template
python -m src.evaluation.s7_e2e_eval run --frames-root <frames> --repeats 3
python -m src.evaluation.run_all --frames-root <frames> --bags <bags> --runs-root <runs>   # everything + report
python -m src.evaluation.report                                                     # tables, figures, checklist only
```

## Rules (guide §2.2, §11)
* Same frozen model / configuration for all final runs; tune only on the **dev** split.
* Every rate is printed as `x % (k/n)`; the CI is left out below 5 samples.
* Sample keyframes (every 10–15 frames) — never count near-identical consecutive frames as separate trials.
* If time is short, keep diversity (easy / medium / hard, seen / unseen, static / dynamic, safe / unsafe) rather than
  dropping whole conditions.
* Failure cases are saved and explained, never hidden.
