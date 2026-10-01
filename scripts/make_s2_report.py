"""Generate S2 progress figures (screenshots) into docs/s2/screenshots/.

    python scripts/make_s2_report.py

Uses the mock S1/S3 frame (data/mock/frame_000), runs the real S2 pipeline,
and renders every intermediate step.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.fusion_3d import geometry as geo  # noqa: E402
from src.fusion_3d.pipeline import load_config, process_frame  # noqa: E402
from src.fusion_3d.run_pipeline import run  # noqa: E402
from src.fusion_3d.transforms import apply_transform  # noqa: E402
from src.fusion_3d.visualize import PALETTE, overlay_masks, render_scene_3d  # noqa: E402
from src.preprocessing.depth_cleaning import clean_depth, depth_to_meters  # noqa: E402
from src.preprocessing.mock_data import generate  # noqa: E402

FRAME = ROOT / "data" / "mock" / "frame_000"
OUT = ROOT / "docs" / "s2" / "screenshots"
INK, INK2, MUTED, GRID, SURFACE = "#0b0b0b", "#52514e", "#8a8984", "#e6e5e0", "#fcfcfb"

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "axes.edgecolor": GRID, "axes.labelcolor": INK2, "xtick.color": MUTED, "ytick.color": MUTED,
    "text.color": INK, "font.size": 10, "axes.titleweight": "bold", "axes.titlesize": 11,
    "axes.titlelocation": "left", "axes.spines.top": False, "axes.spines.right": False,
})


def save(fig, name):
    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / name, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    print("wrote", (OUT / name).relative_to(ROOT))


def terminal(lines, name, title, width=11.5):
    """Render real command output as a terminal-style screenshot."""
    lines = lines[:60]
    h = 0.6 + 0.19 * len(lines)
    fig = plt.figure(figsize=(width, h))
    fig.patch.set_facecolor("#1e1e1e")
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_facecolor("#1e1e1e")
    ax.axis("off")
    for i, c in enumerate(("#ff5f56", "#ffbd2e", "#27c93f")):
        ax.add_patch(plt.Circle((0.015 + i * 0.018, 1 - 0.18 / h), 0.006, color=c, transform=ax.transAxes))
    ax.text(0.5, 1 - 0.18 / h, title, color="#9a9a9a", ha="center", va="center",
            fontsize=9, family="monospace", transform=ax.transAxes)
    for i, line in enumerate(lines):
        col = "#d4d4d4"
        if line.startswith("$"):
            col = "#7fd88f"
        elif "PASSED" in line or " passed" in line:
            col = "#7fd88f"
        elif "FAILED" in line or "REJECTED" in line:
            col = "#ff6b6b"
        ax.text(0.012, 1 - (0.42 + 0.19 * i) / h, line, color=col, fontsize=8.6,
                family="monospace", va="top", transform=ax.transAxes)
    save(fig, name)


def main():
    if not (FRAME / "rgb.png").exists():
        generate(FRAME)
    frame, obs, result, payload, json_path = run(FRAME, ROOT / "outputs" / "fusion_3d")
    cfg = load_config()
    intr = frame.intrinsics
    depth = clean_depth(depth_to_meters(frame.depth_raw, intr.depth_scale), cfg["depth"]["min_m"], cfg["depth"]["max_m"])

    # 01 — inputs from S1 and S3 -----------------------------------------
    fig, axs = plt.subplots(1, 3, figsize=(15, 3.9))
    axs[0].imshow(frame.rgb)
    axs[0].set_title("S1 → RGB (aligned)")
    cmap = plt.get_cmap("Blues_r").copy()
    cmap.set_bad("#1a1a19")
    im = axs[1].imshow(np.where(depth > 0, depth, np.nan), cmap=cmap, vmin=0.5, vmax=1.4)
    axs[1].set_title("S1 → Depth (m), black = no depth")
    cb = fig.colorbar(im, ax=axs[1], fraction=0.035)
    cb.outline.set_visible(False)
    axs[2].imshow(overlay_masks(frame.rgb, obs))
    for i, o in enumerate(obs):
        x1, y1, x2, y2 = o.bbox
        axs[2].add_patch(plt.Rectangle((x1, y1), x2 - x1, y2 - y1, fill=False, ec=PALETTE[i], lw=1.5))
        axs[2].text(x1, y1 - 4, f"{o.label} {o.score:.2f}", fontsize=8, color="white",
                    bbox=dict(fc=PALETTE[i], ec="none", pad=1.5))
    axs[2].set_title("S3 → SemanticObservation (bbox + SAM mask)")
    for a in axs:
        a.set_xticks([]); a.set_yticks([])
        for s in a.spines.values():
            s.set_visible(False)
    save(fig, "01_inputs_S1_S3.png")

    # 02 — mask -> depth filter -> point cloud -> cleaning (mug) ----------
    oid = "mug_0"
    o_obs = next(o for o in obs if o.label == "mug")
    x1, y1, x2, y2 = [int(v) for v in o_obs.bbox]
    pad = 25
    sl = (slice(max(0, y1 - pad), y2 + pad), slice(max(0, x1 - pad), x2 + pad))
    fig = plt.figure(figsize=(15, 4))
    ax = fig.add_subplot(1, 4, 1)
    ax.imshow(overlay_masks(frame.rgb, [o_obs])[sl])
    ax.set_title("1. S3 mask (mug)")
    ax.axis("off")
    ax = fig.add_subplot(1, 4, 2)
    md = np.where(o_obs.mask & (depth > 0), depth, np.nan)
    ax.imshow(md[sl], cmap="Blues_r")
    ax.set_title("2. Depth inside mask only")
    ax.axis("off")
    raw = result.raw_points[oid]
    clean = result.object_points[oid]
    T = result.T_map_camera
    for k, (P, ttl, col) in enumerate(((raw, f"3. Deprojected: {len(raw)} pts", MUTED),
                                       (clean, f"4. Cleaned: {len(clean)} pts", PALETTE[0]))):
        ax = fig.add_subplot(1, 4, 3 + k, projection="3d")
        Pm = apply_transform(T, P)
        ax.scatter(*Pm.T, s=1.0, color=col, linewidths=0)
        if k == 1:
            obj = next(o for o in result.objects if o.object_id == oid)
            cs = geo.gravity_box_corners(obj.box_map)
            for a, b in [(0, 1), (1, 2), (2, 3), (3, 0), (4, 5), (5, 6), (6, 7), (7, 4), (0, 4), (1, 5), (2, 6), (3, 7)]:
                ax.plot(*cs[[a, b]].T, color=PALETTE[1], lw=1.4)
            c = obj.centroid_map
            ax.scatter([c[0]], [c[1]], [c[2]], color=INK, marker="x", s=40)
        ref = apply_transform(T, raw)
        ax.set_xlim(ref[:, 0].min(), ref[:, 0].max())
        ax.set_ylim(ref[:, 1].min(), ref[:, 1].max())
        ax.set_zlim(ref[:, 2].min(), ref[:, 2].max())
        ax.view_init(elev=22, azim=-160)
        ax.set_title(ttl, loc="left")
        ax.tick_params(labelsize=7)
    fig.text(0.51, 0.02, "plane removal (desk RANSAC) → voxel 3 mm → remove_statistical_outlier → largest DBSCAN cluster",
             ha="center", color=INK2, fontsize=9)
    save(fig, "02_mask_to_pointcloud_mug.png")

    # 03 — whole scene 3D with boxes ---------------------------------------
    fig = plt.figure(figsize=(12, 7.5))
    ax = fig.add_axes([0, 0, 1, 0.95], projection="3d")
    render_scene_3d(ax, frame, depth, result, stride=2)
    ax.set_title("ObjectInstance3D — 3D boxes in map frame (label + depth_confidence)", loc="left")
    save(fig, "03_scene_3d_bounding_boxes.png")

    # 04 — JSON output -------------------------------------------------------
    mug = next(o for o in payload["objects"] if o["object_id"] == "mug_0")
    keys = ["semantic_label", "centroid", "box_dimensions", "depth_confidence", "object_id",
            "persistent_id", "label_candidates", "detector_score", "centroid_map", "box_map",
            "num_points", "modality_quality", "fusion_mode", "fusion_weights", "fused_confidence",
            "points_ref", "frame_id", "timestamp"]

    def rnd(v):
        if isinstance(v, float):
            return round(v, 4)
        if isinstance(v, list):
            return [rnd(x) for x in v]
        if isinstance(v, dict):
            return {k: rnd(x) for k, x in v.items()}
        return v
    import re

    js = json.dumps({k: rnd(mug[k]) for k in keys}, indent=2)
    # keep short lists of numbers/strings on one line
    js = re.sub(r"\[\s*([^\[\]{}]*?)\s*\]", lambda m: "[" + re.sub(r"\s*\n\s*", " ", m.group(1)) + "]", js)
    js = js.splitlines()
    terminal(["$ cat outputs/fusion_3d/frame_000_objects.json | jq '.objects[1]'"] + js,
             "04_objectinstance3d_json.png", "ObjectInstance3D → S4 / S6", width=9)

    # 05 — CLI run -------------------------------------------------------------
    cmd = [sys.executable, "-m", "src.fusion_3d.run_pipeline", "--frame", "data/mock/frame_000"]
    out = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True).stdout.splitlines()
    terminal(["$ python -m src.fusion_3d.run_pipeline --frame data/mock/frame_000"] + out,
             "05_pipeline_run_terminal.png", "S2 pipeline run", width=13)

    # 06 — tests -----------------------------------------------------------------
    t = subprocess.run([sys.executable, "-m", "pytest", "-v", "-p", "no:cacheprovider", "tests/"],
                       cwd=ROOT, capture_output=True, text=True).stdout.splitlines()
    t = [line.replace(str(ROOT), ".") for line in t if line.strip() and not line.startswith(("platform", "cachedir", "rootdir", "configfile", "plugins"))]
    terminal(["$ pytest -v tests/"] + t, "06_unit_tests_passed.png", "pytest", width=12)

    # 07 — metrics: localisation error + depth confidence / weights ---------------
    ev = payload["evaluation"]["per_object"]
    labels = [r["label"] for r in ev]
    by = {o.semantic_label: o for o in result.objects}
    fixed = process_frame(frame, obs, cfg, fusion_mode="fixed")
    byf = {o.semantic_label: o for o in fixed.objects}
    fig, axs = plt.subplots(1, 3, figsize=(15, 3.8))
    y = np.arange(len(labels))
    ax = axs[0]
    ax.barh(y + 0.2, [r["box_center_error_m"] * 100 for r in ev], 0.36, color=PALETTE[0], label="box centre")
    ax.barh(y - 0.2, [r["centroid_error_m"] * 100 for r in ev], 0.36, color=PALETTE[1], label="visible-surface centroid")
    ax.set_yticks(y, labels)
    ax.invert_yaxis()
    ax.set_xlabel("error vs ground truth (cm)")
    ax.set_title("Localisation error")
    ax.legend(frameon=False, fontsize=8, loc="upper left", bbox_to_anchor=(0, -0.2), ncol=2)
    ax.grid(axis="x", color=GRID)
    ax.set_axisbelow(True)
    ax = axs[1]
    vals = [by[l].depth_confidence for l in labels]
    ax.barh(y, vals, 0.5, color=PALETTE[0])
    for yi, v in zip(y, vals):
        ax.text(v + 0.02, yi, f"{v:.2f}", va="center", color=INK2, fontsize=9)
    ax.set_yticks(y, labels)
    ax.invert_yaxis()
    ax.set_xlim(0, 1.15)
    ax.set_xlabel("valid depth pixels / mask pixels")
    ax.set_title("depth_confidence (glass is transparent)")
    ax.grid(axis="x", color=GRID)
    ax.set_axisbelow(True)
    ax = axs[2]
    ax.barh(y + 0.2, [byf[l].fusion_weights["depth"] for l in labels], 0.36, color=MUTED, label="fixed (baseline)")
    ax.barh(y - 0.2, [by[l].fusion_weights["depth"] for l in labels], 0.36, color=PALETTE[2], label="adaptive")
    ax.set_yticks(y, labels)
    ax.invert_yaxis()
    ax.set_xlabel("w_depth")
    ax.set_title("Depth fusion weight: fixed vs adaptive")
    ax.legend(frameon=False, fontsize=8, loc="upper left", bbox_to_anchor=(0, -0.2), ncol=2)
    ax.grid(axis="x", color=GRID)
    ax.set_axisbelow(True)
    fig.tight_layout()
    save(fig, "07_metrics.png")

    summary = {
        "recall": payload["evaluation"]["recall"],
        "mean_box_center_error_m": payload["evaluation"]["mean_box_center_error_m"],
        "mean_centroid_error_m": payload["evaluation"]["mean_centroid_error_m"],
        "timings_ms": payload["timings_ms"],
        "n_objects": len(result.objects),
    }
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary))


if __name__ == "__main__":
    main()
