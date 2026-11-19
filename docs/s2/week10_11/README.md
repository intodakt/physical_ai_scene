# S2 — weeks 10–11: overlap failure case and speed-up

Reproduce: `python scripts/s2_week10_11_report.py` (synthetic frames, ground truth known; 5 seeds × 2 profiles).

## Overlap: S3 masks bleeding onto neighbours

| Mask dilated by | objects found | median (cm) | p95 (cm) | max (cm) |
|---|---|---|---|---|
| 0 px | 50 / 50 | 0.68 | 0.91 | 0.97 |
| 3 px | 50 / 50 | 0.68 | 0.74 | 0.78 |
| 6 px | 50 / 50 | 0.69 | 0.76 | 0.85 |
| 10 px | 50 / 50 | 0.7 | 0.9 | 0.95 |
| 15 px | 50 / 50 | 0.7 | 1.16 | 1.21 |

| Object | 0 px | 3 px | 6 px | 10 px | 15 px |
|---|---|---|---|---|---|
| book | 0.72 | 0.71 | 0.71 | 0.71 | 0.7 |
| glass | 0.84 | 0.69 | 0.75 | 0.87 | 1.13 |
| laptop | 0.57 | 0.59 | 0.6 | 0.61 | 0.63 |
| mug | 0.67 | 0.68 | 0.68 | 0.68 | 0.68 |
| multimeter | 0.69 | 0.68 | 0.69 | 0.68 | 0.7 |

## Speed (this run, this machine)

process_frame: median 515.4 ms, p95 593.5 ms over 10 frames; stages (median): {'depth_cleaning': 56.6, 'support_plane': 5.7, 'objects': 453.5}.

W11 changes (results unchanged, max box-centre difference 0.03 mm): NaN-median by sort instead of masked arrays (flying-pixel filter, depth noise), the spike filter computes the local residual once, RGB quality on the mask's bounding box, minimum-area rectangle on the convex hull. Before / after on the same frames and machine: 915 → 506 ms median, 1211 → 609 ms p95; depth cleaning 203 → 58 ms, objects 709 → 445 ms.

Still slow: Open3D voxel / outlier / DBSCAN (~50 % of the objects step) and the minimal OBB; changing them changes results.
