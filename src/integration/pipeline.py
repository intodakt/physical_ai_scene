"""S7 master pipeline: S1 -> S3 -> S2 -> S6 (tracking) -> S4 -> S5 -> S6 (action) -> virtual twin.

Every stage calls the owner's own code; S7 only moves data between them, times each stage and
checks each hand-over against the JSON contracts (src/integration/contracts.py).
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np
import yaml

from ..fusion_3d.pipeline import load_config as load_s2_config
from ..fusion_3d.pipeline import prepare_depth, process_frame
from ..fusion_3d.projection import deproject_depth
from ..fusion_3d.transforms import apply_transform
from ..preprocessing.frame_loader import find_observation_file, load_frame, load_semantic_observations
from ..scene_graph.engine import SceneGraphEngine
from . import contracts, s5_adapter
from .s6_placeholder import CentroidTracker, build_action_goal, simulate

REPO = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = REPO / "configs" / "s7_integration.yaml"
STAGES = ("s1_load", "s3_perception", "s2_fusion", "s6_tracking", "s4_graph")


def load_config(path=None) -> dict:
    return yaml.safe_load(Path(path or DEFAULT_CONFIG).read_text(encoding="utf-8"))


def frame_dirs(path) -> list[Path]:
    """A single S1 frame folder, or a folder of frame_XXXX sub-folders."""
    path = Path(path)
    if (path / "rgb.png").exists():
        return [path]
    dirs = sorted(p for p in path.iterdir() if p.is_dir() and (p / "rgb.png").exists())
    if not dirs:
        raise FileNotFoundError(f"no S1 frames (rgb.png) under {path}")
    return dirs


def frames_from_bag(bag, out_dir, profile="zed_mini", every=1, limit=None) -> list[Path]:
    """S1 ROS 2 bag -> synchronized frame folders (S2's reader, no ROS install needed)."""
    from ..preprocessing.bag_reader import export_frames

    paths, stats = export_frames(bag, out_dir, profile=profile, every=every, limit=limit)
    print(f"[S1] {len(paths)} synchronized frames from {bag} ({stats})")
    return paths


class Pipeline:
    def __init__(self, out_dir="outputs/pipeline", config=None, s3_mode=None, parser=None):
        self.cfg = load_config(config) if not isinstance(config, dict) else config
        self.out = Path(out_dir)
        for sub in ("objects", "scene_graph", "points", "reasoning"):
            (self.out / sub).mkdir(parents=True, exist_ok=True)
        self.s2_cfg = load_s2_config()
        self.s3_mode = s3_mode or self.cfg["stages"]["s3_mode"]
        self.parser = s5_adapter.resolve_parser(parser or self.cfg["stages"]["s5_parser"])
        self.tracker = CentroidTracker(**self.cfg["tracking"])
        self.graph_engine = SceneGraphEngine(desk_top_z=self.cfg["scene_graph"]["desk_top_z"],
                                             session_id=self.out.name)
        self._s3 = None
        self.frames: list[dict] = []
        self.contract_errors: list[str] = []

    # ------------------------------------------------------------ helpers
    def _check(self, kind, data, where):
        errs = contracts.CHECKS[kind](data)
        self.contract_errors += [f"{where}: {e}" for e in errs]
        return data

    def _write(self, rel, data):
        p = self.out / rel
        p.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return p

    def _observations(self, frame_dir: Path, frame):
        if self.s3_mode == "replay":
            try:
                path = find_observation_file(frame_dir)
            except FileNotFoundError as e:
                raise FileNotFoundError(f"{e}: run S3 on these frames first, or use --s3 live") from None
        else:  # live YOLO-World + SAM through S3's own pipeline
            if self._s3 is None:
                from ..open_vocab.models import SamSegmenter, WorldDetector
                from ..open_vocab.pipeline import PerceptionPipeline
                from ..open_vocab.pipeline import load_config as load_s3_config

                s3cfg = load_s3_config(REPO / self.cfg["stages"]["s3_config"])
                self._s3 = PerceptionPipeline(WorldDetector(s3cfg), SamSegmenter(s3cfg["segmenter"]), s3cfg)
            out = self.out / "s3" / frame_dir.name
            path = self._s3.process_frame(np.ascontiguousarray(frame.rgb[..., ::-1]), frame_id=frame_dir.name,
                                          timestamp=frame.timestamp, output_dir=out)
        self._check("observation", json.loads(Path(path).read_text(encoding="utf-8")), f"S3 {frame_dir.name}")
        skipped: list = []
        return load_semantic_observations(path, skipped), skipped, path

    # ------------------------------------------------------------ per frame
    def process(self, frame_dir, T_map_camera=None) -> dict:
        frame_dir = Path(frame_dir)
        name = frame_dir.name
        t = {}
        t0 = time.perf_counter()
        frame = load_frame(frame_dir)                                       # S1
        if frame.T_map_camera is None and T_map_camera is not None:
            frame.T_map_camera = np.asarray(T_map_camera, dtype=float)
        t["s1_load"] = time.perf_counter() - t0

        t0 = time.perf_counter()
        obs, skipped, obs_path = self._observations(frame_dir, frame)       # S3
        t["s3_perception"] = time.perf_counter() - t0

        t0 = time.perf_counter()
        result = process_frame(frame, obs, self.s2_cfg)                     # S2
        payload = {"frame": name, "timestamp": frame.timestamp, "frame_id": frame.frame_id, **result.to_dict()}
        payload["rejected"] = skipped + payload["rejected"]
        t["s2_fusion"] = time.perf_counter() - t0

        t0 = time.perf_counter()
        self.tracker.update(payload["objects"])                             # S6 tracking
        t["s6_tracking"] = time.perf_counter() - t0
        self._check("objects", payload, f"S2 {name}")
        self._write(f"objects/{name}_objects.json", payload)

        t0 = time.perf_counter()
        self.graph_engine.update(payload)                                   # S4
        graph = self.graph_engine.export()
        t["s4_graph"] = time.perf_counter() - t0
        self._check("scene_graph", graph, f"S4 {name}")
        self._write(f"scene_graph/{name}_scene_graph.json", graph)
        self._write("scene_graph/latest.json", graph)

        self._save_points(name, frame, result, payload)
        rec = {"frame": name, "frame_dir": frame_dir.as_posix(), "observation": Path(obs_path).as_posix(),
               "timestamp": frame.timestamp, "n_objects": len(payload["objects"]),
               "n_rejected": len(payload["rejected"]),
               "ids": {o["object_id"]: o["persistent_id"] for o in payload["objects"]},
               "track_motion_m": dict(self.tracker.last_motion),
               "timings_ms": {k: round(v * 1e3, 2) for k, v in t.items()}}
        rec["timings_ms"]["total"] = round(sum(t.values()) * 1e3, 2)
        self.frames.append(rec)
        return rec

    def _save_points(self, name, frame, result, payload):
        """Map-frame clouds for the dashboard's 3D view: the scene (subsampled) and each object."""
        T = result.T_map_camera
        if T is None:
            return
        pts, uv = deproject_depth(prepare_depth(frame, self.s2_cfg), frame.intrinsics, stride=6)
        arrays = {"_scene": apply_transform(T, pts).astype(np.float32),
                  "_scene_rgb": frame.rgb[uv[:, 1], uv[:, 0]].astype(np.uint8)}
        ids = {o["object_id"]: o["persistent_id"] for o in payload["objects"]}
        for oid, P in result.object_points.items():
            if oid in ids and len(P):
                arrays[ids[oid]] = apply_transform(T, P).astype(np.float32)
        np.savez_compressed(self.out / "points" / f"{name}.npz", **arrays)

    # ------------------------------------------------------------ query
    @property
    def graph(self) -> dict:
        return self.graph_engine.export()

    def ask(self, question: str) -> dict:
        graph = self.graph
        t0 = time.perf_counter()
        reasoning = s5_adapter.answer(question, graph, self.parser)                 # S5
        t_s5 = time.perf_counter() - t0
        self._check("reasoning_result", reasoning, "S5")
        t0 = time.perf_counter()
        goal = build_action_goal(reasoning, graph, self.cfg["action"])              # S6 action
        sim = simulate(goal, graph, self.cfg["action"])                             # virtual twin
        t_s6 = time.perf_counter() - t0
        self._check("action_goal", goal, "S6")
        out = {"question": question, "reasoning_result": reasoning, "action_goal": goal, "simulation": sim,
               "timings_ms": {"s5_reasoning": round(t_s5 * 1e3, 2), "s6_action": round(t_s6 * 1e3, 2)}}
        self._write("reasoning/last_query.json", out)
        return out

    def summary(self) -> dict:
        totals = [f["timings_ms"]["total"] for f in self.frames]
        per_stage = {s: round(float(np.mean([f["timings_ms"][s] for f in self.frames])), 2) for s in STAGES} \
            if self.frames else {}
        mean = float(np.mean(totals)) if totals else 0.0
        return {"n_frames": len(self.frames), "s3_mode": self.s3_mode, "s5_parser": self.parser,
                "mean_latency_ms": round(mean, 2), "fps": round(1e3 / mean, 3) if mean else 0.0,
                "stage_latency_ms": per_stage, "contract_errors": self.contract_errors, "frames": self.frames}
