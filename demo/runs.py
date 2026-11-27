"""Demo store: datasets (imported recordings) and pipeline runs, shared by the web app and the CLI.

Layout under ``DEMO_DATA_DIR`` (default ``data/demo_store``; mount a volume there on Railway):

    datasets/<name>/frames/frame_XXXX/...      S1 frames (+ S3 observation.json, masks/)
    datasets/<name>/session_meta.json          bag topics, intrinsics source, TF source, S3 alignment
    runs/<name>/run_summary.json               S7 summary of the pipeline run on that dataset
    runs/<name>/objects|scene_graph|points/    S2 / S4 outputs per frame

    python -m demo.runs --builtin                     # synthetic desk recording (always available)
    python -m demo.runs --import S2_package.zip       # import + run
    python -m demo.runs --url https://drive.google.com/file/d/<id>/view
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import time
import urllib.request
from pathlib import Path
from typing import Callable, Optional

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from src.integration import demo_data  # noqa: E402

STORE = Path(os.environ.get("DEMO_DATA_DIR", REPO / "data" / "demo_store"))
DATASETS, RUNS = STORE / "datasets", STORE / "runs"
BUILTIN = "demo_synthetic_desk"
Progress = Optional[Callable[[str, float], None]]
LAST_ERRORS: list[str] = []          # datasets of the last import that could not be run (shown in the UI)


def _say(progress: Progress, msg: str, frac: float):
    if progress:
        progress(msg, min(max(frac, 0.0), 1.0))


# ---------------------------------------------------------------- listing
def list_datasets() -> list[dict]:
    out = []
    for d in sorted(DATASETS.glob("*/frames")):
        name = d.parent.name
        meta_p = d.parent / "session_meta.json"
        meta = json.loads(meta_p.read_text(encoding="utf-8")) if meta_p.exists() else {}
        out.append({"name": name, "path": d.parent, "meta": meta, "builtin": name == BUILTIN,
                    "n_frames": sum(1 for p in d.iterdir() if p.is_dir()),
                    "run": RUNS / name if (RUNS / name / "run_summary.json").exists() else None})
    out.sort(key=lambda r: (r["builtin"], r["name"]))
    return out


def delete_dataset(name: str):
    for p in (DATASETS / name, RUNS / name):
        shutil.rmtree(p, ignore_errors=True)


# ---------------------------------------------------------------- run the pipeline
def s3_live_available() -> bool:
    try:
        import ultralytics  # noqa: F401
        return True
    except Exception:
        return False


def measure_camera_tf(dirs: list) -> dict:
    """S1's desk-plane TF (src/sensors/static_tf.py) from the first frames: camera height and pitch above the desk."""
    from src.preprocessing.frame_loader import load_frame
    from src.sensors.static_tf import estimate

    return estimate([load_frame(d) for d in dirs[:5]])


