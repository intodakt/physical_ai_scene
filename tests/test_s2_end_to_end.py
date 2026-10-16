"""End-to-end on the generated mock frame (stand-in for S1 bag + S3 masks)."""

import json

import pytest

from src.fusion_3d.object_instance import validate
from src.fusion_3d.run_pipeline import run
from src.preprocessing.mock_data import generate


@pytest.fixture(scope="module")
def mock_run(tmp_path_factory):
    d = tmp_path_factory.mktemp("mock")
    frame_dir = generate(d / "frame_000")
    return run(frame_dir, d / "out")


def test_all_objects_localized(mock_run):
    _, _, result, payload, json_path = mock_run
    ev = payload["evaluation"]
    assert ev["recall"] == 1.0
    assert ev["mean_box_center_error_m"] < 0.02
    for row in ev["per_object"]:
        assert row["box_center_error_m"] < 0.03, row
    data = json.loads(json_path.read_text())
    for o in data["objects"]:
        validate(o)


def test_shiny_object_has_low_depth_confidence(mock_run):
    _, _, result, _, _ = mock_run
    by = {o.semantic_label: o for o in result.objects}
    assert by["glass"].depth_confidence < 0.5
    assert by["mug"].depth_confidence > 0.9
    assert by["glass"].fusion_weights["depth"] < by["mug"].fusion_weights["depth"]
