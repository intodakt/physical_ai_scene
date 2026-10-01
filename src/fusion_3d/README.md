# S2 — 3D Preprocessing & Fusion

Turns S3's 2D masks + S1's aligned depth into 3D objects (`ObjectInstance3D`)
for S4 (scene graph) and S6 (tracking). Pure geometry: NumPy + Open3D, no training.

## Quick start

```bash
pip install -r requirements.txt
python -m src.preprocessing.mock_data --out data/mock/frame_000   # mock S1+S3 frame
python -m src.fusion_3d.run_pipeline --frame data/mock/frame_000  # -> outputs/fusion_3d/
python -m src.fusion_3d.run_pipeline --frame data/mock/frame_000 --show   # Open3D window
pytest -v                                                          # 17 tests
python scripts/make_s2_report.py && python scripts/make_s2_slide.py  # figures in docs/s2/
```

All paths are relative to the repo root.

## Inputs (handshake)

| From | File in the frame dir | Notes |
|---|---|---|
| S1 | `rgb.png` | aligned colour |
| S1 | `depth.png` (uint16 mm) or `depth.npy` (float m) | **must be aligned to colour** (`align_depth.enable:=true`) |
| S1 | `camera_intrinsics.yaml` | flat `fx/fy/cx/cy/width/height` or ROS `camera_info` dump (`k:`) |
| S1 | `frame_meta.json` (optional) | `timestamp`, `T_map_camera` (4x4 optical→map). Fallback: `tf_map_camera_link` in `configs/fusion_3d.yaml` |
| S3 | `semantic_observations.json` | `{"observations": [{bbox, mask, labels, score, ...}]}`; `mask` = RLE `{size, counts}`, or a `.npy`/`.png` path |

## Pipeline (`src/fusion_3d/pipeline.py`)

1. **Depth cleaning:** mm→m, drop NaN/0/out-of-range (`configs/fusion_3d.yaml: depth`).
2. **Support plane:** RANSAC the desk on the whole frame; object points within 8 mm of it are dropped (removes SAM mask bleed).
3. **Mask filter + deprojection:** `X=(u−cx)Z/fx, Y=(v−cy)Z/fy`.
4. **Cleaning:** voxel 3 mm → `remove_statistical_outlier` → largest DBSCAN cluster.
5. **Geometry:** centroid (mean), Open3D minimal OBB (PCA fallback for flat clouds), upright box in `map` (min-area rectangle + z range → `[W, H, D]`, H vertical).
6. **Uncertainty:** `depth_confidence` = valid depth px / mask px; per-modality quality (RGB brightness/sharpness, depth, detector score) → `fixed` or `adaptive` fusion weights; LiDAR kept in the contract at weight 0 (G1 = F2 RGB-D baseline).
7. Objects with < `min_points` points are **rejected** (listed with a reason). No NaN geometry is ever emitted.

## Output: `outputs/fusion_3d/<frame>_objects.json`

```json
{"objects": [{
  "centroid": [x, y, z],            // m, camera optical frame (guide contract)
  "box_dimensions": [W, H, D],      // m, H vertical when map TF known
  "semantic_label": "mug",
  "depth_confidence": 0.98,
  "object_id": "mug_0", "persistent_id": null,      // S6 fills persistent_id
  "centroid_map": [...], "box_map": {"center", "yaw", "dimensions"},
  "label_candidates": [...], "detector_score": 0.88,
  "modality_quality": {...}, "fusion_weights": {...}, "fused_confidence": 0.90,
  "points_ref": "frame_000_points.npz#mug_0", ...
}], "rejected": [...], "timings_ms": {...}}
```

`ObjectInstance3D.from_dict/from_json` round-trips without field loss (tested).
**For S4:** use `centroid_map` / `box_map` (z is up) for `on`/`near`; use `centroid` (camera) for `left_of`.

## Mock data

`src/preprocessing/mock_data.py` ray-casts a desk scene (laptop, mug, book,
multimeter, glass) with a D435-like camera 0.6 m up, pitched 45°, and adds
range-dependent noise, dropouts, flying pixels, a transparent glass (85 % depth
missing) and 2 px dilated masks. `ground_truth.json` lets us measure error.

Mock-frame results: 5/5 objects, mean box-centre error **0.7 cm**,
visible-surface centroid error ~3 cm (a single view only sees the front of the object).

## Known failure cases

- **Reflective/transparent objects:** depth holes → low `depth_confidence`; adaptive fusion lowers `w_depth`.
- **Single viewpoint:** the centroid of visible points is biased towards the camera; prefer `box_map.center`.
- **Touching objects:** if S3 masks overlap, DBSCAN keeps the largest cluster only.
- **Thin objects (< 8 mm tall)** vanish with support-plane removal → lower `support_plane.margin_m`.
- **Runtime:** ~1 s/frame on CPU, dominated by DBSCAN; set `keep_largest_cluster: false` for speed.

## Still to do (later weeks)

- Live ROS 2 / rosbag frame loader once S1's bags are uploaded.
- Run on S1's Static Baseline bag; replace mock with real S3 masks.
- Sensor-subset ablation (F1 RGB vs F2 RGB-D) on real data.
