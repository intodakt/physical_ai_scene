"""One command for the whole W12–W16 evaluation (professor's guide §10.5 "single-command run script").

    python -m src.evaluation.run_all --frames-root /data/frames --bags /data/bags --runs-root /data/runs

Runs every step whose inputs exist and skips the others with the reason, then builds the report:

    S1  plan + metadata templates + manifest/completeness (with --bags)
    S2  fusion ablation             (needs ground_truth_positions.csv + --frames-root)
    S3  predictions of both detectors + scores + prompt robustness  (needs detection_annotations.csv + --frames-root)
    S4  relation score / NEAR sweep / events / flips   (needs relation_ground_truth.csv / --runs-root)
    S5  four configurations on queries_200.csv
    S6  tracking scores (needs tracking_ground_truth.csv + --runs-root) and the 60 action trials
    S7  end-to-end tasks (needs end_to_end_tasks.csv + --frames-root)
    report: tables 1–7, figures 1–9, acceptance checklist; environment_freeze.txt (pip freeze)

``--runs-root`` holds one pipeline output folder per bag (``main_pipeline.py --bag <bag> --out <runs-root>/<bag_id>``).
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from .common import GT, QUERIES, REPORT, TASKS, read_csv


def _run(args: list, why_skip: str | None = None) -> bool:
    if why_skip:
        print(f"  - skip: {why_skip}")
        return False
    print("  $ python -m", " ".join(args))
    r = subprocess.run([sys.executable, "-m", *args])
    if r.returncode:
        print(f"  ! exited with {r.returncode}")
    return r.returncode == 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--frames-root", help="<bag_id>/<frame_id>/ folders (rgb.png, depth, observation.json)")
    ap.add_argument("--bags", nargs="*", default=[])
    ap.add_argument("--runs-root", help="one pipeline output folder per bag")
    ap.add_argument("--parser", default="auto", choices=["auto", "ollama", "rules"])
    ap.add_argument("--repeats", type=int, default=3)
    ap.add_argument("--skip", nargs="*", default=[], help="e.g. S3 S7")
    a = ap.parse_args()
    runs = sorted(str(p) for p in Path(a.runs_root).iterdir() if p.is_dir()) if a.runs_root else []
    has = lambda p: bool(read_csv(p))
    fr = a.frames_root

    steps = [
        ("S1", [["src.evaluation.s1_dataset", "plan"], ["src.evaluation.s1_dataset", "metadata"]]
         + ([["src.evaluation.s1_dataset", "manifest", "--bags", *a.bags]] if a.bags else [["src.evaluation.s1_dataset", "status"]]), None),
        ("S2", [["src.evaluation.s2_fusion_eval", "--frames", str(fr)]
                + (["--tf", "configs/sensors/measured_tf.yaml"] if Path("configs/sensors/measured_tf.yaml").exists() else [])],
         None if fr and has(GT / "ground_truth_positions.csv") else "needs --frames-root and eval/ground_truth/ground_truth_positions.csv"),
        ("S3", [["src.evaluation.s3_detection_eval", "predict", "--detector", d, "--frames", str(fr)] for d in ("yolo_world", "grounding_dino")]
         + [["src.evaluation.s3_detection_eval", "score", "--frames", str(fr)],
            ["src.evaluation.s3_detection_eval", "prompts", "--frames", str(fr)]]
         + ([["src.evaluation.s3_detection_eval", "clip", "--run", runs[0]]] if runs else []),
         None if fr and has(GT / "detection_annotations.csv") else "needs --frames-root and eval/ground_truth/detection_annotations.csv"),
        ("S4", [["src.evaluation.s4_relation_eval", "score"], ["src.evaluation.s4_relation_eval", "sweep", "--runs", *runs],
                ["src.evaluation.s4_relation_eval", "events", "--runs", *runs], ["src.evaluation.s4_relation_eval", "flips", "--runs", *runs]],
         None if runs and has(GT / "relation_ground_truth.csv") else "needs --runs-root and eval/ground_truth/relation_ground_truth.csv"),
        ("S5", [["src.evaluation.s5_query_eval", "run", "--parser", a.parser]],
         None if has(QUERIES / "queries_200.csv") else "needs eval/queries/queries_200.csv (s5_query_eval graphs + generate)"),
        ("S6", [["src.evaluation.s6_tracking_eval", "actions"]]
         + ([["src.evaluation.s6_tracking_eval", "score", "--runs", *runs] + (["--frames-root", fr] if fr else [])]
            if runs and has(GT / "tracking_ground_truth.csv") else []), None),
        ("S7", [["src.evaluation.s7_e2e_eval", "run", "--frames-root", str(fr), "--repeats", str(a.repeats), "--parser", a.parser]],
         None if fr and has(TASKS / "end_to_end_tasks.csv") else "needs --frames-root and eval/tasks/end_to_end_tasks.csv"),
    ]
    for name, cmds, skip in steps:
        print(f"[{name}]")
        if name in a.skip:
            print("  - skipped by --skip")
            continue
        for c in cmds:
            if not _run(c, skip):
                break
    REPORT.mkdir(parents=True, exist_ok=True)
    freeze = subprocess.run([sys.executable, "-m", "pip", "freeze"], capture_output=True, text=True).stdout
    (REPORT / "environment_freeze.txt").write_text(f"# python {sys.version.split()[0]}\n{freeze}", encoding="utf-8")
    print("[report]")
    _run(["src.evaluation.report"])


if __name__ == "__main__":
    main()
