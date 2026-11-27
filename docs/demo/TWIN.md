# G1 virtual table (digital twin)

`demo/twin/` builds a virtual copy of the recorded desk from what the pipeline measured, lets you
**move, hide and turn objects** on it in the browser, and sends every change through the **real
pipeline code**. The table-mounted G1 upper body stays fixed while S6's allowed path is shown on the desk.

## What is real and what is simulated

| Part | Recorded desk | Twin changes (move / hide / turn) |
|---|---|---|
| S1 camera images | real ZED Mini bag | rendered from the twin by S2's ray-cast renderer (`src/preprocessing/mock_data.py`) |
| S3 detection + masks | real YOLO-World + SAM 2 output | exact masks from the renderer |
| S2 3D fusion, S6 tracking, S4 scene graph | team code | **same team code** (`src/integration/pipeline.Pipeline`) |
| S5 reasoning, S6 ActionGoal, twin simulation | team code | **same team code** |
| Robot | official Unitree G1 upper-body mesh on a simulated fixed pedestal; no recorded robot pose | simulated point and grasp gestures after verified requests; separate from S6 execution |

The twin is built from the frame of the run with the most objects: each S2 object is placed at its
measured position, size and rotation, coloured from its S3 mask. The renderer that makes the twin's camera
frames uses boxes, cylinders and a laptop shape; the page draws stylised versions of common objects
(phone, calculator, remote, game controller, keyboard, mouse, apple, egg, mug, bottle, book) fitted to
the same measured box.
A move is rendered as a short slide (frames ≤ 8 cm apart) so S6 sees the object travel, then still
frames until S6 reports `MOVED`. Moves onto another object are refused.

### Object size and look from the real image

S2's boxes come from depth; on a dark, glossy desk most objects are `transparent_suspected` and their
boxes are partial. The twin therefore also uses the camera image (`demo/twin/photo.py`), with S1's
measured camera pose:

* **flat objects** (phones, calculators, remotes, books, pads, or measured height < 4.5 cm): S3's mask
  (eroded 2 px) is projected onto the object's top plane; pixels in front of each column's desk-contact
  point (the visible side face) are dropped; the minimum-area rectangle is the footprint, and the image
  re-sampled onto it is the object's top texture. On the synthetic desk: book 0.227 × 0.151 m (true
  0.22 × 0.15), multimeter 0.151 × 0.086 m (true 0.15 × 0.08);
* **tall objects with failed depth**: S2's own mask + desk-plane estimate (`mask_plane.estimate_from_mask`);
* the page's **Look: Photo** draws flat objects with their top photo and tall ones as a cut-out of the
  camera image standing on the desk; **Stylised** keeps the drawn shapes;
* **✎ (rename)** corrects a label S3 got wrong (kept in `<run>/twin_labels.json`, shown as
  "renamed (S3: …)"); the twin is rebuilt so S4 and S5 use the new name.

Recordings imported before this version need `python -m demo.twin --remeasure <name>` once, so the
measured camera pose is stored with the run.

## Start it

| Laptop | How |
|---|---|
| Windows | double-click **`G1_Twin.bat`** (first run: creates `.venv`, installs `requirements-demo.txt`, pulls the Ollama model if Ollama is installed) |
| macOS | double-click **`G1_Twin.command`** (first time: right-click → Open). Shares `.venv` with `G1_Demo.command` |
| any | `python -m demo.twin` (after `pip install -r requirements-demo.txt`) |

The browser opens at http://127.0.0.1:8600. Options: `--run <run folder>`, `--parser auto|ollama|rules`,
`--planner straight|detour`, `--port 8600`, `--no-browser`.

## Presentation-day workflow

1. Record the desk with the ZED Mini (15–30 s) and run S3 on it (as for every bag).
2. Put the bag (`metadata.yaml` + `.db3`, or the lone `.db3`) and S3's output folder
   (`frame_XXXXXX/observation.json` + `masks/`) in **one folder**, e.g. `my_recording/`. Name the S3
   folder after the bag or its scenario tag (`S2_bag.db3` ↔ `S2_static/`) if the folder holds several bags.
3. Import it and open the twin in one step:
   * Windows: **drag the folder onto `G1_Twin.bat`**;
   * any OS: `python -m demo.twin path/to/my_recording` (a `.zip` or `.db3` works too).

   This replays the bag (S1), attaches S3's masks, runs S2 → S6 → S4 → S5 → S6 on every frame, stores
   the result in `data/demo_store/runs/<bag name>` and builds the twin from it. A bag without S3 output
   is refused with a message (the demo install has no YOLO-World).
   The import also **measures the camera height and tilt from the desk plane** (S1's
   `src/sensors/static_tf.py`, the same as `main_pipeline.py --camera-tf auto`), because the G1 bags carry
   no TF: with the configured placeholder (0.80 m, 29°) every object floats ~0.6 m above the desk and gets
   a huge, tilted box. `--camera-tf bag` turns this off. A recording imported earlier without it is
   re-run with `python -m demo.twin --remeasure <recording name>` (the folder name in
   `data/demo_store/datasets/`).
