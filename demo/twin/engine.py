"""Virtual table (digital twin) built from a real pipeline run, edited live, processed by the real pipeline.

How it works
------------
1. ``load_run`` reads what the pipeline measured on a recording: S2's 3D objects (centre, size, yaw,
   label) of the frame with the most objects, the recording's colour image and its map-frame point
   cloud (``points/<frame>.npz``).
2. ``Twin`` turns every object into a simple shape (box, cylinder, laptop) placed exactly where S2
   measured it. This is the virtual table.
3. Every edit (move, hide, show) is rendered back into an RGB-D frame + object masks with S2's
   ray-cast renderer (``src/preprocessing/mock_data.py``) and sent through the unchanged pipeline
   (``src/integration/pipeline.Pipeline``): S2 3D fusion -> S6 tracking -> S4 scene graph. Questions go
   through S5 (Ollama or the rule parser) and S6's ActionGoal + virtual-agent simulation.
   In twin frames S1 (camera) and S3 (YOLO-World + SAM) are replaced by the renderer.

A move is rendered as a short slide (several frames, at most ``MAX_STEP_M`` apart) so S6's tracker sees
the object travel, as it would in a video, instead of teleporting.

    python -m demo.twin                       # web UI (see demo/twin/server.py)
"""

from __future__ import annotations

import base64
import copy
import io
import json
import math
import shutil
import threading
import time
from pathlib import Path
from typing import Optional

import numpy as np
from PIL import Image

REPO = Path(__file__).resolve().parents[2]
MAX_STEP_M = 0.08                  # largest slide per rendered frame (S6 tracking gate is 0.15 m)
DESK_X, DESK_Y = (0.05, 1.35), (-0.55, 0.55)   # renderer desk top (mock_data: 1.4 x 1.2 m at x 0..1.4)
FRAME_DT = 0.5                     # seconds between twin frames (timestamps for S6 / S4)
ROUND_LABELS = ("mug", "cup", "glass", "bottle", "can", "jar", "vase", "apple", "egg", "orange", "ball", "fruit",
                "peach", "lemon", "tomato", "onion", "potato")
TRANSPARENT = ("glass", "transparent_suspected", "no_depth")
PALETTE = {"laptop": (70, 70, 78), "mug": (200, 60, 50), "cup": (200, 60, 50), "book": (40, 90, 170),
           "glass": (190, 215, 225), "bottle": (60, 140, 90), "multimeter": (235, 190, 30),
           "keyboard": (40, 40, 44), "mouse": (90, 90, 96)}


def _b64_jpeg(img: np.ndarray | Image.Image, size=(480, 360), quality=72) -> str:
    im = img if isinstance(img, Image.Image) else Image.fromarray(img)
    im = im.convert("RGB")
    im.thumbnail(size)
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=quality)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


# ---------------------------------------------------------------- source run
def find_runs() -> list[Path]:
    """Pipeline runs that can seed a twin: demo store runs, then outputs/pipeline."""
    from demo import runs as store

    found = [p.parent for p in sorted(store.RUNS.glob("*/run_summary.json"))]
    found.sort(key=lambda p: (p.name == store.BUILTIN, -p.stat().st_mtime))
    default = REPO / "outputs" / "pipeline"
    if (default / "run_summary.json").exists():
        found.append(default)
    return found


def default_run() -> Path:
    runs = find_runs()
    if runs:
        return runs[0]
    from demo import runs as store

    store.ensure_builtin()
    return store.RUNS / store.BUILTIN


