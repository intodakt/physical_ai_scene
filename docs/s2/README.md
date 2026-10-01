# S2 progress report — 3D Preprocessing

Figures are regenerated from real pipeline runs by `python scripts/make_s2_report.py`
and `python scripts/make_s2_slide.py`. Input is the **mock** S1/S3 frame
(`data/mock/frame_000`) until the real Static Baseline bag and S3 masks are ready.

| Week task (guide) | Status | Evidence |
|---|---|---|
| W3: fake depth + fake 2D circle → 3D centre with Open3D | ✅ | `tests/test_s2_projection.py::test_fake_circle_centroid` |
| W5: mock mask + mock depth → point cloud | ✅ | `src/preprocessing/mock_data.py`, screenshot 01–02 |
| W5: XYZ centroid + oriented bounding box | ✅ | screenshot 02–03 |
| W5: output matches ObjectInstance3D contract | ✅ | screenshot 04, serialization test |
| Relative paths only | ✅ | `--frame data/mock/frame_000`, config paths relative to repo |
| Noise removal (`remove_statistical_outlier`) | ✅ | screenshot 02 (6168 → 2557 pts) |
| depth_confidence (valid depth ratio) | ✅ | screenshot 07 (glass 0.23) |
| Fixed + adaptive fusion weights | ✅ | screenshot 07 |
| Run on S1 Static Baseline bag | ⏳ waiting for S1 | — |

## Screenshots

1. `screenshots/01_inputs_S1_S3.png` — S1 RGB + depth, S3 boxes + masks
2. `screenshots/02_mask_to_pointcloud_mug.png` — mask → masked depth → raw cloud → cleaned cloud + box
3. `screenshots/03_scene_3d_bounding_boxes.png` — all objects with 3D boxes (map frame)
4. `screenshots/04_objectinstance3d_json.png` — JSON handed to S4/S6
5. `screenshots/05_pipeline_run_terminal.png` — CLI run
6. `screenshots/06_unit_tests_passed.png` — 17/17 tests pass
7. `screenshots/07_metrics.png` — localisation error, depth confidence, fixed vs adaptive weights

Slide: `slide_06_S2.png` (1920×1080, upload to Canva as an image, or rebuild it with the text below).

## Slide 6 — speaker notes (o'zbekcha)

> Mening vazifam — S2, 3D Preprocessing. Men 2D dunyoni 3D dunyoga ko'chiraman.
> S1 menga RGB, depth va kamera intrinsics faylini beradi, S3 esa har bir obyekt
> uchun SAM maskasini beradi. Men maska ichidagi depth piksellarini olib,
> X=(u−cx)·Z/fx, Y=(v−cy)·Z/fy formulasi bilan 3D nuqtalarga aylantiraman.
> So'ng stol tekisligini RANSAC bilan olib tashlayman, statistical outlier removal
> va DBSCAN bilan shovqinni tozalayman, Open3D yordamida centroid va oriented
> bounding box hisoblayman. Natija ObjectInstance3D JSON ko'rinishida S4 va S6 ga
> uzatiladi. Har bir obyekt uchun depth_confidence hisoblanadi: masalan shisha
> stakanda depth sensor ishlamaydi, ishonchlilik 0.23 ga tushadi va adaptive
> fusion depth vaznini avtomatik kamaytiradi. Mock sahnada 5 ta obyektning
> hammasi topildi, 3D box markazining o'rtacha xatosi 0.7 sm, 17 ta test o'tdi.
> Keyingi qadam — S1 ning haqiqiy Static Baseline bag'ida ishga tushirish.
