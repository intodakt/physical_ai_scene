"""Week 6–7 evidence for S2: figures + metrics → docs/s2/week6_7/.

    python scripts/make_s2_week6_7_report.py

Everything is computed by running the real pipeline on mock frames
(RealSense profile and ZED Mini profile; glass that fails with holes or by
seeing through to the desk). W5 = Week-5 configuration (no flying-pixel
filter, no reliability check); W7 = current configuration.
"""

from __future__ import annotations

import copy
import json
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.patches import Circle  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.fusion_3d import geometry as geo  # noqa: E402
from src.fusion_3d.depth_reliability import plane_leak_map  # noqa: E402
from src.fusion_3d.evaluate import evaluate_against_ground_truth  # noqa: E402
from src.fusion_3d.mask_plane import _rays, fit_circle_ransac  # noqa: E402
from src.fusion_3d.pipeline import load_config, process_frame, sensor_depth  # noqa: E402
from src.fusion_3d.projection import deproject_depth  # noqa: E402
from src.fusion_3d.run_sequence import run_sequence  # noqa: E402
from src.fusion_3d.transforms import apply_transform  # noqa: E402
from src.preprocessing.frame_loader import load_frame, load_semantic_observations  # noqa: E402
from src.preprocessing.mask_utils import erode  # noqa: E402
from src.preprocessing.mock_data import generate, generate_sequence  # noqa: E402