def load_run(run_dir: str | Path) -> dict:
    """What the pipeline measured on the recording: objects of the richest frame, its image and cloud."""
    run_dir = Path(run_dir)
    summary = json.loads((run_dir / "run_summary.json").read_text(encoding="utf-8"))
    frames = summary.get("frames") or []
    if not frames:
        raise ValueError(f"{run_dir}: the run has no processed frames")
    best = max(reversed(frames), key=lambda f: f["n_objects"])          # latest frame among the richest
    objs = json.loads((run_dir / "objects" / f"{best['frame']}_objects.json").read_text(encoding="utf-8"))
    frame_dir = Path(best["frame_dir"])
    if not frame_dir.is_absolute():
        frame_dir = REPO / frame_dir
    rgb = None
    if (frame_dir / "rgb.png").exists():
        rgb = np.array(Image.open(frame_dir / "rgb.png").convert("RGB"))
    cloud = None
    npz = run_dir / "points" / f"{best['frame']}.npz"
    if npz.exists():
        with np.load(npz) as z:
            if "_scene" in z:
                pts, col = z["_scene"], z["_scene_rgb"]
                keep = np.isfinite(pts).all(1) & (pts[:, 2] > -0.05) & (pts[:, 2] < 0.6)
                pts, col = pts[keep], col[keep]
                if len(pts) > 40000:
                    idx = np.random.default_rng(0).choice(len(pts), 40000, replace=False)
                    pts, col = pts[idx], col[idx]
                cloud = {"xyz": np.round(pts, 4).ravel().tolist(), "rgb": col.astype(int).ravel().tolist()}
    return {"run": run_dir, "name": summary.get("dataset") or run_dir.name, "frame": best["frame"],
            "objects": objs["objects"], "rgb": rgb, "cloud": cloud, "frame_dir": frame_dir,
            "session_meta": summary.get("session_meta", {})}


def _colour(obj: dict, rgb: Optional[np.ndarray], frame_dir: Optional[Path] = None) -> tuple:
    """Median colour of the object's S3 mask in the recording (else the inner half of its 2D box, else a
    label colour)."""
    label = obj.get("semantic_label", "")
    if rgb is not None and frame_dir is not None and obj.get("source_observation_id"):
        m = frame_dir / "masks" / f"{obj['source_observation_id']}.png"
        if m.exists():
            mask = np.array(Image.open(m).convert("L")) > 127
            if mask.shape == rgb.shape[:2] and mask.sum() > 20:
                return tuple(int(v) for v in np.median(rgb[mask], axis=0))
    bb = obj.get("bbox_2d")
    if rgb is not None and bb:
        x1, y1, x2, y2 = (float(v) for v in bb)
        cx, cy, w, h = (x1 + x2) / 2, (y1 + y2) / 2, (x2 - x1) / 4, (y2 - y1) / 4
        patch = rgb[int(max(0, cy - h)):int(cy + h) + 1, int(max(0, cx - w)):int(cx + w) + 1]
        if patch.size:
            return tuple(int(v) for v in patch.reshape(-1, 3).mean(0))
    words = {"white": (225, 225, 220), "black": (35, 35, 40), "red": (190, 50, 45), "green": (60, 140, 70),
             "blue": (45, 90, 170), "yellow": (230, 190, 40), "silver": (180, 182, 188), "grey": (120, 120, 125),
             "gray": (120, 120, 125), "orange": (230, 130, 40), "brown": (120, 80, 45), "pink": (230, 150, 170)}
    for w in label.split():
        if w in words:
            return words[w]
    for k, c in {**PALETTE, "apple": (200, 50, 40), "egg": (240, 228, 205), "phone": (35, 35, 40),
                 "calculator": (40, 42, 48), "controller": (230, 230, 230)}.items():
        if k in label:
            return c
    return (150, 150, 155)


def spec_from_object(obj: dict, rgb: Optional[np.ndarray] = None, frame_dir: Optional[Path] = None) -> dict:
    """S2 ObjectInstance3D -> renderer spec (mock_data.OBJECTS entry) at the measured pose."""
    box = obj.get("box_map") or {}
    label = obj.get("semantic_label", "object")
    cx, cy = (box.get("center") or obj["centroid_map"])[:2]
    d0, d1, dz = box.get("dimensions") or obj["box_dimensions"]
    yaw = float(box.get("yaw", 0.0))
    d0, d1, dz = max(d0, 0.02), max(d1, 0.02), max(dz, 0.01)
    status = obj.get("depth_status") or ""
    spec = {"name": obj.get("persistent_id") or obj["object_id"], "label": label, "xy": (float(cx), float(cy)),
            "labels": list(obj.get("label_candidates") or [label]), "score": float(obj.get("detector_score") or 0.8),
            "color": _colour(obj, rgb, frame_dir), "dropout": 0.85 if (label == "glass" or status in TRANSPARENT) else 0.0}
    if any(w in label for w in ROUND_LABELS):
        spec.update(kind="cylinder", size=(max(d0, d1) / 2, dz), yaw=0.0)
    elif "laptop" in label:
        # mock_data's laptop: base (depth x width x 2 cm) + screen hinged on the local +x edge.
        # The shorter footprint side is the depth; turn it so the screen is on the side away from the camera.
        depth, width = (d0, d1) if d0 <= d1 else (d1, d0)
        ax = yaw if d0 <= d1 else yaw - math.pi / 2
        if math.cos(ax) < 0:
            ax += math.pi
        spec.update(kind="laptop", size=(max(0.12, depth * 0.8), width, 0.02), yaw=math.degrees(ax))
    else:
        spec.update(kind="box", size=(d0, d1, dz), yaw=math.degrees(yaw))
    return spec