def run_dataset(name: str, parser: str = "auto", query: Optional[str] = None, progress: Progress = None,
                camera_tf: Optional[str] = None) -> Path:
    """S1 frames -> S3 -> S2 -> S6 -> S4 (every frame), then one S5 -> S6 question. Writes runs/<name>.

    ``camera_tf="auto"`` measures the camera pose from the desk plane (like ``main_pipeline.py --camera-tf
    auto``) and uses it for every frame instead of the bag TF / configured placeholder."""
    from src.integration.pipeline import Pipeline, frame_dirs

    ds = DATASETS / name
    dirs = frame_dirs(ds / "frames")
    have_obs = [d for d in dirs if (d / "observation.json").exists()]
    s3_mode = "replay" if len(have_obs) == len(dirs) or not s3_live_available() else "live"
    todo = dirs if s3_mode == "live" else have_obs
    if not todo:
        raise ValueError(f"{name}: no frame has S3 masks (observation.json) and YOLO-World is not installed "
                         "here. Add S3's output folder to the upload, or build the image with WITH_S3_LIVE=1.")
    out = RUNS / name
    shutil.rmtree(out, ignore_errors=True)
    pipe = Pipeline(out, s3_mode=s3_mode, parser=parser)
    errors, T, tf_info = [], None, None
    if camera_tf == "auto":
        _say(progress, f"{name}: S1 measuring the camera height and tilt from the desk plane", 0.03)
        try:
            est = measure_camera_tf(todo)
            T = est["T_map_camera"]
            tf_info = {k: est[k] for k in ("method", "camera_height_m", "pitch_below_horizontal_deg",
                                           "height_spread_m", "n_frames")}
            _say(progress, f"{name}: camera {est['camera_height_m']:.3f} m above the desk, "
                           f"{est['pitch_below_horizontal_deg']:.1f} deg below horizontal", 0.04)
        except Exception as e:      # no desk plane found: keep the bag / configured TF
            errors.append({"frame": "-", "stage": "camera_tf", "error": f"{type(e).__name__}: {e}"})
    for i, d in enumerate(todo):
        _say(progress, f"{name}: frame {i + 1}/{len(todo)} through S3 -> S2 -> S6 -> S4", 0.05 + 0.85 * i / len(todo))
        try:
            pipe.process(d, T_map_camera=T, force_tf=T is not None)
        except Exception as e:  # one bad frame must not kill the demo; S7 logs it
            errors.append({"frame": d.name, "stage": "pipeline", "error": f"{type(e).__name__}: {e}"})
    if not pipe.frames:
        raise ValueError(f"{name}: every frame failed: {errors[:3]}")
    _say(progress, f"{name}: S5 question + S6 ActionGoal", 0.93)
    result = pipe.ask(query or pipe.cfg["default_query"])
    summary = pipe.summary()
    summary.update({"dataset": name, "last_query": result, "frame_errors": errors,
                    "skipped_no_s3": [d.name for d in dirs if d not in todo], "camera_tf": tf_info,
                    "session_meta": json.loads((ds / "session_meta.json").read_text(encoding="utf-8"))
                    if (ds / "session_meta.json").exists() else {},
                    "created": time.strftime("%Y-%m-%d %H:%M:%S")})
    (out / "run_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    _say(progress, f"{name}: done ({len(pipe.frames)} frames)", 1.0)
    return out


# ---------------------------------------------------------------- import
def import_and_run(src: Path, parser: str = "auto", max_frames: int = 40, progress: Progress = None,
                   camera_tf: Optional[str] = None) -> list[str]:
    made = demo_data.import_source(src, DATASETS, max_frames=max_frames, workdir=STORE / "_unpack",
                                   progress=lambda m, f: _say(progress, m, 0.5 * f))
    names = []
    LAST_ERRORS.clear()
    for k, d in enumerate(made):
        sub = (lambda m, f, k=k: _say(progress, m, 0.5 + 0.5 * (k + f) / len(made))) if progress else None
        try:
            run_dataset(d.name, parser, progress=sub, camera_tf=camera_tf)
            names.append(d.name)
            s3 = json.loads((d / "session_meta.json").read_text(encoding="utf-8")).get("s3", {})
            if s3.get("by_order"):
                LAST_ERRORS.append(f"{d.name}: {s3['alignment']}")
        except Exception as e:      # one bag without S3 masks must not hide the other bags
            LAST_ERRORS.append(str(e))
            _say(progress, f"FAILED {d.name}: {e}", 0.5 + 0.5 * (k + 1) / len(made))
    if not names:
        raise ValueError("; ".join(LAST_ERRORS))
    return names


def bag_name(filenames: list[str]) -> str:
    """Recording name from the uploaded bag files: S1_static_bag_0.db3 -> S1_static_bag."""
    import re

    db = next((n for n in filenames if n.endswith((".db3", ".mcap"))), "recording")
    return demo_data.slug(re.sub(r"_\d+$", "", Path(db).stem))


def import_parts(name: str, bag_files: list, s3_zips: list = (), intrinsics=None, parser: str = "auto",
                 max_frames: int = 40, progress: Progress = None) -> list[str]:
    """Separately uploaded pieces -> one recording.

    ``bag_files``: (filename, file object) for S1's ``metadata.yaml`` + ``.db3`` / ``.mcap``;
    ``s3_zips``: (filename, file object) for S3's output zips; ``intrinsics``: optional
    (filename, file object) for camera_intrinsics.yaml. Files are streamed to disk, laid out as
    a bag folder + S3 runs, then imported like any other upload.
    """
    if not any(n.endswith((".db3", ".mcap")) for n, _ in bag_files):
        raise ValueError("S1: upload the bag's .db3 (or .mcap) file; metadata.yaml alone is not a recording")
    name = demo_data.slug(name)
    stage = STORE / "_parts" / name
    shutil.rmtree(stage, ignore_errors=True)
    (stage / name).mkdir(parents=True)

    def save(fobj, dst: Path):
        fobj.seek(0)
        with open(dst, "wb") as f:
            shutil.copyfileobj(fobj, f, 1 << 20)

    try:
        _say(progress, "saving S1 bag files", 0.01)
        has_meta = any(Path(n).name == "metadata.yaml" for n, _ in bag_files)
        for fname, fobj in bag_files:
            fname = Path(fname).name
            if not has_meta and fname.endswith(".db3"):
                fname = f"{name}.db3"          # a lone .db3 names the recording itself
            save(fobj, stage / name / fname)
        for fname, fobj in s3_zips:
            _say(progress, f"unpacking S3 output {fname}", 0.03)
            z = stage / "_zips" / Path(fname).name
            z.parent.mkdir(exist_ok=True)
            save(fobj, z)
            demo_data.safe_extract(z, stage / "s3_semantic" / demo_data.slug(Path(fname).stem))
            z.unlink()
        if intrinsics is not None:
            save(intrinsics[1], stage / "camera_intrinsics.yaml")
        return import_and_run(stage, parser, max_frames, progress)
    finally:
        shutil.rmtree(stage, ignore_errors=True)


def build_builtin(progress: Progress = None) -> str:
    """Synthetic desk recorded as a real ZED-format ROS 2 bag + S3 masks, imported like team data."""
    import numpy as np

    from scripts.make_demo_sequence import generate
    from src.preprocessing.frame_loader import load_frame
    from src.sensors import bag_replay

    work = STORE / "_builtin"
    shutil.rmtree(work, ignore_errors=True)
    _say(progress, "rendering the synthetic desk sequence", 0.05)
    dirs = generate(work / "render", n_frames=8)
    frames = [load_frame(d) for d in dirs]
    O = np.eye(4)
    O[:3, :3] = bag_replay.R_LINK_OPTICAL          # S1's static TF map -> camera_link (body frame)
    bag_replay.write_bag(frames, work / "pkg" / BUILTIN, camera_info=True,
                         T_map_link=frames[0].T_map_camera @ np.linalg.inv(O))
    for i, (d, fr) in enumerate(zip(dirs, frames)):        # S3 output layout of src/open_vocab/run.py
        f = work / "pkg" / "s3_semantic" / BUILTIN / f"frame_{i:06d}"
        shutil.copytree(d / "masks", f / "masks")
        obs = json.loads((d / "observation.json").read_text(encoding="utf-8"))
        obs["timestamp"] = fr.timestamp
        (f / "observation.json").write_text(json.dumps(obs), encoding="utf-8")
    names = import_and_run(work / "pkg", parser="rules", progress=progress)
    shutil.rmtree(work, ignore_errors=True)
    return names[0]


def ensure_builtin(progress: Progress = None) -> str:
    if not (RUNS / BUILTIN / "run_summary.json").exists():
        build_builtin(progress)
    return BUILTIN


# ---------------------------------------------------------------- remote data
def fetch(url: str, dest_dir: Path, progress: Progress = None) -> Path:
    """Download a zip / .db3 from a direct link or a Google Drive share link."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    if "drive.google.com" in url or "docs.google.com" in url:
        import gdown

        _say(progress, "downloading from Google Drive", 0.01)
        if "/folders/" in url:
            out = dest_dir / f"drive_{abs(hash(url)) % 10 ** 8}"
            gdown.download_folder(url, output=str(out), quiet=True)
            return out
        path = gdown.download(url, output=str(dest_dir) + "/", quiet=True, fuzzy=True)
        if not path:
            raise ValueError("Google Drive refused the download: share the file as 'Anyone with the link'")
        return Path(path)
    name = Path(url.split("?")[0]).name or "download.zip"
    out = dest_dir / name
    req = urllib.request.Request(url, headers={"User-Agent": "g1-demo"})
    with urllib.request.urlopen(req, timeout=60) as r, open(out, "wb") as f:
        total, done = int(r.headers.get("Content-Length") or 0), 0
        while chunk := r.read(1 << 20):
            f.write(chunk)
            done += len(chunk)
            _say(progress, f"downloading {name}: {done >> 20} MB", 0.4 * done / total if total else 0.1)
    return out


def import_url(url: str, parser: str = "auto", max_frames: int = 40, progress: Progress = None) -> list[str]:
    tmp = STORE / "_download"
    try:
        path = fetch(url, tmp, progress)
        return import_and_run(path, parser, max_frames, progress)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def bootstrap_from_env(progress: Progress = None) -> list[str]:
    """DEMO_DATA_URLS (comma separated) are imported once per store; a marker file remembers them."""
    urls = [u.strip() for u in os.environ.get("DEMO_DATA_URLS", "").split(",") if u.strip()]
    marker = STORE / "imported_urls.json"
    done = json.loads(marker.read_text(encoding="utf-8")) if marker.exists() else []
    names = []
    for u in urls:
        if u in done:
            continue
        names += import_url(u, progress=progress)
        done.append(u)
        STORE.mkdir(parents=True, exist_ok=True)
        marker.write_text(json.dumps(done, indent=2), encoding="utf-8")
    return names


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--builtin", action="store_true", help="(re)build the synthetic demo dataset")
    ap.add_argument("--import", dest="src", help=".zip, bag folder, .db3 or frame folders")
    ap.add_argument("--url", help="direct or Google Drive link to a .zip / .db3")
    ap.add_argument("--rerun", help="re-run the pipeline on an imported dataset")
    ap.add_argument("--camera-tf", choices=["auto"], default=None,
                    help="auto: measure the camera pose from the desk plane instead of the bag TF / placeholder")
    ap.add_argument("--max-frames", type=int, default=40)
    ap.add_argument("--parser", choices=["auto", "rules", "ollama"], default="auto")
    a = ap.parse_args()
    log = lambda m, f: print(f"[{f:4.0%}] {m}", flush=True)
    if a.builtin:
        print("built-in:", build_builtin(log))
    if a.src:
        print("imported:", import_and_run(Path(a.src), a.parser, a.max_frames, log, camera_tf=a.camera_tf))
    if a.url:
        print("imported:", import_url(a.url, a.parser, a.max_frames, log))
    if a.rerun:
        print("run:", run_dataset(a.rerun, a.parser, progress=log, camera_tf=a.camera_tf))
    if not (a.builtin or a.src or a.url or a.rerun):
        for d in list_datasets():
            print(f"{d['name']:30s} {d['n_frames']:4d} frames  run={'yes' if d['run'] else 'no'}")


if __name__ == "__main__":
    main()
