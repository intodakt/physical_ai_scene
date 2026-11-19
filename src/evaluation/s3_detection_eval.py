"""S3 (Li Yizhe) — two-detector benchmark, seen/unseen P/R/F1, prompt robustness, distractors, CLIP on real data.

Professor's guide §6. Ground truth: eval/ground_truth/detection_annotations.csv (Appendix A.3: one row per
object appearance: image_id, class, seen_unseen, xmin, ymin, xmax, ymax). ``image_id`` is the frame path
relative to ``--frames`` (``<bag_id>/<frame_id>``; the image is ``rgb.png`` inside, or the path itself).

    # 0. a first annotation draft from the detector, which people then correct (faster than drawing)
    python -m src.evaluation.s3_detection_eval draft --frames /data/frames --images-list keyframes.txt
    # 1. predictions of each detector with the SAME frozen prompts / thresholds / frames
    python -m src.evaluation.s3_detection_eval predict --detector yolo_world     --frames /data/frames
    python -m src.evaluation.s3_detection_eval predict --detector grounding_dino --frames /data/frames
    # 2. P / R / F1 (IoU >= 0.5, same canonical class) per detector, split and class + failure crops
    python -m src.evaluation.s3_detection_eval score --frames /data/frames
    # 3. prompt robustness + distractor test on the unseen classes (5 prompt forms each)
    python -m src.evaluation.s3_detection_eval prompts --detector yolo_world --frames /data/frames
    # 4. CLIP consistency on real tracked crops (same object over time vs different objects)
    python -m src.evaluation.s3_detection_eval clip --run outputs/pipeline --frames outputs/pipeline_frames

Outputs (eval/results/s3/): predictions_<detector>.csv, detector_comparison.csv, precision_recall_f1_table.csv,
seen_unseen_annotations.csv, prompt_robustness.csv, distractor_test.csv, clip_similarity_real_data.csv,
clip_similarity.png, failure_cases/ (crops + failures.csv with an explanation column).
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

import numpy as np
import yaml

from ..open_vocab.aliases import canonical
from .common import COLUMNS, GT, as_float, read_csv, results_dir, write_csv, write_json
from .stats import cosine, describe, iou_2d, prf

IOU_MIN = 0.5
DEFAULT_CONFIG = Path("configs/frozen/desk_v1.json")
VARIANTS = Path("src/open_vocab/configs/prompt_variants.yaml")


def image_path(frames_root, image_id) -> Path:
    p = Path(frames_root) / image_id
    return p / "rgb.png" if p.is_dir() else p


def load_image_bgr(frames_root, image_id):
    import cv2
    return cv2.imread(str(image_path(frames_root, image_id)))


def frozen_config(path=None) -> dict:
    p = Path(path) if path else DEFAULT_CONFIG
    if not p.exists():
        p = Path("src/open_vocab/configs/desk.json")
    cfg = json.loads(p.read_text())
    return cfg.get("config", cfg)


def _gt_by_image(rows) -> dict:
    out = defaultdict(list)
    for r in rows:
        out[r["image_id"]].append({"class": canonical(r["class"]), "split": r.get("seen_unseen", "seen"),
                                   "box": [as_float(r[k]) for k in ("xmin", "ymin", "xmax", "ymax")]})
    return out


# ---------------------------------------------------------------- predictions
def predict(detector_name, frames_root, image_ids, cfg, detector=None, prompt_type="frozen") -> list[dict]:
    from ..open_vocab.models import make_detector

    det = detector or make_detector(detector_name, cfg)
    rows = []
    for iid in image_ids:
        img = load_image_bgr(frames_root, iid)
        if img is None:
            print(f"skip {iid}: image not found")
            continue
        for d in det.detect(img):
            x1, y1, x2, y2 = d["bbox"]
            rows.append({"image_id": iid, "class": canonical(d["labels"][0]), "xmin": x1, "ymin": y1, "xmax": x2, "ymax": y2,
                         "prompt_type": prompt_type, "prompt_text": d["labels"][0], "detector": detector_name,
                         "pred_score": d["detector_score"]})
    return rows


def match(gt_rows: list, pred_rows: list, iou_min=IOU_MIN):
    """Greedy (highest score first) one-to-one matching per image and canonical class.
    Returns (pred rows with tp_fp_fn filled, list of missed GT objects)."""
    gt = _gt_by_image(gt_rows)
    by_img = defaultdict(list)
    for p in pred_rows:
        by_img[p["image_id"]].append(p)
    out, missed = [], []
    for iid in sorted(set(gt) | set(by_img)):
        G = gt.get(iid, [])
        used = [False] * len(G)
        for p in sorted(by_img.get(iid, []), key=lambda r: -as_float(r["pred_score"], 0)):
            box = [as_float(p[k]) for k in ("xmin", "ymin", "xmax", "ymax")]
            best, best_iou = None, iou_min
            for k, g in enumerate(G):
                if not used[k] and g["class"] == canonical(p["class"]):
                    v = iou_2d(box, g["box"])
                    if v >= best_iou:
                        best, best_iou = k, v
            if best is None:
                out.append({**p, "seen_unseen": "", "tp_fp_fn": "fp"})
            else:
                used[best] = True
                out.append({**p, "seen_unseen": G[best]["split"], "tp_fp_fn": "tp", "iou": round(best_iou, 3)})
        for k, g in enumerate(G):
            if not used[k]:
                missed.append({"image_id": iid, "class": g["class"], "seen_unseen": g["split"],
                               "xmin": g["box"][0], "ymin": g["box"][1], "xmax": g["box"][2], "ymax": g["box"][3], "tp_fp_fn": "fn"})
    return out, missed


def score(gt_rows: list, preds: dict) -> tuple[list, list]:
    """preds: detector -> rows. Returns (detector_comparison rows, per-class rows)."""
    unseen = {canonical(r["class"]) for r in gt_rows if r.get("seen_unseen") == "unseen"}
    comp, per_class = [], []
    for det, rows in preds.items():
        matched, missed = match(gt_rows, rows)
        cnt = defaultdict(lambda: {"tp": 0, "fp": 0, "fn": 0})
        for r in matched:
            cnt[canonical(r["class"])][r["tp_fp_fn"]] += 1
        for m in missed:
            cnt[m["class"]]["fn"] += 1
        for split in ("seen", "unseen", "all"):
            agg = {"tp": 0, "fp": 0, "fn": 0}
            for c, v in cnt.items():
                if split == "all" or (c in unseen) == (split == "unseen"):
                    for k in agg:
                        agg[k] += v[k]
            comp.append({"detector": det, "split": split, **prf(**agg)})
        for c, v in sorted(cnt.items()):
            per_class.append({"detector": det, "class": c, "split": "unseen" if c in unseen else "seen", **prf(**v)})
    return comp, per_class


def failure_crops(frames_root, gt_rows, preds: dict, out: Path, limit: int = 40) -> list:
    """Every FP / FN (up to ``limit`` per detector) saved as a crop + a row to explain by hand."""
    import cv2

    d = out / "failure_cases"
    d.mkdir(parents=True, exist_ok=True)
    rows = []
    for det, pr in preds.items():
        matched, missed = match(gt_rows, pr)
        bad = [r for r in matched if r["tp_fp_fn"] == "fp"] + missed
        for k, r in enumerate(bad[:limit]):
            img = load_image_bgr(frames_root, r["image_id"])
            name = f"{det}_{k:03d}_{r['tp_fp_fn']}_{str(r['class']).replace(' ', '_')}.png"
            if img is not None:
                x1, y1, x2, y2 = (int(round(as_float(r[c]))) for c in ("xmin", "ymin", "xmax", "ymax"))
                pad = 20
                crop = img[max(0, y1 - pad):y2 + pad, max(0, x1 - pad):x2 + pad].copy()
                cv2.imwrite(str(d / name), crop)
            rows.append({"file": name, "detector": det, "kind": r["tp_fp_fn"], "image_id": r["image_id"], "class": r["class"],
                         "score": r.get("pred_score", ""), "explanation": ""})
    write_csv(d / "failures.csv", rows)
    return rows


# ---------------------------------------------------------------- prompt robustness + distractors
def prompt_forms(path=VARIANTS) -> dict:
    return yaml.safe_load(Path(path).read_text())


def prompts_test(detector_name, frames_root, gt_rows, cfg, forms=None, detector_factory=None) -> tuple[list, list]:
    """For every unseen class and prompt form: run the detector with (seen prompts + that one prompt) on the
    frames that contain the class. Record detected (IoU >= 0.5) and the score; the distractor column says
    which annotated object the top-scoring box of that prompt landed on."""
    from ..open_vocab.models import make_detector

    forms = forms or prompt_forms()
    gt = _gt_by_image(gt_rows)
    seen_prompts = [p for p in cfg["prompts"] if canonical(p) not in {canonical(c) for c in forms}]
    rows, distract = [], []
    for cls, variants in forms.items():
        c = canonical(cls)
        images = [i for i, objs in gt.items() if any(o["class"] == c for o in objs)]
        if not images:
            continue
        for ptype, text in variants.items():
            run_cfg = {**cfg, "prompts": seen_prompts + [text]}
            det = detector_factory(run_cfg) if detector_factory else make_detector(detector_name, run_cfg)
            for iid in images:
                img = load_image_bgr(frames_root, iid)
                if img is None:
                    continue
                dets = [d for d in det.detect(img) if d["labels"][0] == text]
                gbox = [o["box"] for o in gt[iid] if o["class"] == c]
                hit = max(((d["detector_score"], max(iou_2d(d["bbox"], b) for b in gbox)) for d in dets), default=(0.0, 0.0))
                ok = [d for d in dets if max(iou_2d(d["bbox"], b) for b in gbox) >= IOU_MIN]
                rows.append({"detector": detector_name, "class": c, "prompt_type": ptype, "prompt_text": text, "image_id": iid,
                             "detected": int(bool(ok)), "score": round(max((d["detector_score"] for d in ok), default=0.0), 4),
                             "best_iou": round(hit[1], 3)})
                if dets:
                    top = max(dets, key=lambda d: d["detector_score"])
                    on = max(gt[iid], key=lambda o: iou_2d(top["bbox"], o["box"]))
                    landed = on["class"] if iou_2d(top["bbox"], on["box"]) >= IOU_MIN else "background"
                else:
                    landed = "nothing"
                distract.append({"detector": detector_name, "class": c, "prompt_type": ptype, "prompt_text": text, "image_id": iid,
                                 "selected": landed, "correct": int(landed == c),
                                 "distractors_in_frame": ";".join(sorted({o["class"] for o in gt[iid]} - {c}))})
    return rows, distract


def summarise_prompts(rows) -> list:
    out = []
    for (det, ptype), sub in sorted(_group(rows, ("detector", "prompt_type")).items()):
        n, k = len(sub), sum(int(r["detected"]) for r in sub)
        out.append({"detector": det, "prompt_type": ptype, "detected": f"{k}/{n}", "recall": round(k / n, 4) if n else None,
                    "mean_score_when_detected": describe([r["score"] for r in sub if int(r["detected"])])["mean"]})
    return out


def _group(rows, keys):
    g = defaultdict(list)
    for r in rows:
        g[tuple(r[k] for k in keys)].append(r)
    return g


# ---------------------------------------------------------------- CLIP on real tracked crops (§6.6)
def clip_pairs(run_dir, frames_root, embedder=None, min_gap=5, max_pairs=200, seed=0) -> list:
    """Crops of tracked objects (S2 bbox_2d + S6 persistent_id) → same-object pairs ≥ ``min_gap`` frames apart
    and different-object pairs from the same frame, cosine similarity of the embeddings."""
    import cv2

    from ..open_vocab.embeddings import ColorHistEmbedder

    emb = embedder or ColorHistEmbedder()
    crops = []
    for k, p in enumerate(sorted((Path(run_dir) / "objects").glob("*_objects.json"))):
        d = json.loads(p.read_text())
        img_p = Path(frames_root) / d["frame"] / "rgb.png"
        if not img_p.exists():
            continue
        rgb = cv2.cvtColor(cv2.imread(str(img_p)), cv2.COLOR_BGR2RGB)
        for o in d["objects"]:
            b = o.get("bbox_2d")
            if not b or not o.get("persistent_id"):
                continue
            x1, y1, x2, y2 = (int(round(v)) for v in b)
            mask = np.zeros(rgb.shape[:2], bool)
            mask[max(0, y1):y2, max(0, x1):x2] = True
            if mask.sum() < 50:
                continue
            crops.append({"frame_idx": k, "frame": d["frame"], "pid": o["persistent_id"], "vec": emb.embed(rgb, mask)})
    rng = np.random.default_rng(seed)
    same, diff = [], []
    for i, a in enumerate(crops):
        for b in crops[i + 1:]:
            if a["pid"] == b["pid"] and abs(a["frame_idx"] - b["frame_idx"]) >= min_gap:
                same.append((a, b))
            elif a["pid"] != b["pid"] and a["frame_idx"] == b["frame_idx"]:
                diff.append((a, b))
    rows = []
    for kind, pairs in (("same_object", same), ("different_object", diff)):
        idx = rng.permutation(len(pairs))[:max_pairs]
        for j in idx:
            a, b = pairs[j]
            rows.append({"pair": kind, "a": f"{a['frame']}:{a['pid']}", "b": f"{b['frame']}:{b['pid']}",
                         "cosine": round(cosine(a["vec"], b["vec"]), 4), "embedder": type(emb).__name__})
    return rows


def plot_clip(rows, out: Path) -> Path | None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return None
    fig, ax = plt.subplots(figsize=(6.5, 3.6), dpi=150)
    for kind, col in (("same_object", "#14a085"), ("different_object", "#d18b0f")):
        v = [r["cosine"] for r in rows if r["pair"] == kind]
        if v:
            ax.hist(v, bins=20, range=(min(0, min(v)), 1), alpha=0.7, color=col, label=f"{kind.replace('_', ' ')} (n={len(v)})")
    ax.set_xlabel("cosine similarity")
    ax.set_ylabel("pairs")
    ax.set_title(f"Embedding consistency on real crops ({rows[0]['embedder'] if rows else ''})")
    ax.legend(frameon=False)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    p = out / "clip_similarity.png"
    fig.savefig(p)
    plt.close(fig)
    return p


# ---------------------------------------------------------------- annotation draft
def draft(frames_root, image_ids, cfg, detector_name="yolo_world", detector=None, out: Path | None = None) -> Path:
    """Detector boxes as a draft of detection_annotations.csv + overlay images to check against (§6.2)."""
    import cv2

    out = out or GT
    rows = predict(detector_name, frames_root, image_ids, cfg, detector)
    unseen = {canonical(l) for l in Path("src/open_vocab/configs/unseen_objects.txt").read_text().splitlines()
              if l.strip() and not l.startswith("#")}
    draft_rows = [{"image_id": r["image_id"], "class": r["class"], "seen_unseen": "unseen" if r["class"] in unseen else "seen",
                   **{k: round(as_float(r[k]), 1) for k in ("xmin", "ymin", "xmax", "ymax")}} for r in rows]
    p = write_csv(out / "detection_annotations_DRAFT.csv", draft_rows, COLUMNS["detection_annotations"])
    vis = out / "annotation_check"
    vis.mkdir(parents=True, exist_ok=True)
    for iid in image_ids:
        img = load_image_bgr(frames_root, iid)
        if img is None:
            continue
        for k, r in enumerate(x for x in draft_rows if x["image_id"] == iid):
            x1, y1, x2, y2 = (int(r[c]) for c in ("xmin", "ymin", "xmax", "ymax"))
            cv2.rectangle(img, (x1, y1), (x2, y2), (0, 200, 0), 2)
            cv2.putText(img, f"{k}:{r['class']}", (x1, max(12, y1 - 4)), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 200, 0), 1)
        cv2.imwrite(str(vis / (iid.replace("/", "__") + ".png")), img)
    return p


def _image_ids(args, gt_rows) -> list:
    if getattr(args, "images_list", None):
        return [l.strip() for l in Path(args.images_list).read_text().splitlines() if l.strip()]
    return sorted({r["image_id"] for r in gt_rows})


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("draft", "predict", "score", "prompts", "clip"):
        s = sub.add_parser(name)
        s.add_argument("--frames", required=name != "clip")
        s.add_argument("--gt", default=str(GT / "detection_annotations.csv"))
        s.add_argument("--config", help="frozen S3 config (default configs/frozen/desk_v1.json)")
        s.add_argument("--detector", default="yolo_world", choices=["yolo_world", "grounding_dino"])
        s.add_argument("--images-list")
        if name == "score":
            s.add_argument("--detectors", nargs="+", default=["yolo_world", "grounding_dino"])
        if name == "clip":
            s.add_argument("--run", required=True, help="pipeline output folder (objects/*_objects.json)")
            s.add_argument("--clip", action="store_true", help="use the CLIP embedder (needs torch); default colour histogram")
    a = ap.parse_args()
    out = results_dir("s3")
    gt_rows = read_csv(a.gt)
    cfg = frozen_config(a.config)
    if a.cmd == "draft":
        print("->", draft(a.frames, _image_ids(a, gt_rows), cfg, a.detector))
    elif a.cmd == "predict":
        rows = predict(a.detector, a.frames, _image_ids(a, gt_rows), cfg)
        print("->", write_csv(out / f"predictions_{a.detector}.csv", rows, COLUMNS["detection_predictions"]), len(rows), "boxes")
    elif a.cmd == "score":
        preds = {d: read_csv(out / f"predictions_{d}.csv") for d in a.detectors if (out / f"predictions_{d}.csv").exists()}
        comp, per_class = score(gt_rows, preds)
        write_csv(out / "detector_comparison.csv", comp)
        write_csv(out / "precision_recall_f1_table.csv", per_class)
        write_csv(out / "seen_unseen_annotations.csv", gt_rows, COLUMNS["detection_annotations"])
        for d, rows in preds.items():
            matched, missed = match(gt_rows, rows)
            write_csv(out / f"predictions_{d}_scored.csv", matched + missed, COLUMNS["detection_predictions"] + ["iou"])
        failure_crops(a.frames, gt_rows, preds, out)
        for r in comp:
            print(r)
    elif a.cmd == "prompts":
        rows, distract = prompts_test(a.detector, a.frames, gt_rows, cfg)
        write_csv(out / "prompt_robustness.csv", rows)
        write_csv(out / "prompt_robustness_summary.csv", summarise_prompts(rows))
        write_csv(out / "distractor_test.csv", distract)
        print(summarise_prompts(rows))
    elif a.cmd == "clip":
        emb = None
        if a.clip:
            from ..open_vocab.embeddings import ClipEmbedder
            emb = ClipEmbedder()
        rows = clip_pairs(a.run, a.frames or Path(a.run) / "frames", emb)
        write_csv(out / "clip_similarity_real_data.csv", rows)
        plot_clip(rows, out)
        summ = {k: describe([r["cosine"] for r in rows if r["pair"] == k]) for k in ("same_object", "different_object")}
        write_json(out / "clip_similarity_summary.json", summ)
        print(summ)


if __name__ == "__main__":
    main()
