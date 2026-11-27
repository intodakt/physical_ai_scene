"""Virtual table (demo/twin): a twin built from a pipeline run, edited, and processed by the real pipeline."""

import json
import threading
import urllib.request

import pytest

from demo.twin import engine, server


@pytest.fixture(scope="module")
def run_dir(tmp_path_factory):
    from main_pipeline import run

    out = tmp_path_factory.mktemp("run")
    run(out=str(out), parser="rules", limit=3, quiet=True)
    return out


@pytest.fixture(scope="module")
def twin(run_dir, tmp_path_factory):
    # the team's S6 config (only the laptop is an exclusion zone); "all objects" is tested below
    return engine.Twin(run_dir, workdir=tmp_path_factory.mktemp("twin"), parser="rules", obstacles="config")


def _events(state):
    return state["log"][-1]["events"]


def test_twin_matches_the_measured_objects(twin):
    st = twin.state()
    names = {o["name"] for o in st["twin"]}
    assert names == {n["id"] for n in st["nodes"]}
    assert all(n["state"] == "observed" for n in st["nodes"])
    assert st["contract_errors"] == 0
    assert {"laptop", "cylinder", "box"} <= {o["kind"] for o in st["twin"]}


def test_move_keeps_identity_and_reports_moved(twin):
    x, y = twin.specs["mug_01"]["xy"]
    st = twin.move("mug_01", x - 0.1, y - 0.1)
    assert "MOVED mug_01" in _events(st)
    node = next(n for n in st["nodes"] if n["id"] == "mug_01")
    assert abs(node["pose"][0] - (x - 0.1)) < 0.03 and abs(node["pose"][1] - (y - 0.1)) < 0.03
    assert sum(n["label"] == "mug" for n in st["nodes"]) == 1          # no second mug track
    with pytest.raises(ValueError, match="overlap"):
        twin.move("mug_01", *twin.specs["laptop_01"]["xy"])


def test_hidden_object_is_remembered_and_refused(twin):
    st = twin.hide("book_01")
    assert "OCCLUDED book_01" in _events(st)
    st = twin.ask("Go to the book")
    assert st["query"]["code"] == "TARGET_OCCLUDED" and not st["query"]["validated"]
    st = twin.show("book_01")
    assert "REAPPEARED book_01" in _events(st)
    assert twin.ask("Go to the book")["query"]["validated"]


def test_glass_past_the_laptop_needs_a_detour(twin):
    twin.reset()
    st = twin.run_preset("behind")
    assert st["query"]["code"] == "PATH_BLOCKED"
    twin.set_planner("detour")
    st = twin.ask(st["query"]["question"])
    assert st["query"]["code"] == "OK_DETOUR" and st["query"]["simulation"]["success"]
    twin.set_planner("straight")


def test_every_object_is_an_obstacle_by_default(run_dir, tmp_path):
    twin = engine.Twin(run_dir, workdir=tmp_path / "twin", parser="rules")
    assert twin.obstacles == "all"
    target, _ = twin._block_pick()
    question = f"Go to the {twin.specs[target]['label']}"
    assert twin.ask(question)["query"]["validated"]                       # clear before
    st = twin.run_preset("block")
    assert st["query"]["code"] == "PATH_BLOCKED"                           # an object now stands in the way
    twin.set_planner("detour")
    q = twin.ask(st["query"]["question"])["query"]
    assert q["code"] == "OK_DETOUR" and q["simulation"]["success"] and q["simulation"]["collisions"] == 0
    twin.set_obstacles("config")                                           # team config: laptop only
    twin.set_planner("straight")
    assert twin.ask(st["query"]["question"])["query"]["code"] == "OK"


def test_http_api(run_dir, tmp_path):
    app = server.App(run_dir, parser="rules", workdir=tmp_path / "twin")
    srv = server.ThreadingHTTPServer(("127.0.0.1", 0), server.make_handler(app))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{srv.server_address[1]}/"
    try:
        page = urllib.request.urlopen(base).read().decode("utf-8")
        assert "Scene Studio" in page and "vendor/three.min.js" in page
        assert urllib.request.urlopen(base + "vendor/three.min.js").status == 200
        assert urllib.request.urlopen(base + "assets/g1/g1-upper-body.glb").status == 200
        joints = json.loads(urllib.request.urlopen(base + "assets/g1/g1-upper-body.json").read())["joints"]
        assert "right_hand_palm_joint" in joints and "left_elbow_joint" in joints
        src = json.loads(urllib.request.urlopen(base + "api/source").read())
        assert src["n_objects"] >= 4 and src["cloud"]
        assert src["recorded_camera"]["intrinsics"]["fy"] > 0
        req = urllib.request.Request(base + "api/ask", data=json.dumps({"question": "Where is the mug?"}).encode(),
                                     headers={"Content-Type": "application/json"})
        st = json.loads(urllib.request.urlopen(req).read())
        assert st["query"]["target"] == "mug_01"
        bad = urllib.request.Request(base + "api/hide", data=b'{"name": "nope"}')
        with pytest.raises(urllib.error.HTTPError) as e:
            urllib.request.urlopen(bad)
        assert e.value.code == 400
        with pytest.raises(urllib.error.HTTPError):
            urllib.request.urlopen(base + "../engine.py")
    finally:
        srv.shutdown()


