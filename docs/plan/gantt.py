"""G1 16-week Gantt chart with the current week and the status of every past cell.

    python docs/plan/gantt.py docs/plan/gantt_w12.png            # NOW = week 12 (default)
    python docs/plan/gantt.py out.png --now 13

Status marks (✓ done, ◐ partly, ✗ not done) come from STATUS below — update it when a cell changes.
W12–W16 follow the professor's Weeks 12–16 evaluation guide.
"""
import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyBboxPatch, Rectangle  # noqa: E402

BG, TXT, MUT, HEAD = "#1E2023", "#F2F0EA", "#A3A19B", "#2A2D31"
PH = {  # phase: (cell fill, stripe/legend colour, label)
    "res": ("#22324A", "#3B82F6", "Research & setup"),
    "pro": ("#1B3B36", "#14A085", "Prototype on mock data"),
    "real": ("#45391F", "#D18B0F", "Real-data integration"),
    "adv": ("#363552", "#8B7FE0", "Advanced features"),
    "eval": ("#1F3A27", "#22A04A", "Evaluation & documentation"),
    "reh": ("#4A2A35", "#D9467A", "Freeze & rehearsal"),
    "exam": ("#5A2E31", "#E25C5C", "Exam / milestone"),
}
MEMBERS = [("S1 · Sensors & Data", "Muzaffar", "23013095"), ("S2 · 3D Preprocessing & Fusion", "Sarvar", "22013120"),
           ("S3 · Open-Vocab Perception", "Li Yizhe", "23013060"), ("S4 · Scene Graph Engine", "Jaloliddin", "23012848"),
           ("S5 · Language Verifier", "Kurbonaliyev Sanjarbek", "23012853"), ("S6 · Tracking & Action", "Erkinov Shakhzodjon", "23013094"),
           ("S7 · Integration & UI", "Mirzokhidbek", "23012852")]
