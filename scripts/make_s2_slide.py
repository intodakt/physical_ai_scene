"""Render the S2 presentation slide (16:9, 1920x1080) -> docs/s2/slide_06_S2.png.

Run scripts/make_s2_report.py first (it produces the screenshots + summary.json).
"""

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.image as mpimg  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyBboxPatch  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SHOTS = ROOT / "docs" / "s2" / "screenshots"
INK, INK2, MUTED, LINE, SURFACE = "#0b0b0b", "#52514e", "#8a8984", "#e6e5e0", "#fcfcfb"
ACCENT, ACCENT2, ACCENT3 = "#2a78d6", "#eb6834", "#1baf7a"


def card(fig, x, y, w, h, fc="white", ec=LINE):
    fig.patches.append(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=0.012",
                                      transform=fig.transFigure, fc=fc, ec=ec, lw=1.2, zorder=0))


def main():
    s = json.loads((SHOTS / "summary.json").read_text())
    objs = json.loads((ROOT / "outputs" / "fusion_3d" / "frame_000_objects.json").read_text())["objects"]
    glass = next(o for o in objs if o["semantic_label"] == "glass")
    fig = plt.figure(figsize=(16, 9), dpi=120)
    fig.patch.set_facecolor(SURFACE)

    # Header
    fig.text(0.04, 0.925, "06", color=ACCENT, fontsize=30, weight="bold", va="center")
    fig.text(0.095, 0.935, "S2 — 3D Preprocessing: from 2D masks to 3D objects", color=INK,
             fontsize=26, weight="bold", va="center")
    fig.text(0.095, 0.892, "Geometry only (Python + Open3D) · no model training · branch-ready module in src/preprocessing + src/fusion_3d",
             color=INK2, fontsize=12.5, va="center")
    fig.lines.append(plt.Line2D([0.04, 0.96], [0.86, 0.86], color=LINE, lw=1.2, transform=fig.transFigure))

    # Left: pipeline steps
    steps = [
        ("IN", "S1: RGB + aligned depth + intrinsics.yaml\nS3: observation.json (bbox, SAM mask PNG, labels)"),
        ("1", "Clean depth (range clip, holes) + RANSAC desk plane"),
        ("2", "Mask filter → deproject  X=(u−cx)Z/fx,  Y=(v−cy)Z/fy"),
        ("3", "Voxel 3 mm → statistical outlier removal → DBSCAN"),
        ("4", "Centroid, Open3D OBB, upright box in map frame"),
        ("5", "Quality → adaptive weights (depth ↓ on shiny objects)"),
        ("OUT", "ObjectInstance3D JSON → S4 (graph), S6 (tracking)"),
    ]
    x0, y_top, h, gap = 0.04, 0.80, 0.088, 0.016
    for i, (tag, txt) in enumerate(steps):
        y = y_top - i * (h + gap) - h
        io = tag in ("IN", "OUT")
        card(fig, x0, y, 0.33, h, fc="#eef4fc" if io else "white", ec=ACCENT if io else LINE)
        fig.text(x0 + 0.018, y + h / 2, tag, color=ACCENT, fontsize=13 if io else 16, weight="bold", va="center")
        fig.text(x0 + 0.06, y + h / 2, txt, color=INK, fontsize=11.2, va="center", linespacing=1.35)

    # Centre: 3D result
    ax = fig.add_axes([0.385, 0.10, 0.37, 0.73])
    img = mpimg.imread(SHOTS / "03_scene_3d_bounding_boxes.png")
    h_img = img.shape[0]
    ax.imshow(img[int(0.06 * h_img):int(0.92 * h_img)])
    ax.axis("off")
    fig.text(0.39, 0.815, "Result: 3D boxes over every desk object (label + depth_confidence)",
             color=INK2, fontsize=11.5, weight="bold")
    ax2 = fig.add_axes([0.385, 0.075, 0.37, 0.12])
    inp = mpimg.imread(SHOTS / "01_inputs_S1_S3.png")
    ax2.imshow(inp)
    ax2.axis("off")

    # Right: key numbers
    stats = [
        (f"{int(round(s['recall'] * s['n_objects']))}/{s['n_objects']}", "objects localized in 3D", ACCENT),
        (f"{s['mean_box_center_error_m'] * 100:.1f} cm", "mean 3D box-centre error\nvs ground truth", ACCENT),
        (f"{glass['depth_confidence']:.2f} → {glass['fusion_weights']['depth']:.2f}", "glass: depth_confidence →\ndepth weight (adaptive fusion)", ACCENT2),
        (s["tests"], "unit, S3-interface and\nend-to-end tests pass", ACCENT3),
    ]
    for i, (big, small, col) in enumerate(stats):
        y = 0.70 - i * 0.165
        card(fig, 0.78, y, 0.18, 0.145)
        fig.text(0.795, y + 0.095, big, color=col, fontsize=25, weight="bold", va="center")
        fig.text(0.795, y + 0.038, small, color=INK2, fontsize=10.5, va="center", linespacing=1.3)

    fig.text(0.04, 0.03, "Mock S1/S3 frame (ray-cast RealSense D435 model with noise, dropouts, flying pixels) — "
             "swap in the real Static Baseline bag with no code changes.",
             color=MUTED, fontsize=10.5)
    out = ROOT / "docs" / "s2" / "slide_06_S2.png"
    fig.savefig(out, dpi=120, facecolor=SURFACE)
    print("wrote", out.relative_to(ROOT))


if __name__ == "__main__":
    main()