def footprint_radius(spec: dict) -> float:
    s = spec["size"]
    if spec["kind"] == "cylinder":
        return s[0]
    return 0.5 * math.hypot(s[0], s[1])


def virtual_camera(specs: list) -> tuple[list, list]:
    """map -> camera_link (xyz, rpy) that looks down at all objects with the renderer's 55° lens."""
    if not specs:
        return [0.0, 0.0, 0.6], [0.0, math.radians(45), 0.0]
    xy = np.array([s["xy"] for s in specs])
    lo, hi = xy.min(0) - 0.12, xy.max(0) + 0.12
    c = (lo + hi) / 2
    extent = float(max(hi[1] - lo[1], (hi[0] - lo[0]) * 1.3, 0.5))
    dist = max(0.75, extent * 1.05)
    pitch = math.radians(48)
    return ([float(c[0] - dist * math.cos(pitch)), float(c[1]), float(dist * math.sin(pitch))], [0.0, pitch, 0.0])


def _seg_dist(p, a, b) -> float:
    ax, ay, bx, by = *a, *b
    dx, dy = bx - ax, by - ay
    t = max(0.0, min(1.0, ((p[0] - ax) * dx + (p[1] - ay) * dy) / ((dx * dx + dy * dy) or 1.0)))
    return math.dist(p, (ax + t * dx, ay + t * dy))