WEEKS = [
    ("W1", "1–7 Sep", "res", ["Camera options review\n→ ZED Mini chosen", "RGB-D & pinhole model\nOpen3D basics", "Open-vocab survey\nYOLO-World, SAM 2", "Scene-graph papers\n(ConceptGraphs)", "LLM grounding papers\n(SayPlan)", "Tracking survey\n(SORT, Hungarian)", "Rubric review\nroles & timeline"]),
    ("W2", "8–14 Sep", "res", ["Ubuntu 22.04 +\nROS 2 Humble install", "Depth noise study\nfilters, outliers", "Ultralytics setup\nfirst YOLO-World run", "NetworkX basics\nrelation rule draft", "Ollama local LLM\nsetup", "2D grid simulator\nsketch", "GitHub repo &\nfolder structure"]),
    ("W3", "15–21 Sep", "pro", ["ROS bag play /\nrecord practice", "Fake depth + circle\n→ 3D centroid", "Detect laptop & mug\non a desk JPEG", "3 fake objects\nnear < 0.3 m edge", "Closest object on\nAppendix-A graph", "Line vs exclusion\nsquare check", "Blank Streamlit\ndashboard layout"]),
    ("W4", "22–28 Sep", "pro", ["ZED Mini bring-up\nstable 30 FPS", "ObjectInstance3D\nJSON contract", "SAM 2 masks from\nYOLO boxes", "Scene Graph JSON\nschema (App. A)", "Strict JSON intent\nprompt design", "Centroid tracker on\nfake trajectories", "Data contracts doc\nrequirements.txt"]),
    ("W5", "29 Sep – 5 Oct", "pro", ["Checkerboard calib\nintrinsics YAML + TF", "Mask → 3D, OBB,\ndepth conf · tests", "observation.json\nexport + unseen list", "NetworkX nodes\nnear / on / left_of", "LLM parser +\ngeometric verifier", "Exclusion-zone check\nActionGoal JSON", "Review PRs, merge\ndashboard skeleton"]),
    ("W6", "6–12 Oct", "real", ["Record S0–S3 bags\n(calib → relocation)", "Run on Static\nBaseline bag", "Run on S1 bags\nseen / unseen split", "Ingest real S2\nObjectInstance3D", "Connect to live\nS4 graph JSON", "Track real objects\npersistent IDs", "main_pipeline.py v1\nS1 → S3 → S2"]),
    ("W7", "13–19 Oct", "real", ["Record S4–S6 bags\n(unseen → language)", "Depth cleaning +\nadaptive fusion tune", "Unseen-object test\n(S4 bag)", "Graph update on\nobject relocation", "20 canonical\nqueries pass", "Occlusion handling\n(S5 bag)", "First end-to-end\nrun on 90 s bag"]),
    ("W8", "20–26 Oct", "exam", "MIDTERM EXAM|Midterm presentation · end-to-end demo on recorded ZED Mini bags (≈ 50 % milestone)"),
    ("W9", "27 Oct – 2 Nov", "adv", ["Calibration QA\nreprojection overlay", "Ablation: F1 RGB\nvs F2 RGB-D", "Second detector\nbaseline benchmark", "Temporal edges\n+ graph history", "Negative constraints\n(\"NOT near\")", "ActionGoal → virtual\nsimulator", "Dashboard: camera\n+ 3D view"]),
    ("W10", "3–9 Nov", "adv", ["Re-record weak\nscenarios", "Failure cases: shiny,\noverlap, no depth", "Prompt freezing\nsemantic scores", "under / inside rules\n+ unit tests", "Propose → verify →\ncorrect loop", "Re-ID after\nocclusion tests", "Dashboard: pyvis\ngraph + chat"]),
    ("W11", "10–16 Nov", "adv", ["Dataset README\nsession checklist", "Runtime speed-up\nper-frame latency", "CLIP embedding\nconsistency", "Graph save / load\nserialization", "Temporal queries\n(\"where before?\")", "Path blocking /\nreachability", "Latency & FPS\nlogging"]),
    ("W12", "17–23 Nov", "eval", ["Calibration bag +\nmeasured TF · 45 bags", "GT positions with S1\ncondition coverage", "Grounding DINO +\nbox annotation", "Relation sheet\n≥ 250 labels", "GT graphs →\n200 queries", "Record 30 real\ntracking sequences", "Eval toolkit merged\n30-task set"]),
    ("W13", "24–30 Nov", "eval", ["≥ 15 GT scenes\nmanifest + metadata", "M1–M4 ablation\non real GT", "Seen/unseen P/R/F1\nprompts + CLIP", "Relation P/R/F1\nNEAR sweep · events", "Configs A–D on\n200 queries", "Tracking metrics\n+ 60 action trials", "Experiment matrix\nfirst result tables"]),
    ("W14", "1–7 Dec", "eval", ["Replay check for\nall final bags", "Failure analysis\n3D stage", "Failure analysis\nperception", "Failure analysis\ngraph", "Failure analysis\nreasoning", "Failure analysis\ntracking / action", "30 e2e tasks × 3\nfailure stages"]),
    ("W15", "8–14 Dec", "reh", ["Freeze bags + calib\nREADME · demo rig", "Freeze fusion cfg\nREADME + figures", "Freeze prompts\nREADME", "Freeze thresholds\nREADME", "Freeze LLM prompt\nREADME + query log", "Safety tests\nREADME", "Clean-setup run\nreport · rehearse"]),
    ("W16", "15–21 Dec", "exam", "FINAL|Live demo on ZED Mini (12-step scenario) · code, data, configs, results and README handover"),
]
PHASES = [("Research &\nsetup\nW1–2", 0, 1, "res"), ("Prototype\non mock data\nW3–5", 2, 4, "pro"), ("Real-data\nintegration\nW6–7", 5, 6, "real"),
          ("Midterm\nW8", 7, 7, "exam"), ("Advanced\nfeatures\nW9–11", 8, 10, "adv"), ("Data +\nevaluation\nW12–14", 11, 13, "eval"),
          ("Freeze +\nrehearse\nW15", 14, 14, "reh"), ("Final\nW16", 15, 15, "exam")]
# status of past cells (repository, 26 Nov 2026); default done. (week, member index 0..6)
STATUS = {("W5", 0): "part", ("W6", 0): "part", ("W9", 0): "part", ("W10", 0): "part", ("W9", 2): "part", ("W11", 2): "part"}
MARK = {"done": ("✓", "#4FB3A9"), "part": ("◐", "#E3A33B"), "no": ("✗", "#E66767")}
DATES = {12: "17 Nov", 13: "24 Nov", 14: "1 Dec", 15: "8 Dec", 16: "15 Dec"}
F = "DejaVu Sans"


