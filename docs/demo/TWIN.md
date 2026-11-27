# G1 virtual table (digital twin)

`demo/twin/` builds a virtual copy of the recorded desk from what the pipeline measured, lets you
**move, hide and turn objects** on it in the browser, and sends every change through the **real
pipeline code**. Then you ask questions and a virtual robot drives the path S6 allowed, or stays put
when S6 refuses.

## What is real and what is simulated

| Part | Recorded desk | Twin changes (move / hide / turn) |
|---|---|---|
| S1 camera images | real ZED Mini bag | rendered from the twin by S2's ray-cast renderer (`src/preprocessing/mock_data.py`) |
| S3 detection + masks | real YOLO-World + SAM 2 output | exact masks from the renderer |
| S2 3D fusion, S6 tracking, S4 scene graph | team code | **same team code** (`src/integration/pipeline.Pipeline`) |
| S5 reasoning, S6 ActionGoal, twin simulation | team code | **same team code** |
| Robot | virtual: follows S6's 2D path (mobile robot), or an arm that reaches along it (visual only) | same |

The twin is built from the frame of the run with the most objects: each S2 object is placed at its
measured position, size and rotation, coloured from its S3 mask. The renderer that makes the twin's camera
frames uses boxes, cylinders and a laptop shape; the page draws stylised versions of common objects
(phone, calculator, remote, game controller, keyboard, mouse, apple, egg, mug, bottle, book) fitted to
the same measured box.
A move is rendered as a short slide (frames ≤ 8 cm apart) so S6 sees the object travel, then still
frames until S6 reports `MOVED`. Moves onto another object are refused.

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
* **Robot**: mobile robot (default), arm, or off.
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
| `demo/twin/static/index.html` | 3D page (three.js r128, bundled in `static/vendor/`, MIT licence) |
| `G1_Twin.bat`, `G1_Twin.command` | one-click start on Windows / macOS |
| `tests/test_twin.py` | twin from a pipeline run: move, hide, presets, API |
