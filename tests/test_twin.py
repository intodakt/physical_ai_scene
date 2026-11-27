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
    return engine.Twin(run_dir, workdir=tmp_path_factory.mktemp("twin"), parser="rules")


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


def test_http_api(run_dir, tmp_path):
    app = server.App(run_dir, parser="rules", workdir=tmp_path / "twin")
    srv = server.ThreadingHTTPServer(("127.0.0.1", 0), server.make_handler(app))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{srv.server_address[1]}/"
    try:
        page = urllib.request.urlopen(base).read().decode("utf-8")
        assert "G1 Virtual Table" in page and "vendor/three.min.js" in page
        assert urllib.request.urlopen(base + "vendor/three.min.js").status == 200
        src = json.loads(urllib.request.urlopen(base + "api/source").read())
        assert src["n_objects"] >= 4 and src["cloud"]
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