def draw(out: Path, now: int = 12):
    W, H = 16.54, 11.69
    fig = plt.figure(figsize=(W, H), dpi=200, facecolor=BG)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, W)
    ax.set_ylim(H, 0)
    ax.axis("off")

    def box(x, y, w, h, fc, ec=None, lw=0, r=0.06, alpha=1.0):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle=f"round,pad=0,rounding_size={r}", fc=fc, ec=ec or fc, lw=lw, alpha=alpha))

    ax.text(0.58, 0.5, "CAPSTONE DESIGN  ·  Group G1", color=MUT, fontsize=11, fontweight="bold", va="center", family=F)
    ax.text(0.58, 0.88, "Semantic Scene Understanding and Scene-Graph Reasoning", color=TXT, fontsize=22, fontweight="bold", va="center", family=F)
    ax.text(0.58, 1.24, "16-week project plan  ·  Fall 2026  ·  Week 1 starts 1 September 2026  ·  ZED Mini RGB-D  ·  W12–16 per the professor's evaluation guide",
            color=MUT, fontsize=9.5, va="center", family=F)
    box(13.9, 0.36, 2.06, 0.3, BG, ec=TXT, lw=1.6, r=0.05)
    ax.text(14.93, 0.51, f"NOW · Week {now} ({DATES.get(now, '')})", color=TXT, fontsize=9.5, fontweight="bold", ha="center", va="center", family=F)
    lx = 12.55
    for t, col in (("✓ done", "#4FB3A9"), ("◐ partly", "#E3A33B"), ("✗ not done", "#E66767")):
        ax.text(lx, 1.24, t, color=col, fontsize=9.5, fontweight="bold", va="center", family=F)
        lx += 1.05
    lx = 0.58
    for k in ["res", "pro", "real", "adv", "eval", "reh", "exam"]:
        box(lx, 1.52, 0.2, 0.18, PH[k][1], r=0.03)
        ax.text(lx + 0.28, 1.61, PH[k][2], color=TXT, fontsize=9, va="center", family=F)
        lx += 0.4 + len(PH[k][2]) * 0.074 + 0.3

    X0, CW, GAP, Y0, RH, RG = 2.16, 1.66, 0.14, 2.62, 0.45, 0.094
    ax.text(0.64, 2.28, "Week", color=MUT, fontsize=10, fontweight="bold", va="center", family=F)
    ax.text(14.86, 2.28, "Phase", color=MUT, fontsize=10, fontweight="bold", va="center", family=F)
    for i, (role, name, sid) in enumerate(MEMBERS):
        x = X0 + i * (CW + GAP)
        box(x, 1.98, CW, 0.62, HEAD)
        ax.text(x + CW / 2, 2.1, role, color=MUT, fontsize=7.2, ha="center", va="center", family=F)
        ax.text(x + CW / 2, 2.3, name, color=TXT, fontsize=8.6 if len(name) > 16 else 10, fontweight="bold", ha="center", va="center", family=F)
        ax.text(x + CW / 2, 2.5, sid, color=MUT, fontsize=7.6, ha="center", va="center", family=F)

    for r, (wk, dates, ph, cells) in enumerate(WEEKS):
        y = Y0 + r * (RH + RG)
        n = r + 1
        past, is_now = n < now, n == now
        a = 0.55 if past else 1.0
        box(0.58, y, 1.4, RH, "#33373C" if is_now else HEAD, ec=TXT if is_now else None, lw=1.4 if is_now else 0)
        ax.text(0.7, y + 0.16, wk, color=TXT, fontsize=12, fontweight="bold", va="center", family=F, alpha=a)
        ax.text(0.7, y + 0.34, dates, color=MUT, fontsize=7.6, va="center", family=F, alpha=a)
        if is_now:
            ax.text(1.88, y + 0.16, "◆ now", color="#E3A33B", fontsize=8, fontweight="bold", ha="right", va="center", family=F)
        if isinstance(cells, str):
            t1, t2 = cells.split("|")
            box(X0, y, 7 * CW + 6 * GAP, RH, PH["exam"][0], ec=PH["exam"][1], lw=1.4, alpha=a)
            ax.text(X0 + (7 * CW + 6 * GAP) / 2, y + 0.15, t1, color=TXT, fontsize=13, fontweight="bold", ha="center", va="center", family=F, alpha=a)
            ax.text(X0 + (7 * CW + 6 * GAP) / 2, y + 0.33, t2, color=TXT, fontsize=8.8, ha="center", va="center", family=F, alpha=a)
            continue
        for i, c in enumerate(cells):
            x = X0 + i * (CW + GAP)
            box(x, y, CW, RH, PH[ph][0], ec=TXT if is_now else None, lw=1.6 if is_now else 0, alpha=a)
            ax.text(x + 0.08, y + RH / 2, c, color=TXT, fontsize=7.9, va="center", family=F, linespacing=1.25, alpha=0.6 if past else 1.0)
            if past:
                st = STATUS.get((wk, i), "done")
                ax.text(x + CW - 0.07, y + 0.12, MARK[st][0], color=MARK[st][1], fontsize=9, fontweight="bold", ha="right", va="center", family=F)

    for label, a0, b0, ph in PHASES:
        y1, y2 = Y0 + a0 * (RH + RG), Y0 + b0 * (RH + RG) + RH
        ax.add_patch(Rectangle((14.86, y1), 0.07, y2 - y1, fc=PH[ph][1], ec="none"))
        ax.text(15.02, (y1 + y2) / 2, label, color=TXT, fontsize=8, va="center", family=F, linespacing=1.2)
    yn = Y0 + (now - 1) * (RH + RG) - RG / 2
    ax.plot([0.5, 14.75], [yn, yn], color="#E3A33B", lw=1.4, ls=(0, (4, 3)))
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, facecolor=BG)
    plt.close(fig)
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("out", nargs="?", default="docs/plan/gantt_w12.png")
    ap.add_argument("--now", type=int, default=12)
    a = ap.parse_args()
    print("saved", draw(Path(a.out), a.now))
