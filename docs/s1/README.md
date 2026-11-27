# S1 — Sensors & calibration tools (reference implementation, to be reviewed by S1)

> **Authorship.** The S1 bags were recorded by S1 (Ulmasov Muzaffar). The code in `src/sensors/`
> was written with Claude Code (AI): `bag_replay.py` for the demo platform, and the three tools
> below as a reference implementation of roadmap §11.1. S1 reviews them, runs them on the real
> bags and reports the numbers as their own measurements.

| Roadmap item (§11.1) | Tool | Output |
|---|---|---|
| Save intrinsics (the skipped S0 bag) | `python -m src.sensors.calibration --images <dir> \| --bag <S0 bag> --pattern 9x6 --square 0.025 --out <dir>` | `camera_intrinsics.yaml` (same keys as `configs/sensors/`), `calibration_report.csv` (RMS per view, outliers) |
| Documented TF; measured camera height and pitch | `python -m src.sensors.static_tf --frames <exported frames> --out <dir>` | `static_tf.yaml` (map → camera_link xyz / rpy, height, pitch, spread over frames, vs the configured placeholder), `static_tf.json` |
| Use the measured TF in the pipeline | `python main_pipeline.py --bag <bag> --camera-tf auto` (or `--camera-tf static_tf.json`) | every frame uses the desk-plane TF |
| 30 FPS stability; timestamp sync error | `python -m src.sensors.session_report --bag <bag> --out <dir>` | `session_meta.json`: measured FPS, frame gaps, RGB↔depth offset mean / p95 / max |
| Invalid-depth % on glass / shiny / dark | same, with `--frames <exported frames with S3 output>` | `depth_quality.csv`: valid-depth %, median distance, depth noise per object |
| Reprojection / deprojection consistency | `calibration.deprojection_consistency(depth, K)` | round-trip error in pixels |

Export frames from a bag first: `python -m src.sensors.bag_replay --bag <bag> --out <dir>`.

Checked on synthetic data only (`tests/test_s1_sensors.py`): calibration recovers fx to 1 % from
12 simulated views; the desk-plane TF recovers the mock camera (0.60 m, 45°) to 1 cm / 1°. The real
bags are not in the repository, so the real numbers (e.g. the ≈ 0.32 m / ≈ 52° seen by S2 against the
0.80 m placeholder) have to be produced by S1 with these commands.

## W12–W16 evaluation (S1) — professor's step-by-step guide

- Recording plan (45 bags, families A–H, frozen dev/test split): `python -m src.evaluation.s1_dataset plan` → `eval/dataset/`
- Metadata per bag (§2.4): `python -m src.evaluation.s1_dataset metadata` → fill `eval/dataset/metadata/<bag>.yaml` on the recording day
- Calibration (§4.2): `python -m src.sensors.calibration --bag <A01 bag> --every 15 --out configs/sensors/` → mean / median / max px + overlays
- Measured camera pose (§3.1): `python -m src.evaluation.s1_dataset tf --height <m> --pitch-deg <deg> --x <m> --y <m> --yaw-deg <deg>`
- Manifest + completeness (§4.5): `python -m src.evaluation.s1_dataset manifest --bags <bags>`; alignment check: `... align --bag <bag>`
- Ground truth: `eval/ground_truth/ground_truth_positions.csv` (≥ 15 scenes, tape frame). Done means (§16): calibration measured, all bags with metadata, ≥ 15 GT scenes, any member can replay every bag.

Full workflow and the shared dataset: [`eval/README.md`](../../eval/README.md).
