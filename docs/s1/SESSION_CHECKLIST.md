# S1 — recording session checklist (W11)

Use this for every new or re-recorded bag. Tick each line; a bag that fails a check is re-recorded.

## Before recording
- [ ] Camera on the tripod, lens clean, cable fixed; nothing on the desk moves the tripod.
- [ ] Measure and write down the **camera height above the desk** and the **tilt** (tape + phone inclinometer).
- [ ] Mark the **table origin** (tape corner) and measure the positions of 3–5 reference objects from it.
- [ ] Lights the same as in the earlier bags; no direct sunlight on the desk.
- [ ] `ros2 launch zed_wrapper zed_camera.launch.py camera_model:=zedm`
- [ ] `ros2 topic hz /zed/zed_node/rgb/image_rect_color` → about 30 Hz (also depth).
- [ ] `ros2 topic echo --once /zed/zed_node/rgb/camera_info` → real fx, fy, cx, cy (not zeros).
- [ ] Static TF `map → camera_link` published with the **measured** height / tilt (not the config placeholder).

## Recording
- [ ] `ros2 bag record -o <Sx_name>_<date> <rgb> <depth> <camera_info> /tf /tf_static`
- [ ] Say the scenario name and the take number on the first seconds (or write it in the session sheet).
- [ ] Follow the scenario script (what moves, when, how far); keep hands out of the view except when scripted.
- [ ] Record at least 30 s; for relocation / occlusion: 5 s still before and after every action.
- [ ] Repeat key scenarios **3 times** (S1, S3, S5).

## After recording
- [ ] `ros2 bag info <bag>` — message counts for RGB, depth, camera_info, tf_static are not zero.
- [ ] `python -m src.sensors.session_report --bag <bag> --out reports/<bag>/` — FPS ≈ 30, gaps 0, RGB↔depth p95 < 20 ms.
- [ ] `python -m src.sensors.bag_replay --bag <bag> --out frames/<bag>/ --max-frames 20` then
      `python -m src.sensors.static_tf --frames frames/<bag>/ --out reports/<bag>/` — height / tilt agree with the tape (± 1 cm, ± 1°).
- [ ] Hand the bag to S3 (masks) and add it to `python -m src.sensors.dataset_readme --bags data/bags/`.

## Weak scenarios to re-record (W10 plan, from what the team found)
| Bag | Problem found | Re-record with |
|---|---|---|
| S0 calibration | not recorded; intrinsics are nominal | checkerboard 9×6, 15–30 views, `src.sensors.calibration` |
| S1 static baseline | TF on the frames was the 0.80 m config placeholder | measured static TF; tape-measured object positions (W12 ground truth) |
| S3 relocation, S5 occlusion | no ground-truth identities | a short session sheet: which object moves / is hidden in which second |
| S6 language task | white / glossy objects lose depth; a calculator is labelled remote control by S3 | same objects + matte reference objects; tell S3 which objects are on the desk |