# ---------------------------------------------------------------- twin
class Twin:
    """The editable virtual table plus the pipeline that processes it. Thread-safe (one edit at a time)."""

    def __init__(self, run_dir: str | Path | None = None, workdir: str | Path | None = None,
                 parser: str = "auto", planner: Optional[str] = None, obstacles: str = "all"):
        from demo import runs as store

        self.lock = threading.RLock()
        self.workdir = Path(workdir) if workdir else store.STORE / "twin"
        self.parser_mode = parser
        self.source = load_run(run_dir or default_run())
        self.base = [spec_from_object(o, self.source["rgb"], self.source["frame_dir"]) for o in self.source["objects"]]
        self.cam_xyz, self.cam_rpy = virtual_camera(self.base)
        self.planner = planner
        if obstacles not in ("all", "config"):
            raise ValueError("obstacles must be 'all' or 'config'")
        self.obstacles = obstacles
        # the virtual robot starts on the camera side of the objects, on the desk (not inside an object)
        self.agent_start = self._pick_agent_start() if self.base else None
        self.reset()

    def _pick_agent_start(self) -> list:
        """Front edge of the objects; the y with clear straight lines to the most objects (S6 margin 3 cm)."""
        xs = [sp["xy"][0] - footprint_radius(sp) for sp in self.base]
        ys = [sp["xy"][1] for sp in self.base]
        x0 = max(DESK_X[0], min(xs) - 0.08)
        med = float(np.median(ys))

        def n_clear(start):
            k = 0
            for sp in self.base:
                if all(_seg_dist(o["xy"], start, sp["xy"]) > footprint_radius(o) + 0.05
                       for o in self.base if o is not sp):
                    k += 1
            return k

        cands = [(x0, y) for y in np.linspace(min(ys) - 0.1, max(ys) + 0.1, 13)]
        best = max(cands, key=lambda c: (n_clear(c), -abs(c[1] - med)))
        return [round(float(best[0]), 3), round(float(best[1]), 3)]

    def _action_cfg(self):
        """S6 settings for this twin. S6's code is unchanged; only its config differs:
        obstacles='all' makes every object except the target an exclusion zone (the team config lists only
        the laptop), and the agent starts in front of this table's objects."""
        a = self.pipe.cfg["action"]
        if not hasattr(self, "_config_exclusion"):
            self._config_exclusion = list(a.get("exclusion_labels", []))
        if self.planner:
            a["planner"] = self.planner
        if self.agent_start:
            a["agent_start"] = list(self.agent_start)
        if self.obstacles == "all":
            words = set()
            for sp in self.specs.values():
                for lab in [sp["label"], *sp["labels"]]:
                    words |= set(str(lab).replace("_", " ").split())
            a["exclusion_labels"] = sorted(words)
        else:
            a["exclusion_labels"] = list(self._config_exclusion)

    def set_obstacles(self, mode: str) -> dict:
        if mode not in ("all", "config"):
            raise ValueError("obstacles must be 'all' or 'config'")
        with self.lock:
            self.obstacles = mode
            self._action_cfg()
            return self.state()

    # ------------------------------------------------------------ state
    def reset(self):
        """Back to the table as recorded; a fresh pipeline (tracker and scene graph start empty)."""
        from src.integration.pipeline import Pipeline

        with self.lock:
            self.specs = {s["name"]: copy.deepcopy(s) for s in self.base}
            self.hidden: set[str] = set()
            shutil.rmtree(self.workdir, ignore_errors=True)
            self.pipe = Pipeline(self.workdir / "run", parser=self.parser_mode)
            self.specs = {s["name"]: copy.deepcopy(s) for s in self.base}
            self._action_cfg()
            self.k = 0
            self.t0 = 1.0e9
            self.log: list[dict] = []          # one entry per user action
            self.last_query: Optional[dict] = None
            self.last_frame: Optional[dict] = None
            self._step("Twin built from the recording", [])
            self._step("Twin built from the recording", [])   # 2 frames so S4 relations settle

    def _visible_specs(self) -> list:
        return [copy.deepcopy(s) for n, s in self.specs.items() if n not in self.hidden]

    def _render(self) -> Path:
        from src.preprocessing import mock_data

        d = self.workdir / "frames" / f"frame_{self.k:04d}"
        orig = (mock_data.OBJECTS, mock_data.CAMERA_XYZ, mock_data.CAMERA_RPY)
        try:
            mock_data.OBJECTS = self._visible_specs()
            mock_data.CAMERA_XYZ, mock_data.CAMERA_RPY = self.cam_xyz, self.cam_rpy
            mock_data.generate(d, seed=self.k, timestamp=self.t0 + self.k * FRAME_DT, profile="realsense")
        finally:
            mock_data.OBJECTS, mock_data.CAMERA_XYZ, mock_data.CAMERA_RPY = orig
        self.k += 1
        return d

    def _step(self, action: str, changes: list) -> dict:
        d = self._render()
        rec = self.pipe.process(d)
        self.last_frame = {"dir": d, **rec}
        return rec

    def _settle(self, name: str, max_frames: int = 4) -> list:
        """Still frames after a slide; S6 reports MOVED once the object's speed has decayed (rest)."""
        recs = []
        for _ in range(max_frames):
            recs.append(self._step("settle", [name]))
            if any(e["event"] == "MOVED" and e["persistent_id"] == name for e in recs[-1]["events"]):
                break
        return recs

    def visible_fraction(self, name: str, xy: tuple) -> float:
        """Share of ``name``'s pixels the virtual camera would see at ``xy`` (1 = nothing in front of it)."""
        import tempfile

        from src.preprocessing import mock_data

        def area(specs):
            orig = (mock_data.OBJECTS, mock_data.CAMERA_XYZ, mock_data.CAMERA_RPY)
            with tempfile.TemporaryDirectory() as tmp:
                try:
                    mock_data.OBJECTS = specs
                    mock_data.CAMERA_XYZ, mock_data.CAMERA_RPY = self.cam_xyz, self.cam_rpy
                    out = mock_data.generate(Path(tmp) / "f", seed=0, profile="realsense")
                finally:
                    mock_data.OBJECTS, mock_data.CAMERA_XYZ, mock_data.CAMERA_RPY = orig
                obs = json.loads((out / "observation.json").read_text(encoding="utf-8"))
                want = self.specs[name]["labels"]
                for det in obs["detections"]:
                    if det["labels"] == want:
                        return int((np.array(Image.open(out / det["mask"])) > 127).sum())
            return 0

        me = dict(copy.deepcopy(self.specs[name]), xy=tuple(xy))
        alone = area([me])
        if not alone:
            return 0.0
        others = [s for s in self._visible_specs() if s["name"] != name]
        return area(others + [me]) / alone

    def _record(self, action: str, recs: list, t_start: float):
        events = [f"{e['event']} {e['persistent_id']}" for r in recs for e in r["events"]]
        self.log.append({"action": action, "frames": [r["frame"] for r in recs], "events": events,
                         "seconds": round(time.perf_counter() - t_start, 2)})
        self.last_query = None

    # ------------------------------------------------------------ edits
    def _clamp(self, name: str, x: float, y: float) -> tuple[float, float]:
        r = footprint_radius(self.specs[name])
        return (min(max(x, DESK_X[0] + r), DESK_X[1] - r), min(max(y, DESK_Y[0] + r), DESK_Y[1] - r))

    def collisions(self, name: str, x: float, y: float) -> list[str]:
        """Visible objects whose footprint would overlap ``name`` placed at (x, y)."""
        r = footprint_radius(self.specs[name]) * 0.85
        hits = []
        for other, s in self.specs.items():
            if other == name or other in self.hidden:
                continue
            if math.dist((x, y), s["xy"]) < r + footprint_radius(s) * 0.85:
                hits.append(other)
        return hits

    def move(self, name: str, x: float, y: float) -> dict:
        with self.lock:
            if name not in self.specs:
                raise KeyError(f"no object {name!r}")
            if name in self.hidden:
                raise ValueError(f"{name} is hidden; show it first")
            t = time.perf_counter()
            x, y = self._clamp(name, float(x), float(y))
            hits = self.collisions(name, x, y)
            if hits:
                raise ValueError(f"{name} would overlap {', '.join(hits)}: pick a free spot on the desk")
            x0, y0 = self.specs[name]["xy"]
            n = max(1, math.ceil(math.dist((x0, y0), (x, y)) / MAX_STEP_M))
            recs = []
            for i in range(1, n + 1):
                self.specs[name]["xy"] = (x0 + (x - x0) * i / n, y0 + (y - y0) * i / n)
                recs.append(self._step("move", [name]))
            recs += self._settle(name)                      # still frames until S6 confirms the new rest pose
            self._record(f"Moved {name} {math.dist((x0, y0), (x, y)) * 100:.0f} cm", recs, t)
            return self.state()

    def rotate(self, name: str, degrees: float) -> dict:
        with self.lock:
            if name not in self.specs or name in self.hidden:
                raise ValueError(f"{name} is not on the desk")
            t = time.perf_counter()
            self.specs[name]["yaw"] = float(self.specs[name].get("yaw", 0.0)) + float(degrees)
            recs = [self._step("rotate", [name])]
            self._record(f"Turned {name} {degrees:+.0f}°", recs, t)
            return self.state()

    def hide(self, name: str) -> dict:
        with self.lock:
            if name not in self.specs:
                raise KeyError(f"no object {name!r}")
            t = time.perf_counter()
            self.hidden.add(name)
            recs = [self._step("hide", [name])]
            self._record(f"Hid {name}", recs, t)
            return self.state()

    def show(self, name: str) -> dict:
        with self.lock:
            if name not in self.specs:
                raise KeyError(f"no object {name!r}")
            hits = self.collisions(name, *self.specs[name]["xy"])
            if hits:
                raise ValueError(f"{name}'s spot is taken by {', '.join(hits)}: move that first")
            t = time.perf_counter()
            self.hidden.discard(name)
            recs = [self._step("show", [name])]
            self._record(f"Put {name} back", recs, t)
            return self.state()

    def wait(self, frames: int = 1) -> dict:
        """Let time pass (still frames): hidden objects age in S6's memory."""
        with self.lock:
            t = time.perf_counter()
            recs = [self._step("wait", []) for _ in range(max(1, int(frames)))]
            self._record(f"Waited {len(recs)} frame(s)", recs, t)
            return self.state()

    def set_planner(self, planner: str) -> dict:
        if planner not in ("straight", "detour"):
            raise ValueError("planner must be 'straight' or 'detour'")
        with self.lock:
            self.planner = planner
            self.pipe.cfg["action"]["planner"] = planner
            return self.state()

    def ask(self, question: str) -> dict:
        with self.lock:
            question = (question or "").strip()
            if not question:
                raise ValueError("type a question first")
            t = time.perf_counter()
            res = self.pipe.ask(question)
            res["seconds"] = round(time.perf_counter() - t, 2)
            res["parser"] = self.pipe.parser
            self.last_query = res
            return self.state()

    # ------------------------------------------------------------ presets (backup buttons)
    def _find(self, *words) -> Optional[str]:
        for n, s in self.specs.items():
            if any(w in s["label"] for w in words):
                return n
        return None

    def presets(self) -> list[dict]:
        out = []
        mug, book = self._find("mug", "cup"), self._find("book")
        laptop, glass = self._find("laptop"), self._find("glass", "bottle")
        if mug:
            out.append({"id": "slide", "title": f"Slide the {self.specs[mug]['label']}",
                        "question": f"Go to the {self.specs[mug]['label']}"})
        if book:
            out.append({"id": "hide", "title": f"Hide the {self.specs[book]['label']}",
                        "question": f"Go to the {self.specs[book]['label']}"})
        if laptop and (glass or mug):
            obj = glass or mug
            out.append({"id": "behind", "title": f"{self.specs[obj]['label'].capitalize()} past the laptop",
                        "question": f"Go to the {self.specs[obj]['label']}"})
        pick = self._block_pick()
        if pick:
            target, blocker = pick
            out.append({"id": "block", "title": f"Block the path with the {self.specs[blocker]['label']}",
                        "question": f"Go to the {self.specs[target]['label']}"})
        return out

    def _block_candidates(self) -> list:
        """(target, blocker) pairs for 'block the path', best first (target with a clear path, far away)."""
        if self.obstacles != "all":
            return []
        vis = [n for n in self.specs if n not in self.hidden]
        if len(vis) < 2:
            return []
        from src.planning.action import footprint_polygon, path_hits

        cfg = self.pipe.cfg["action"]
        agent = cfg["agent_start"]
        nodes = {n["id"]: n for n in self.pipe.graph["nodes"] if not n.get("virtual") and n.get("state") != "occluded"}

        def clear(n):       # S6's own zones and path check, as build_action_goal will do it
            if n not in nodes:
                return False
            zones = [{"object_id": o, "polygon": footprint_polygon(nd, cfg.get("exclusion_margin_m", 0.03) + 0.01)}
                     for o, nd in nodes.items() if o != n]
            return not path_hits([agent, nodes[n]["pose_map"][:2]], zones, cfg.get("step_m", 0.01))

        labels = [self.specs[n]["label"] for n in vis]
        unique = [n for n in vis if labels.count(self.specs[n]["label"]) == 1] or vis
        far = sorted(unique, key=lambda n: (not clear(n), -math.dist(agent, self.specs[n]["xy"])))
        pairs = []
        for t in far:
            for b in sorted((n for n in vis if n != t), key=lambda n: footprint_radius(self.specs[n])):
                pairs.append((t, b))
        return pairs

    def _block_pick(self):
        c = self._block_candidates()
        return c[0] if c else None

    def _block_spots(self, target: str, blocker: str) -> list:
        agent = self.pipe.cfg["action"]["agent_start"]
        tx, ty = self.specs[target]["xy"]
        r = footprint_radius(self.specs[blocker])
        L = math.dist(agent, (tx, ty)) or 1.0
        nx, ny = -(ty - agent[1]) / L, (tx - agent[0]) / L
        out = []
        for t in (0.5, 0.42, 0.58, 0.35, 0.65, 0.3, 0.72, 0.25, 0.8):
            for off in (0.0, 0.015, -0.015):
                x, y = agent[0] + (tx - agent[0]) * t + nx * off, agent[1] + (ty - agent[1]) * t + ny * off
                if math.dist((x, y), agent) > r + 0.06 and \
                        math.dist((x, y), (tx, ty)) > r + footprint_radius(self.specs[target]) + 0.03:
                    out.append((x, y))
        return out

    def _free_spot(self, name: str, candidates) -> tuple[float, float]:
        for x, y in candidates:
            x, y = self._clamp(name, x, y)
            if not self.collisions(name, x, y):
                return x, y
        raise ValueError(f"no free spot found for {name}")

    def _spot_past_laptop(self) -> tuple:
        """A free, visible spot for the glass (or mug) whose straight path from the agent crosses the laptop zone."""
        from src.planning.action import footprint_polygon, inside, path_hits

        name = self._find("glass", "bottle") or self._find("mug", "cup")
        lap_name = self._find("laptop")
        lap = self.specs[lap_name]
        node = next((n for n in self.pipe.graph["nodes"] if n["id"] == lap_name), None)
        if node is None:
            raise ValueError("the laptop is not in the scene graph right now")
        cfg = self.pipe.cfg["action"]
        # the same zone S6 will draw: S4's laptop node inflated by the configured margin (+2 cm so the
        # S2-measured glass position, a little off the twin position, still lands past the laptop)
        zone = [{"object_id": lap_name, "polygon": footprint_polygon(node, cfg.get("exclusion_margin_m", 0.03))}]
        wide = [{"object_id": lap_name, "polygon": footprint_polygon(node, cfg.get("exclusion_margin_m", 0.03) + 0.02)}]
        agent = cfg["agent_start"]
        lx, ly = node["pose_map"][:2]
        half = 0.5 * max(node["size"][:2])
        cands = []
        for r in (half + 0.08, half + 0.14, half + 0.2):
            for deg in range(-80, 81, 10):
                a = math.atan2(ly - agent[1], lx - agent[0]) + math.radians(deg)
                x, y = self._clamp(name, lx + r * math.cos(a), ly + r * math.sin(a))
                if inside((x, y), wide[0]["polygon"]) or self.collisions(name, x, y):
                    continue
                # robust crossing: the line must still cross the zone with the target 3 cm either side
                ends = [[x + dx, y + dy] for dx, dy in ((0, 0), (0.03, 0), (-0.03, 0), (0, 0.03), (0, -0.03))]
                if not all(path_hits([agent, e], zone, cfg.get("step_m", 0.01)) for e in ends):
                    continue
                cands.append((100 * r - abs(deg), x, y))   # prefer close to the laptop and off to its side
        if not cands:
            raise ValueError("no free spot past the laptop on this table")
        for _, x, y in sorted(cands)[:8]:
            if self.visible_fraction(name, (x, y)) >= 0.6:
                return name, x, y
        raise ValueError("every spot behind the laptop is hidden from the camera")

    def run_preset(self, pid: str) -> dict:
        with self.lock:
            p = {q["id"]: q for q in self.presets()}.get(pid)
            if not p:
                raise ValueError(f"preset {pid!r} is not available for this table")
            if pid == "slide":
                n = self._find("mug", "cup")
                x, y = self.specs[n]["xy"]
                spot = self._free_spot(n, [(x - 0.1, y - 0.12), (x - 0.1, y + 0.12), (x + 0.12, y - 0.1), (x - 0.15, y)])
                self.move(n, *spot)
            elif pid == "hide":
                n = self._find("book")
                if n not in self.hidden:
                    self.hide(n)
            elif pid == "behind":
                self.move(*self._spot_past_laptop())
            elif pid == "block":
                for target, blocker in self._block_candidates():
                    spots = [(x, y) for x, y in self._block_spots(target, blocker)
                             if not self.collisions(blocker, *self._clamp(blocker, x, y))]
                    if spots:
                        self.move(blocker, *spots[0])
                        p = {"question": f"Go to the {self.specs[target]['label']}"}
                        break
                else:
                    raise ValueError("no free spot on the robot's path for any object on this table")
            return self.ask(p["question"])

    # ------------------------------------------------------------ view model for the web page
    def state(self) -> dict:
        with self.lock:
            graph = self.pipe.graph
            payload = {}
            if self.last_frame:
                f = self.pipe.out / "objects" / f"{self.last_frame['frame']}_objects.json"
                if f.exists():
                    payload = json.loads(f.read_text(encoding="utf-8"))
            measured = {o["persistent_id"]: o for o in payload.get("objects", [])}
            nodes = []
            for n in graph["nodes"]:
                if n.get("virtual"):
                    continue
                m = measured.get(n["id"], {})
                nodes.append({"id": n["id"], "label": n["names"][0]["text"] if n.get("names") else n["id"],
                              "pose": n["pose_map"], "size": n["size"], "yaw": n.get("yaw", 0.0),
                              "state": n.get("state"), "confidence": n.get("confidence"),
                              "depth_confidence": m.get("depth_confidence", n.get("depth_confidence")),
                              "depth_status": m.get("depth_status")})
            edges = [{"s": e["source"], "p": e["predicate"], "t": e["target"],
                      "distance_m": (e.get("evidence") or {}).get("distance_m")}
                     for e in graph["edges"] if e.get("end_time") is None]
            twin = [{"name": n, "label": s["label"], "kind": s["kind"], "xy": s["xy"], "size": s["size"],
                     "yaw": s.get("yaw", 0.0), "color": s["color"], "hidden": n in self.hidden,
                     "transparent": s["dropout"] > 0} for n, s in self.specs.items()]
            frame = None
            if self.last_frame:
                d = self.last_frame["dir"]
                frame = {"name": self.last_frame["frame"], "timings_ms": self.last_frame["timings_ms"],
                         "rgb": _b64_jpeg(Image.open(d / "rgb.png")), "events": [
                             f"{e['event']} {e['persistent_id']}" for e in self.last_frame["events"]]}
            q = None
            if self.last_query:
                r, g = self.last_query["reasoning_result"], self.last_query["action_goal"]
                q = {"question": self.last_query["question"], "answer": r.get("final_answer"),
                     "verified": r.get("verification_status"), "warnings": r.get("warnings", []),
                     "parsed": r.get("llm_parsed_query"), "parser": self.last_query.get("parser"),
                     "target": g.get("target_object_id"), "validated": g.get("validated"),
                     "code": g.get("reason_code"), "reason": g.get("reason"), "path": g.get("path"),
                     "start": g.get("agent_start"), "goal_warnings": g.get("warnings", []),
                     "zones": [z["polygon"] for z in g.get("exclusion_zones", [])],
                     "simulation": self.last_query.get("simulation"), "timings_ms": self.last_query.get("timings_ms"),
                     "seconds": self.last_query.get("seconds")}
            s = self.pipe.summary()
            return {"twin": twin, "nodes": nodes, "edges": edges, "frame": frame, "query": q,
                    "log": self.log[-30:], "presets": self.presets(),
                    "planner": self.pipe.cfg["action"]["planner"], "parser": self.pipe.parser,
                    "agent_start": self.pipe.cfg["action"]["agent_start"], "obstacles": self.obstacles,
                    "exclusion_labels": self.pipe.cfg["action"].get("exclusion_labels", []),
                    "n_frames": s["n_frames"], "mean_latency_ms": s["mean_latency_ms"],
                    "contract_errors": len(s["contract_errors"]),
                    "desk": {"x": DESK_X, "y": DESK_Y},
                    "camera": {"xyz": self.cam_xyz, "rpy": self.cam_rpy}}

    def source_info(self) -> dict:
        src = self.source
        return {"name": src["name"], "frame": src["frame"], "run": src["run"].name,
                "n_objects": len(src["objects"]),
                "rgb": _b64_jpeg(src["rgb"]) if src["rgb"] is not None else None,
                "cloud": src["cloud"],
                "measured": [{"name": o.get("persistent_id") or o["object_id"], "label": o.get("semantic_label"),
                              "center": (o.get("box_map") or {}).get("center") or o.get("centroid_map")}
                             for o in src["objects"]]}
