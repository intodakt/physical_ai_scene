# S2 — 3D Preprocessing & Fusion

Turns S3's 2D masks + S1's aligned depth into 3D objects (`ObjectInstance3D`)
for S4 (scene graph) and S6 (tracking). Pure geometry: NumPy + Open3D, no training.

## Quick start

```bash
pip install -r requirements.txt
python -m src.preprocessing.mock_data --out data/mock/frame_000   # mock S1+S3 frame
python -m src.fusion_3d.run_pipeline --frame data/mock/frame_000  # -> outputs/fusion_3d/
python -m src.fusion_3d.run_pipeline --frame data/mock/frame_000 --show   # Open3D window
pytest -v                                                          # 35 tests
python scripts/make_s2_report.py && python scripts/make_s2_slide.py  # figures in docs/s2/
```

All paths are relative to the repo root.

## Week 6 — real-data path (ZED Mini bags)

```bash
# 1. S1's ROS 2 bag → synchronized frame folders (|t_rgb − t_depth| ≤ 20 ms)
python -m src.preprocessing.bag_reader --bag data/bags/<S1 bag> --out data/frames/static_baseline --profile zed_mini --every 10
# 2. S3 writes observation.json into every frame folder (src/open_vocab)
# 3. S2 over the whole sequence: per-frame JSON + stability report (+ temporal median)
python -m src.fusion_3d.run_sequence --frames data/frames/static_baseline --out outputs/fusion_3d/static_baseline --temporal-median
```

Profiles: `zed_mini` (`/zed/zed_node/rgb/image_rect_color`, `/zed/zed_node/depth/depth_registered` 32FC1 metres,
`/zed/zed_node/rgb/camera_info`) and `realsense` (16UC1 millimetres). Tested by writing a ZED-format bag from mock
frames and reading it back bit-exact (`tests/test_s2_week6_7.py`).

## Week 7 — depth cleaning and transparent objects

* **Flying-pixel filter** (`depth.flying_pixel_filter`): drops pixels that differ from their 3×3 median by
  more than 2 cm + 2 %. **Temporal median** (`--temporal-median`) for static scenes.
* **Depth reliability** (`src/fusion_3d/depth_reliability.py`), measured on the eroded mask interior:
  * `interior_valid_ratio` — holes (structured light / specular glass);
  * `plane_leak_ratio` — share of interior depth lying *on the desk plane*: the stereo camera looked
    *through* the glass;
  * `genuine_ratio = valid × (1 − leak)`; `depth_status` = `ok` / `transparent_suspected` / `no_depth`.
* **Mask + desk-plane fallback** (`src/fusion_3d/mask_plane.py`): when genuine depth < 10 %, the lowest mask
  pixel of every column is intersected with the desk plane and a RANSAC circle is fitted (rim-only columns are
  outliers); the height comes from the top of the mask. `geometry_source` says which path was used.

Mock results (`python scripts/make_s2_week6_7_report.py` → `docs/s2/week6_7/`): fully transparent glass
5.2 cm → **1.0 cm**, glass with no depth at all 5.6 cm → **1.0 cm**; partially visible glass costs ≈ 2 mm
(0.7 → 0.9 cm) because only the mask interior is trusted.

## Inputs (handshake)

| From | File in the frame dir | Notes |
|---|---|---|
| S1 | `rgb.png` | aligned colour |
| S1 | `depth.png` (uint16 mm) or `depth.npy` (float m) | **must be aligned to colour** (RealSense `align_depth.enable:=true`; ZED Mini depth is already registered to the left image) |
| S1 | `camera_intrinsics.yaml` | flat `fx/fy/cx/cy/width/height` or ROS `camera_info` dump (`k:`) |
| S1 | `frame_meta.json` (optional) | `timestamp`, `T_map_camera` (4x4 optical→map). Fallback: `tf_map_camera_link` in `configs/fusion_3d.yaml` |
| S3 | `observation.json` + `masks/*.png` | S3's `s3-semantic-draft-0.1` contract (`src/open_vocab/contract.py`): `detections[]` with `detection_id`, `bbox` (xyxy px), `labels`, `detector_score`, `mask` (relative PNG 0/255), `mask_status`. Detections with `mask_status != "ok"` are skipped and listed under `rejected`. Pass a path from an S3 run with `--observations output/s3_semantic/<run>/frame_000000/observation.json` |

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

`src/preprocessing/mock_data.py` writes S3's exact output layout (validated by
S3's own `contract.load_observation` in `tests/test_s2_s3_interface.py`) and ray-casts a desk scene (laptop, mug, book,
multimeter, glass) with a D435-like camera 0.6 m up, pitched 45°, and adds
range-dependent noise, dropouts, flying pixels, a transparent glass (85 % depth
missing) and 2 px dilated masks. `ground_truth.json` lets us measure error.

Mock-frame results: 5/5 objects, mean box-centre error **0.7 cm**,
visible-surface centroid error ~3 cm (a single view only sees the front of the object).

## Known failure cases

- **Reflective/transparent objects:** flagged by holes / see-through cues; geometry from mask + desk plane
  when no genuine depth remains. The see-through cue only works when the desk is behind the glass — if another
  object stands behind it, those pixels look genuine. The fallback assumes a round footprint (glasses, bottles).
- **Single viewpoint:** the centroid of visible points is biased towards the camera; prefer `box_map.center`.
- **Touching objects:** if S3 masks overlap, DBSCAN keeps the largest cluster only.
- **Thin objects (< 8 mm tall)** vanish with support-plane removal → lower `support_plane.margin_m`.
- **Runtime:** ~1 s/frame on CPU, dominated by DBSCAN; set `keep_largest_cluster: false` for speed.

## Still to do (later weeks)

- Run on S1's real ZED Mini bags once uploaded (loader is ready); replace mock with real S3 masks.
- Sensor-subset ablation (F1 RGB vs F2 RGB-D) on real data.
