"""Mock "desk interaction" sequence for the S7 smoke test and dashboard (until S1's bags are shared).

Uses S2's ray-cast mock generator (src/preprocessing/mock_data.py) frame by frame:
  * the mug slides 1.3 cm per frame towards the laptop  -> S6 tracking must keep mug_01;
  * the book is taken away in two frames, then put back -> S4 marks it occluded, S6 re-uses book_01.

    python scripts/make_demo_sequence.py --out data/demo/desk_sequence --frames 8
    python scripts/make_demo_sequence.py --out data/demo/desk_bag --frames 8 --bag   # also a ROS 2 bag
"""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path

from src.preprocessing import mock_data

FPS = 15.0
T0 = 1760572800.0  # 16 Oct 2026


BASE_SCENE = copy.deepcopy(mock_data.OBJECTS)


def scene_at(k: int) -> list:
    objs = copy.deepcopy(BASE_SCENE)
    for o in objs:
        if o["name"] == "mug":
            o["xy"] = (o["xy"][0] - 0.005 * k, o["xy"][1] + 0.012 * k)
    if k in (4, 5):
        objs = [o for o in objs if o["name"] != "book"]
    return objs


def generate(out_dir, n_frames: int = 8, profile: str = "realsense") -> list[Path]:
    original = mock_data.OBJECTS
    paths = []
    try:
        for k in range(n_frames):
            mock_data.OBJECTS = scene_at(k)
            paths.append(mock_data.generate(Path(out_dir) / f"frame_{k:04d}", seed=200 + k,
                                            timestamp=T0 + k / FPS, profile=profile))
    finally:
        mock_data.OBJECTS = original
    (Path(out_dir) / "sequence.json").write_text(json.dumps({
        "source": "MOCK desk sequence (scripts/make_demo_sequence.py) - stand-in for S1's ROS 2 bag",
        "frames": n_frames, "fps": FPS, "profile": profile,
        "events": {"mug": "slides 1.3 cm per frame towards the laptop", "book": "hidden in frames 4-5"}}, indent=2))
    return paths


def to_bag(frame_paths, bag_path, profile="zed_mini") -> Path:
    """Write the frames as a ROS 2 bag with S1's ZED Mini topics (S2's writer)."""
    from src.preprocessing.bag_reader import write_bag
    from src.preprocessing.frame_loader import load_frame

    return write_bag([load_frame(p) for p in frame_paths], bag_path, profile=profile)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default="data/demo/desk_sequence")
    ap.add_argument("--frames", type=int, default=8)
    ap.add_argument("--profile", choices=sorted(mock_data.CAMERA_PROFILES), default="realsense")
    ap.add_argument("--bag", action="store_true", help="also write <out>_bag (ROS 2, ZED Mini topics)")
    a = ap.parse_args()
    paths = generate(a.out, a.frames, a.profile)
    print(f"{len(paths)} frames -> {a.out}")
    if a.bag:
        print("bag ->", to_bag(paths, Path(f"{a.out}_bag")))


if __name__ == "__main__":
    main()
