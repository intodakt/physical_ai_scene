"""S1 W11: dataset README generated from the bags."""

from scripts.make_demo_sequence import generate
from src.preprocessing.frame_loader import load_frame
from src.sensors import bag_replay, dataset_readme


def test_readme_from_bags(tmp_path):
    frames = [load_frame(d) for d in generate(tmp_path / "f", n_frames=4)]
    for k, f in enumerate(frames):
        f.timestamp = 50.0 + k / 30
    bag_replay.write_bag(frames, tmp_path / "bags" / "S1_static_take1", camera_info=True, lone_db3=False)
    bag_replay.write_bag(frames, tmp_path / "bags" / "misc", lone_db3=True)
    bags = dataset_readme.find_bags([tmp_path / "bags"])
    rows = [dataset_readme.describe(b) for b in bags]
    by = {r["bag"]: r for r in rows}
    assert by["S1_static_take1"]["scenario"] == "Static baseline" and by["S1_static_take1"]["camera_info"]
    assert by["S1_static_take1"]["fps"] == 30.0 and by["S1_static_take1"]["rgb_frames"] == 4
    assert by["misc"]["scenario"] == "unknown scenario" and not by["misc"]["camera_info"]
    md = dataset_readme.write_readme(rows, tmp_path / "DATASET.md").read_text()
    assert "| S1_static_take1 | Static baseline |" in md and (tmp_path / "DATASET.json").exists()
