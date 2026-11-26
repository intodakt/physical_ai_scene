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

The twin is built from the frame of the run with the most objects: each S2 object becomes a box,
cylinder or laptop shape at its measured position, size and rotation, coloured from its S3 mask.
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
2. Import it into the demo store: `python -m demo.runs --import <bag + S3 zip>` (or use *➕ Add recording*
   in `streamlit run demo/app.py`). This runs the whole pipeline on the real recording.
3. Start the twin. It picks the newest recording in `data/demo_store/runs/` (choose another in the
   *Recording* menu, top right). Without any recording it builds the synthetic desk.
4. Show the real recording first (left card + *Recording point cloud* toggle), then edit the twin.

## On the page

* **Drag** an object on the table to move it; **Hide / Put back / ⟳** in the object list.
* **Let time pass** renders a still frame (hidden objects age in S6's 10-frame memory).
* **Ask** any question S5 understands: *Where is the mug? · Go to the book · What is closest to the
  laptop? · Find the mug that is not near the laptop · What is on the book? · Where was the mug before?*
* **Planner**: *Straight* refuses a path through the laptop zone (`PATH_BLOCKED`); *Detour* plans around it.
* **Robot**: mobile robot (default), arm, or off.
* **Pipeline's 3D boxes** shows S4's nodes (dashed yellow = occluded, remembered position).
* **Backup scenarios**: slide the mug, hide the book, move the glass past the laptop, each followed by its question.
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