def test_import_measures_the_camera_from_the_desk(tmp_path, monkeypatch):
    """Real G1 bags carry no TF: with camera_tf='auto' S1's desk-plane TF puts the objects on the desk."""
    import shutil

    from demo import runs
    from scripts.make_demo_sequence import generate
    from src.preprocessing.frame_loader import load_frame
    from src.sensors import bag_replay

    dirs = generate(tmp_path / "render", n_frames=3)
    frames = [load_frame(d) for d in dirs]
    pkg = tmp_path / "rec"
    bag_replay.write_bag(frames, pkg / "S1_static_bag", camera_info=True)          # no /tf_static
    for i, (d, fr) in enumerate(zip(dirs, frames)):
        f = pkg / "s3_run" / f"frame_{i:06d}"
        shutil.copytree(d / "masks", f / "masks")
        obs = json.loads((d / "observation.json").read_text(encoding="utf-8"))
        obs["timestamp"] = fr.timestamp
        (f / "observation.json").write_text(json.dumps(obs), encoding="utf-8")
    monkeypatch.setattr(runs, "DATASETS", tmp_path / "store" / "datasets")
    monkeypatch.setattr(runs, "RUNS", tmp_path / "store" / "runs")
    name = runs.import_and_run(pkg, parser="rules", camera_tf="auto")[0]
    summary = json.loads((runs.RUNS / name / "run_summary.json").read_text(encoding="utf-8"))
    assert abs(summary["camera_tf"]["camera_height_m"] - 0.6) < 0.02                 # mock camera: 0.6 m, 45 deg
    assert abs(summary["camera_tf"]["pitch_below_horizontal_deg"] - 45) < 2
    loaded = engine.load_run(runs.RUNS / name)
    assert loaded["camera_tf"]["method"] == "desk_plane_ransac"
    assert loaded["T_map_camera"] == summary["camera_tf"]["T_map_camera"]
    last = summary["frames"][-1]["frame"]
    objs = json.loads((runs.RUNS / name / "objects" / f"{last}_objects.json").read_text(encoding="utf-8"))["objects"]
    assert objs and all(o["box_map"]["center"][2] < 0.15 for o in objs)              # on the desk, not floating


def test_flat_objects_get_their_size_from_the_mask(twin):
    """Synthetic desk truth: book 0.22 x 0.15 m, multimeter 0.15 x 0.08 m (mock_data.OBJECTS)."""
    sizes = {s["label"]: s["size"] for s in twin.base if s.get("geometry") == "mask_plane_flat"}
    assert abs(sizes["book"][0] - 0.22) < 0.02 and abs(sizes["book"][1] - 0.15) < 0.02
    assert abs(sizes["multimeter"][0] - 0.15) < 0.02 and abs(sizes["multimeter"][1] - 0.08) < 0.02
    mug = next(s for s in twin.base if s["label"] == "mug")
    assert abs(mug["size"][1] - 0.10) < 0.02                      # height, not depth (S2 box order W, H, D)
    looks = {s["label"]: twin.photos[s["name"]]["look"] for s in twin.base}
    assert looks["book"] == "top" and looks["mug"] == "cutout"


def test_rename_corrects_the_label_everywhere(run_dir, tmp_path):
    twin = engine.Twin(run_dir, workdir=tmp_path / "twin", parser="rules", obstacles="config")
    try:
        st = twin.rename("multimeter_01", "calculator")
        names = {o["name"] for o in st["twin"]}
        assert "calculator_01" in names and "multimeter_01" not in names
        assert "calculator_01" in {n["id"] for n in st["nodes"]}
        assert twin.ask("Where is the calculator?")["query"]["target"] == "calculator_01"
    finally:
        (run_dir / "twin_labels.json").unlink(missing_ok=True)