OUT = ROOT / "docs" / "s2" / "week6_7"
INK, INK2, MUTED, GRID, SURF = "#1d1f22", "#52514e", "#8a8984", "#e6e5e0", "#ffffff"
BLUE, ORANGE, AQUA, RED, GREEN = "#2a78d6", "#eb6834", "#1baf7a", "#e34948", "#008300"
plt.rcParams.update({"font.size": 10, "axes.edgecolor": GRID, "axes.labelcolor": INK2, "xtick.color": MUTED,
                     "ytick.color": MUTED, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.titleweight": "bold", "axes.titlelocation": "left", "figure.facecolor": SURF})

CASES = [  # key, title, generate kwargs
    ("holes85", "RealSense · glass with holes (85 % missing)", dict(profile="realsense", glass_mode="holes")),
    ("see85", "ZED Mini · see-through (85 % sees the desk)", dict(profile="zed_mini", glass_mode="see_through")),
    ("see100", "ZED Mini · fully transparent (100 % sees the desk)", dict(profile="zed_mini", glass_mode="see_through", glass_failure=1.0)),
    ("holes100", "ZED Mini · no depth at all on the glass", dict(profile="zed_mini", glass_mode="holes", glass_failure=1.0)),
]


def w5_config():
    c = load_config()
    c["depth"]["flying_pixel_filter"]["enabled"] = False
    c["depth_reliability"]["enabled"] = False
    return c


def save(fig, name):
    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / name, dpi=160, bbox_inches="tight")
    plt.close(fig)
    print("wrote", (OUT / name).relative_to(ROOT))


def run_case(d, cfg):
    fr = load_frame(d)
    obs = load_semantic_observations(d / "observation.json")
    res = process_frame(fr, obs, cfg)
    gt = json.loads((d / "ground_truth.json").read_text())
    ev = evaluate_against_ground_truth(res.objects, gt)
    g = next((o for o in res.objects if o.semantic_label == "glass"), None)
    row = next((r for r in ev["per_object"] if r["label"] == "glass"), None)
    return fr, obs, res, ev, g, row


def main():
    tmp = Path(tempfile.mkdtemp(prefix="s2w67_"))
    metrics = {"cases": {}, "generated": time.strftime("%Y-%m-%d")}

    # ------------------------------------------------ Week 7: glass cases, W5 vs W7
    rows = []
    for key, title, kw in CASES:
        d = generate(tmp / key, seed=3, **kw)
        _, _, _, ev5, g5, r5 = run_case(d, w5_config())
        fr, obs, res, ev7, g7, r7 = run_case(d, load_config())
        m = {"title": title,
             "w5": {"glass_error_cm": None if r5 is None else round(r5["box_center_error_m"] * 100, 2),
                    "glass_dims_whd_cm": None if g5 is None else [round(x * 100, 1) for x in g5.box_dimensions],
                    "mean_error_cm": round(ev5["mean_box_center_error_m"] * 100, 2), "objects": len(ev5["per_object"])},
             "w7": {"glass_error_cm": round(r7["box_center_error_m"] * 100, 2),
                    "glass_dims_whd_cm": [round(x * 100, 1) for x in g7.box_dimensions],
                    "mean_error_cm": round(ev7["mean_box_center_error_m"] * 100, 2), "objects": len(ev7["per_object"]),
                    "status": g7.depth_status, "geometry_source": g7.geometry_source,
                    "reliability": g7.depth_reliability, "w_depth": g7.fusion_weights["depth"],
                    "true_dims_whd_cm": [round(x * 100, 1) for x in r7["true_dims_whd"]]}}
        metrics["cases"][key] = m
        rows.append((key, title, d, fr, obs, res, g7))
        print(key, m["w5"]["glass_error_cm"], "->", m["w7"]["glass_error_cm"], g7.depth_status, g7.geometry_source)

    # ------------------------------------------------ Figure 1: how the glass is detected
    cfg = load_config()
    fig, axs = plt.subplots(3, 4, figsize=(14, 9.6), gridspec_kw={"width_ratios": [1, 1, 1, 1.25]})
    for r, (key, title, d, fr, obs, res, g) in enumerate([x for x in rows if x[0] in ("holes85", "see85", "see100")]):
        gob = next(o for o in obs if o.label == "glass")
        x1, y1, x2, y2 = [int(v) for v in gob.bbox]
        pad = int(0.35 * (x2 - x1))
        sl = (slice(max(0, y1 - pad), y2 + pad), slice(max(0, x1 - pad), x2 + pad))
        raw = sensor_depth(fr, cfg)
        pts, _ = deproject_depth(raw, fr.intrinsics, 4)
        plane = geo.fit_support_plane(pts, 0.006)
        interior = erode(gob.mask, 3)
        lm = plane_leak_map(raw, interior, fr.intrinsics, plane, 0.012)
        ax = axs[r, 0]; ax.imshow(fr.rgb[sl]); ax.contour(gob.mask[sl], levels=[0.5], colors=[BLUE], linewidths=1.2)
        ax.set_title("RGB + S3 mask" if r == 0 else "", fontsize=10); ax.set_ylabel(title.split("·")[1].strip(), fontsize=9.5, color=INK)
        ax2 = axs[r, 1]
        cmap = plt.get_cmap("Blues_r").copy(); cmap.set_bad("#111111")
        dd = np.where(raw > 0, raw, np.nan)[sl]
        ax2.imshow(dd, cmap=cmap, vmin=np.nanpercentile(dd, 2), vmax=np.nanpercentile(dd, 98))
        ax2.set_title("depth (black = none)" if r == 0 else "", fontsize=10)
        rgbmap = np.zeros(lm.shape + (3,)); rgbmap[:] = (0.93, 0.93, 0.92)
        inside = interior & (lm == 0); rgbmap[inside] = (0.15, 0.15, 0.15)
        rgbmap[lm == 1] = matplotlib.colors.to_rgb(GREEN); rgbmap[lm == 2] = matplotlib.colors.to_rgb(RED)
        ax3 = axs[r, 2]; ax3.imshow(rgbmap[sl]); ax3.set_title("cue map inside the mask" if r == 0 else "", fontsize=10)
        for a in (ax, ax2, ax3):
            a.set_xticks([]); a.set_yticks([])
        rel = g.depth_reliability
        txt = (f"interior pixels with depth   {rel['interior_valid_ratio']*100:5.1f} %\n"
               f"of those ON the desk (leak)  {rel['plane_leak_ratio']*100:5.1f} %\n"
               f"genuine glass depth          {rel['genuine_ratio']*100:5.1f} %\n\n"
               f"status    {g.depth_status}\n"
               f"geometry  {g.geometry_source}\n"
               f"error     {metrics['cases'][key]['w7']['glass_error_cm']:.1f} cm  (W5: "
               f"{metrics['cases'][key]['w5']['glass_error_cm'] if metrics['cases'][key]['w5']['glass_error_cm'] is not None else '—'} cm)")
        axs[r, 3].axis("off")
        axs[r, 3].text(0.0, 0.5, txt, family="monospace", fontsize=9.6, va="center", color=INK)
    fig.legend(handles=[matplotlib.patches.Patch(color=GREEN, label="depth on the glass (above desk)"),
                        matplotlib.patches.Patch(color=RED, label="depth on the desk behind the glass (see-through)"),
                        matplotlib.patches.Patch(color="#262626", label="no depth (hole)")],
               loc="lower center", ncol=3, frameon=False, bbox_to_anchor=(0.45, -0.01))
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    save(fig, "fig1_glass_cues.png")

    # ------------------------------------------------ Figure 2: mask + desk plane fallback
    key, title, d, fr, obs, res, g = next(x for x in rows if x[0] == "see100")
    gob = next(o for o in obs if o.label == "glass")
    raw = sensor_depth(fr, cfg)
    pts, _ = deproject_depth(raw, fr.intrinsics, 4)
    plane = geo.fit_support_plane(pts, 0.006)
    m = gob.mask
    cols = np.flatnonzero(m.any(0)); H = m.shape[0]
    bottom = H - 1 - np.argmax(m[::-1, cols], 0) - 2
    ray = _rays(cols.astype(float), bottom.astype(float), fr.intrinsics)
    t = -plane[3] / (ray @ plane[:3])
    contact = apply_transform(fr.T_map_camera, ray * t[:, None])
    ctr, rad, inl = fit_circle_ransac(contact[:, :2])
    gt = next(o for o in json.loads((d / "ground_truth.json").read_text())["objects"] if o["name"] == "glass")
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(12, 4.6), gridspec_kw={"width_ratios": [1, 1.25]})
    x1, y1, x2, y2 = [int(v) for v in gob.bbox]; pad = 25
    a1.imshow(fr.rgb[y1 - pad:y2 + pad, x1 - pad:x2 + pad])
    a1.contour(m[y1 - pad:y2 + pad, x1 - pad:x2 + pad], levels=[0.5], colors=[BLUE], linewidths=1)
    a1.scatter(cols[inl] - x1 + pad, bottom[inl] - y1 + pad, s=9, color=GREEN, label="contact pixels (inliers)")
    a1.scatter(cols[~inl] - x1 + pad, bottom[~inl] - y1 + pad, s=9, color=RED, label="rim-only columns (rejected)")
    a1.legend(loc="upper center", bbox_to_anchor=(0.5, -0.02), fontsize=8.5, frameon=False, ncol=1)
    a1.set_xticks([]); a1.set_yticks([]); a1.set_title("1. lowest mask pixel of every column")
    to = lambda xy: np.c_[-xy[:, 1], xy[:, 0]] * 100  # map → (right, forward) in cm
    p = to(contact[:, :2])
    a2.scatter(p[inl, 0], p[inl, 1], s=12, color=GREEN, label="ray ∩ desk plane (inliers)")
    a2.scatter(p[~inl, 0], p[~inl, 1], s=12, color=RED, label="rim-only columns (outliers)")
    c_est, c_gt = to(ctr[None])[0], to(np.array(gt["center"][:2])[None])[0]
    a2.add_patch(Circle(c_est, rad * 100, fill=False, ec=BLUE, lw=2, label=f"RANSAC circle  Ø {2*rad*100:.1f} cm"))
    a2.add_patch(Circle(c_gt, gt["dimensions_xyz"][0] * 50, fill=False, ec=MUTED, lw=1.5, ls="--", label=f"true glass  Ø {gt['dimensions_xyz'][0]*100:.0f} cm"))
    a2.scatter(*c_est, marker="+", s=120, color=BLUE); a2.scatter(*c_gt, marker="x", s=60, color=MUTED)
    a2.set_aspect("equal"); a2.set_xlabel("← left · right → [cm]"); a2.set_ylabel("forward from camera [cm]")
    a2.legend(fontsize=8.5, frameon=False, loc="upper left", bbox_to_anchor=(1.0, 1.0))
    a2.set_title(f"2. circle fit on the desk → centre error {metrics['cases']['see100']['w7']['glass_error_cm']:.1f} cm")
    a2.grid(color=GRID, lw=0.6); a2.set_axisbelow(True)
    fig.tight_layout()
    save(fig, "fig2_mask_plane_fallback.png")

    # ------------------------------------------------ Figure 3: W5 vs W7 glass error
    fig, ax = plt.subplots(figsize=(9.5, 3.6))
    keys = [k for k, *_ in CASES]
    y = np.arange(len(keys))
    w5 = [metrics["cases"][k]["w5"]["glass_error_cm"] for k in keys]
    w7 = [metrics["cases"][k]["w7"]["glass_error_cm"] for k in keys]
    w5p = [v if v is not None else 0 for v in w5]
    ax.barh(y - 0.19, w5p, 0.36, color="#b9b8b2", label="Week 5 pipeline")
    ax.barh(y + 0.19, w7, 0.36, color=BLUE, label="Week 7 pipeline")
    for yi, a, b in zip(y, w5, w7):
        ax.text((a or 0) + 0.15, yi - 0.19, "rejected" if a is None else f"{a:.1f} cm", va="center", fontsize=9, color=INK2)
        ax.text(b + 0.15, yi + 0.19, f"{b:.1f} cm", va="center", fontsize=9, color=INK)
    ax.set_yticks(y, [metrics["cases"][k]["title"] for k in keys]); ax.invert_yaxis()
    ax.set_xlabel("glass 3D box-centre error vs ground truth (cm)")
    ax.set_title("Glass localisation: Week 5 vs Week 7")
    ax.legend(frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.22), ncol=2); ax.grid(axis="x", color=GRID); ax.set_axisbelow(True)
    save(fig, "fig3_glass_w5_vs_w7.png")

    # ------------------------------------------------ Week 6: bag round trip + static sequence
    seq = tmp / "zed_static"
    generate_sequence(seq, n_frames=5, profile="zed_mini", glass_mode="see_through", glass_failure=1.0)
    bag_info = {}
    try:
        from src.preprocessing.bag_reader import export_frames, write_bag
        frames = [load_frame(p) for p in sorted(seq.iterdir())]
        t0 = time.perf_counter()
        bag = write_bag(frames, tmp / "bag_zed", profile="zed_mini")
        paths, st = export_frames(bag, tmp / "from_bag", "zed_mini")
        same = all(np.array_equal(load_frame(p).rgb, f.rgb) for p, f in zip(paths, frames))
        bag_info = {"frames_written": len(frames), "synced": st.synced, "dropped": st.dropped,
                    "rgb_identical": same, "seconds": round(time.perf_counter() - t0, 2),
                    "topics": ["/zed/zed_node/rgb/image_rect_color", "/zed/zed_node/depth/depth_registered",
                               "/zed/zed_node/rgb/camera_info"]}
    except ImportError:
        bag_info = {"skipped": "rosbags not installed"}
    metrics["bag_round_trip"] = bag_info
    rep7 = run_sequence(seq, None, load_config(), temporal_median=True)
    rep5 = run_sequence(seq, None, w5_config(), temporal_median=False)
    metrics["static_sequence"] = {"w7": rep7, "w5": rep5}

    fig, ax = plt.subplots(figsize=(9.5, 3.2))
    labs = sorted(rep7["stability"])
    y = np.arange(len(labs))
    j7 = [rep7["stability"][l]["jitter_rms_mm"] for l in labs]
    ax.barh(y, j7, 0.5, color=AQUA)
    for yi, v, l in zip(y, j7, labs):
        st_ = rep7["stability"][l]
        ax.text(v + 0.05, yi, f"{v:.2f} mm · detected {st_['detection_rate']*100:.0f} % · {st_['depth_status']}",
                va="center", fontsize=9, color=INK2)
    ax.set_yticks(y, labs); ax.invert_yaxis(); ax.set_xlim(0, max(j7) * 3.2)
    ax.set_xlabel("RMS jitter of the 3D box centre over 5 static ZED frames (mm)")
    ax.set_title("Static baseline stability (Week 6)")
    ax.grid(axis="x", color=GRID); ax.set_axisbelow(True)
    save(fig, "fig4_static_stability.png")

    # ------------------------------------------------ tests terminal
    out = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "tests/"], cwd=ROOT,
                         capture_output=True, text=True).stdout.strip().splitlines()
    metrics["tests"] = out[-1] if out else ""
    lines = ["$ pytest tests/test_s2_week6_7.py -v"] + [
        l.replace(str(ROOT), ".") for l in subprocess.run(
            [sys.executable, "-m", "pytest", "-v", "-p", "no:cacheprovider", "tests/test_s2_week6_7.py"], cwd=ROOT,
            capture_output=True, text=True).stdout.splitlines()
        if "PASSED" in l or "FAILED" in l or "passed" in l]
    lines = [re.sub(r"\s+\[\s*\d+%\]", "", l) for l in lines]
    fig = plt.figure(figsize=(11, 0.5 + 0.2 * len(lines))); fig.patch.set_facecolor("#1e1e1e")
    a = fig.add_axes([0, 0, 1, 1]); a.axis("off"); a.set_facecolor("#1e1e1e")
    for i, l in enumerate(lines):
        a.text(0.012, 1 - (0.3 + 0.2 * i) / (0.5 + 0.2 * len(lines)), l, family="monospace", fontsize=8.4,
               color="#7fd88f" if ("PASSED" in l or "passed" in l or l.startswith("$")) else "#d4d4d4", va="top",
               transform=a.transAxes)
    fig.savefig(OUT / "fig5_tests.png", dpi=160, facecolor="#1e1e1e"); plt.close(fig)
    print("wrote docs/s2/week6_7/fig5_tests.png")

    (OUT / "metrics.json").write_text(json.dumps(metrics, indent=2, default=float))
    print(json.dumps({k: (v["w5"]["glass_error_cm"], v["w7"]["glass_error_cm"]) for k, v in metrics["cases"].items()}),
          metrics["tests"], bag_info)


if __name__ == "__main__":
    main()