4. Later starts (`G1_Twin.bat` alone) open the newest imported recording; the *Recording* menu (top
   right) switches between recordings. With none imported, the synthetic desk is used.
5. Show the real recording first (left card + *Recording point cloud* toggle), then edit the twin.

Recordings imported in the Streamlit demo (*➕ Add recording*) or with `python -m demo.runs --import`
land in the same store and show up in the *Recording* menu too.

## Windows blocks a file

`Access denied ... An Application Control policy has blocked this file` (on `G1_Twin.bat`) or
`DLL load failed ... Application Control policy` (Open3D's `pybind`) means Windows 11 **Smart App
Control** (or a school/company policy) blocks unsigned files downloaded from the internet.

* `.bat` only: run the steps by hand in PowerShell from the project folder:
  `py -3.11 -m venv .venv`, `.venv\Scripts\python.exe -m pip install -r requirements-demo.txt`,
  `.venv\Scripts\python.exe -m demo.twin "<recording folder>"`.
* Open3D DLL: Windows Security → App & browser control → Smart App Control → Off (Windows only lets
  you turn it back on by resetting the PC), or use a laptop without the policy (macOS: `G1_Twin.command`).
  A policy managed by an organisation cannot be changed by the user.

## On the page

* **Drag** an object on the table to move it; **Hide / Put back / ⟳** in the object list.
* **Let time pass** renders a still frame (hidden objects age in S6's 10-frame memory).
* **Ask** any question S5 understands: *Where is the mug? · Go to the book · What is closest to the
  laptop? · Find the mug that is not near the laptop · What is on the book? · Where was the mug before?*
* **Obstacles**: *All objects* (default) makes every object except the target an S6 exclusion zone;
  *Laptop only* is the team config (`exclusion_labels: [laptop]` in `configs/s7_integration.yaml`), where
  the robot may cross every other object. S6's code is the same; only its config differs. The robot
  starts at the front edge, at the spot with clear straight lines to the most objects.
* **Planner**: *Straight* refuses a path through an exclusion zone (`PATH_BLOCKED`); *Detour* plans around it.
* **Robot**: a fixed G1 upper body with articulated hands. After S5 verifies an object, *find/where* requests make a hand point to it; *take/pick/move* requests animate a simulated grasp and lift. The held object stays in the visual hand until *Release object* or the next request. The source object position and S4 state remain unchanged. *Preview reach* is also available for the selected object. If the mounted arm cannot reach the target, the page says so. The base never walks or follows S6's path; S6's 2D path is a separate overlay.
* **Views**: table, recorded camera, robot overview, front, left, right, rear, top, and saved user views. *Human from right/left/back/front* places the viewing camera at that table edge; the selected-object panel then shows left/right and near/far from that person's view. The robot stays mounted. Robot-side labels are relative to the robot's heading, shown by its front arrow.
* **Recorded camera** uses S1's optical transform and intrinsics. Desk-plane calibration estimates height and pitch only, so this view says *horizontal pose unknown* until measured camera X, Y, and yaw are entered under *View controls*. Those values are saved in this browser for the selected recording. The camera frustum is shown in other views.
* **Coordinates**: the optional 10 cm XY grid has number labels laid flat along two table edges, so they do not draw over the robot. The footer shows X/Y under the mouse. The selected-object panel shows twin X/Y/Z in metres and yaw, plus S4's latest measured centre. Mount X/Y and nearest-object clearance are in *View controls*. The mount is chosen at a clear table edge and can be adjusted there.
* **Pipeline's 3D boxes** shows S4's nodes (dashed yellow = occluded, remembered position).
* **Backup scenarios**: slide the mug, hide the book, move the glass past the laptop, and **block the
  path** (an object is slid onto the robot's line to a target that was reachable), each followed by its question.
* **Questions without Ollama**: the rule parser reads the question instead of the LLM (top bar:
  *S5 parser: rules*); same question types, same verifier and S6.
* Right side: S5 answer + S6 decision, the rendered frame the pipeline processed with per-stage latency,
  S6 events and an action log, S4 relations.

## Files

| File | Role |
|---|---|
| `demo/twin/engine.py` | `Twin`: run → twin, edits, rendering, pipeline, questions, presets |
| `demo/twin/server.py` | local web server (standard library) and JSON API |
| `demo/twin/static/index.html` | 3D page, camera views, orientation and coordinate controls |
| `demo/twin/static/g1-robot.js` | fixed pedestal, articulated G1 joint preview and mount placement |
| `demo/twin/static/assets/g1/` | derived official Unitree mesh, license and source attribution |
| `tools/build_g1_upper_body.py` | rebuilds the GLB from Unitree's G1 URDF and STL meshes |
| `G1_Twin.bat`, `G1_Twin.command` | one-click start on Windows / macOS |
| `tests/test_twin.py` | twin from a pipeline run: move, hide, presets, API |
