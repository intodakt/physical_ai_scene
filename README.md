# physical_ai_scene

Physical AI Scene Understanding — G1 capstone (stationary RGB-D tabletop).

| Module | Owner | Path |
|---|---|---|
| Sensors & calibration | S1 | `src/sensors/` |
| 3D preprocessing & fusion | S2 | `src/preprocessing/`, `src/fusion_3d/` — see [src/fusion_3d/README.md](src/fusion_3d/README.md) |
| Open-vocabulary perception | S3 | `src/open_vocab/` |
| Scene graph | S4 | `src/scene_graph/` |
| Language verifier | S5 | `src/reasoning/` |
| Tracking & action | S6 | `src/tracking/`, `src/planning/` |
| Integration & UI | S7 | `main_pipeline.py`, `src/integration/`, `src/evaluation/`, `dashboard/`, `tools/` — see [docs/s7/README.md](docs/s7/README.md) |

## Live demo (all seven modules on one page)

```bash
pip install -r requirements-demo.txt
streamlit run demo/app.py                    # or: docker build -t g1-demo . && docker run -p 8080:8080 g1-demo
python -m demo.pack --src recordings/ --out G1_bags.zip   # bags + S3 masks -> small zip to upload
```

Replays a recorded ZED Mini bag like `ros2 bag play` and shows one tab per member (S1 … S7).
On a MacBook, double-click `G1_Demo.command` (local Ollama LLM included).
Deploys as-is on Railway (`railway.json`) or Google Cloud Run. See [docs/demo/README.md](docs/demo/README.md).

## Quick start

```bash
pip install -r requirements.txt
python main_pipeline.py                      # S1 -> S3 -> S2 -> S6 -> S4 -> S5 -> S6 on the mock desk sequence
python tests/smoke_test.py                   # one-click: ROS 2 bag in, ActionGoal out
python -m src.evaluation.metrics             # experiment matrix -> outputs/evaluation/experiment_matrix.xlsx
streamlit run dashboard/app.py               # presentation dashboard
python tools/check_contracts.py              # PR gatekeeper: absolute paths + JSON contracts
python -m pytest -q
```

## Contributing

Work on a branch and open a pull request into `main`. Before asking for a merge, run
`python tools/check_contracts.py` and `python -m pytest -q`.
