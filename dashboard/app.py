"""G1 presentation dashboard (S7).

    streamlit run dashboard/app.py

Four views of one pipeline run (outputs/pipeline, written by main_pipeline.py):
  1. Camera  - S1 RGB with S3 masks/boxes and S6 persistent IDs;
  2. 3D      - S1 depth as a point cloud with S2's 3D boxes, S6 exclusion zones and agent path;
  3. Graph   - S4 scene graph (pyvis), edges labelled with their metric evidence;
  4. Chat    - question -> S5 parsed JSON | S5 geometric proof | S6 ActionGoal + virtual twin.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.fusion_3d.geometry import gravity_box_corners  # noqa: E402
from src.integration import s5_adapter  # noqa: E402
from src.integration.pipeline import load_config  # noqa: E402
from src.integration.s6_placeholder import build_action_goal, node_label, simulate  # noqa: E402

RUN_DIR = ROOT / "outputs" / "pipeline"
PALETTE = ["#2a78d6", "#e3742b", "#3aa463", "#c64fb0", "#d6b02a", "#5bb6c9", "#8a6bd1", "#d24a4a"]
DEMO_QUERIES = ["Go to the mug", "Go to the glass", "What is closest to the laptop?",
                "Find a cup that is not near the laptop", "Which chair is closest to the laptop?"]

st.set_page_config(page_title="G1 Scene Understanding", layout="wide")


# ---------------------------------------------------------------- data
@st.cache_data
def load_run(run_dir: str, stamp: float):
    run = Path(run_dir)
    summary = json.loads((run / "run_summary.json").read_text(encoding="utf-8"))
    frames = []
    for f in summary["frames"]:
        name = f["frame"]
        frames.append({
            **f,
            "objects": json.loads((run / "objects" / f"{name}_objects.json").read_text(encoding="utf-8")),
            "graph": json.loads((run / "scene_graph" / f"{name}_scene_graph.json").read_text(encoding="utf-8")),
        })
    return summary, frames


LABEL_ORDER = ["laptop", "mug", "book", "multimeter", "glass", "cup", "chair", "desk"]


def color_of(pid: str) -> str:
    """One stable colour per object class (same colour in every view and frame)."""
    label = pid.rsplit("_", 1)[0] if pid[-1:].isdigit() else pid
    if label not in LABEL_ORDER:
        LABEL_ORDER.append(label)
    return PALETTE[LABEL_ORDER.index(label) % len(PALETTE)]


def hex_rgb(h):
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))


def run_pipeline():
    from main_pipeline import run

    with st.spinner("Running S1 -> S3 -> S2 -> S6 -> S4 -> S5 -> S6 on the demo sequence..."):
        run(out=str(RUN_DIR), quiet=True)
    st.cache_data.clear()


# ---------------------------------------------------------------- views
def camera_view(frame):
    rgb = np.array(Image.open(ROOT / frame["frame_dir"] / "rgb.png").convert("RGB")).astype(float)
    obs_path = ROOT / frame["observation"]
    obs = json.loads(obs_path.read_text(encoding="utf-8"))
    ids = frame["ids"]
    by_det = {o["source_observation_id"]: o for o in frame["objects"]["objects"]}
    fig = go.Figure()
    for det in obs["detections"]:
        o = by_det.get(det["detection_id"])
        pid = ids.get(o["object_id"]) if o else None
        col = color_of(pid or det["labels"][0])
        if det["mask_status"] == "ok":
            m = np.array(Image.open(obs_path.parent / det["mask"])) > 127
            rgb[m] = 0.55 * rgb[m] + 0.45 * np.array(hex_rgb(col))
        x1, y1, x2, y2 = det["bbox"]
        text = f"{pid or det['labels'][0]}  {det['detector_score']:.2f}"
        if o and o.get("depth_status", "ok") != "ok":
            text += f"  ({o['depth_status']})"
        fig.add_shape(type="rect", x0=x1, y0=y1, x1=x2, y1=y2, line=dict(color=col, width=2))
        fig.add_annotation(x=x1, y=y1, text=text, showarrow=False, xanchor="left", yanchor="bottom",
                           font=dict(color="white", size=11), bgcolor=col)
    fig.add_trace(go.Image(z=rgb.clip(0, 255).astype(np.uint8)))
    fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), height=430, xaxis=dict(visible=False),
                      yaxis=dict(visible=False))
    st.plotly_chart(fig, use_container_width=True)
    rej = frame["objects"].get("rejected", [])
    st.caption(f"{len(obs['detections'])} S3 detections (YOLO-World + SAM) -> {frame['n_objects']} S2 objects"
               + (f", {len(rej)} rejected" if rej else ""))


def zone_trace(z):
    xs = [p[0] for p in z["polygon"]] + [z["polygon"][0][0]]
    ys = [p[1] for p in z["polygon"]] + [z["polygon"][0][1]]
    return xs, ys


def view_3d(frame, goal=None):
    fig = go.Figure()
    pts_file = RUN_DIR / "points" / f"{frame['frame']}.npz"
    if pts_file.exists():
        pts = np.load(pts_file)
        if "_scene" in pts:
            P, C = pts["_scene"], pts["_scene_rgb"]
            keep = P[:, 2] > -0.05
            fig.add_trace(go.Scatter3d(x=P[keep, 0], y=P[keep, 1], z=P[keep, 2], mode="markers",
                                       marker=dict(size=1.5, color=[f"rgb({r},{g},{b})" for r, g, b in C[keep]]),
                                       name="depth cloud", hoverinfo="skip"))
    edges = [(0, 1), (1, 2), (2, 3), (3, 0), (4, 5), (5, 6), (6, 7), (7, 4), (0, 4), (1, 5), (2, 6), (3, 7)]
    for o in frame["objects"]["objects"]:
        if not o.get("box_map"):
            continue
        pid = frame["ids"].get(o["object_id"], o["object_id"])
        c = gravity_box_corners(o["box_map"])
        xs, ys, zs = [], [], []
        for a, b in edges:
            xs += [c[a, 0], c[b, 0], None]
            ys += [c[a, 1], c[b, 1], None]
            zs += [c[a, 2], c[b, 2], None]
        fig.add_trace(go.Scatter3d(x=xs, y=ys, z=zs, mode="lines", line=dict(color=color_of(pid), width=5),
                                   name=f"{pid} ({o['fused_confidence']:.2f})"))
    if goal:
        for z in goal["exclusion_zones"]:
            xs, ys = zone_trace(z)
            fig.add_trace(go.Scatter3d(x=xs, y=ys, z=[0.002] * len(xs), mode="lines",
                                       line=dict(color="#d24a4a", width=6, dash="dash"), name=f"no-go {z['object_id']}"))
        if goal["target_pose"]:
            a, t = goal["agent_start"], goal["target_pose"]
            fig.add_trace(go.Scatter3d(x=[a[0], t[0]], y=[a[1], t[1]], z=[0.005, 0.005], mode="lines+markers",
                                       line=dict(color="#3aa463" if goal["validated"] else "#d24a4a", width=8),
                                       name="agent path"))
    fig.update_layout(height=430, margin=dict(l=0, r=0, t=0, b=0), legend=dict(font=dict(size=10)),
                      scene=dict(aspectmode="data", xaxis_title="x (m)", yaxis_title="y (m)", zaxis_title="z (m)",
                                 camera=dict(eye=dict(x=-1.3, y=0.0, z=1.1))))
    st.plotly_chart(fig, use_container_width=True)
    st.caption("Map frame (z up). Boxes: S2 gravity-aligned ObjectInstance3D; legend shows fused confidence.")


def graph_view(graph):
    from pyvis.network import Network

    net = Network(height="420px", width="100%", directed=True, bgcolor="#ffffff", font_color="#222222",
                  cdn_resources="in_line")
    for n in graph["nodes"]:
        occluded = n["state"] == "occluded"
        net.add_node(n["id"], label=n["id"], shape="box" if n.get("virtual") else "dot", size=18,
                     color="#bbbbbb" if occluded else color_of(n["id"]),
                     title=f"{node_label(n)} | state={n['state']} | pose={n['pose_map']} | conf={n['confidence']}")
    for e in graph["edges"]:
        if e["end_time"] is not None:
            continue
        ev = ", ".join(f"{k}={v}" for k, v in e["evidence"].items() if k != "frame")
        net.add_edge(e["source"], e["target"], label=e["predicate"], title=ev,
                     arrows="" if e["predicate"] == "near" else "to", font={"size": 10})
    net.set_options('{"physics": {"barnesHut": {"springLength": 140}}, "edges": {"smooth": false}}')
    components.html(net.generate_html(notebook=False), height=440)
    active = [e for e in graph["edges"] if e["end_time"] is None]
    ended = len(graph["edges"]) - len(active)
    st.caption(f"{len(graph['nodes'])} nodes, {len(active)} active edges"
               + (f", {ended} ended (kept as history)" if ended else "") + ". Hover an edge for its metric proof.")


def topdown(graph, goal):
    fig = go.Figure()
    for n in graph["nodes"]:
        if n.get("virtual"):
            continue
        x, y, _ = n["pose_map"]
        fig.add_trace(go.Scatter(x=[y], y=[x], mode="markers+text", text=[n["id"]], textposition="top center",
                                 marker=dict(size=12, color="#bbbbbb" if n["state"] == "occluded" else color_of(n["id"])),
                                 showlegend=False))
    for z in goal["exclusion_zones"]:
        xs, ys = zone_trace(z)
        fig.add_trace(go.Scatter(x=ys, y=xs, fill="toself", fillcolor="rgba(210,74,74,0.18)",
                                 line=dict(color="#d24a4a"), name=f"exclusion {z['object_id']}"))
    a = goal["agent_start"]
    fig.add_trace(go.Scatter(x=[a[1]], y=[a[0]], mode="markers", marker=dict(symbol="square", size=14, color="#222"),
                             name="virtual agent"))
    if goal["target_pose"]:
        t = goal["target_pose"]
        fig.add_trace(go.Scatter(x=[a[1], t[1]], y=[a[0], t[0]], mode="lines",
                                 line=dict(color="#3aa463" if goal["validated"] else "#d24a4a", width=3,
                                           dash="solid" if goal["validated"] else "dash"),
                                 name="accepted path" if goal["validated"] else "rejected path"))
    fig.update_layout(height=360, margin=dict(l=0, r=0, t=10, b=0),
                      xaxis=dict(title="y (m)  ← camera right · camera left →", range=[0.6, -0.45]),
                      yaxis=dict(title="x (m) from camera", range=[0.15, 1.0], scaleanchor="x"),
                      legend=dict(orientation="h", y=-0.25))
    st.plotly_chart(fig, use_container_width=True)


def chat_view(graph, cfg, parser):
    if "history" not in st.session_state:
        st.session_state.history = []
    cols = st.columns(len(DEMO_QUERIES))
    preset = None
    for c, q in zip(cols, DEMO_QUERIES):
        if c.button(q, use_container_width=True):
            preset = q
    question = st.chat_input("Ask about the desk, e.g. 'Which cup is closest to the book?'") or preset
    if question:
        rr = s5_adapter.answer(question, graph, parser)
        goal = build_action_goal(rr, graph, cfg["action"])
        sim = simulate(goal, graph, cfg["action"])
        st.session_state.history.insert(0, {"q": question, "rr": rr, "goal": goal, "sim": sim})
    if not st.session_state.history:
        st.info("Pick a demo question or type one. The LLM only translates; the geometry decides.")
        return None
    h = st.session_state.history[0]
    rr, goal, sim = h["rr"], h["goal"], h["sim"]
    with st.chat_message("user"):
        st.write(h["q"])
    with st.chat_message("assistant"):
        (st.success if rr["verification_status"] else st.warning)(rr["final_answer"])
        for w in rr["warnings"]:
            st.caption(f"warning: {w}")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(f"**1 · S5 parser ({rr['parser']})**")
        st.json(rr.get("llm_parsed_query", {}), expanded=True)
    with c2:
        st.markdown("**2 · S5 geometric verifier**")
        st.metric("verified", "yes" if rr["verification_status"] else "no", f"confidence {rr['confidence']}")
        st.code(rr["computed_facts"], language="text")
    with c3:
        st.markdown("**3 · S6 ActionGoal**")
        st.metric("validated", "yes" if goal["validated"] else "no", goal["reason"],
                  delta_color="normal" if goal["validated"] else "inverse")
        st.json({k: goal[k] for k in ("target_object_id", "target_pose", "validated")} |
                {"exclusion_zones": [z["object_id"] for z in goal["exclusion_zones"]], "virtual_twin": sim})
    topdown(graph, goal)
    if len(st.session_state.history) > 1:
        with st.expander("Earlier questions"):
            for old in st.session_state.history[1:]:
                st.write(f"**{old['q']}** -> {old['rr']['final_answer']} (goal validated: {old['goal']['validated']})")
    return goal


# ---------------------------------------------------------------- page
def main():
    cfg = load_config()
    st.title("G1 · Semantic Scene Understanding & Scene-Graph Reasoning")
    st.caption("F2 RGB-D baseline · zero-training foundation models · sim-to-real digital twin. "
               "The LLM translates, the math decides.")

    with st.sidebar:
        st.header("Run")
        if st.button("Run pipeline on demo sequence", type="primary"):
            run_pipeline()
        parser_mode = st.radio("S5 parser", ["auto", "rules", "ollama"], horizontal=True,
                               help="auto = local Ollama model if its server answers, else the offline rule parser")
        parser = s5_adapter.resolve_parser(parser_mode)
        st.caption(f"using: **{parser}**")

    if not (RUN_DIR / "run_summary.json").exists():
        st.warning("No pipeline run yet. Press **Run pipeline** in the sidebar, or run `python main_pipeline.py`.")
        return
    summary, frames = load_run(str(RUN_DIR), (RUN_DIR / "run_summary.json").stat().st_mtime)

    with st.sidebar:
        k = st.slider("Frame", 0, len(frames) - 1, len(frames) - 1)
        frame = frames[k]
        st.markdown("**Persistent IDs (S6)**")
        st.write(", ".join(sorted(set(frame["ids"].values()))))
        moved = {p: m for p, m in frame.get("track_motion_m", {}).items() if m > 0.005}
        if moved:
            st.caption("moved since last frame: " + ", ".join(f"{p} {m * 100:.1f} cm" for p, m in moved.items()))
        st.markdown("**Stage latency (ms)**")
        st.bar_chart(summary["stage_latency_ms"], horizontal=True, height=200)

    m = st.columns(5)
    m[0].metric("Frames", summary["n_frames"])
    m[1].metric("Latency S1→S6", f"{summary['mean_latency_ms']:.0f} ms")
    m[2].metric("Throughput", f"{summary['fps']:.2f} FPS")
    m[3].metric("Objects (this frame)", frame["n_objects"])
    m[4].metric("Contract errors", len(summary["contract_errors"]))

    graph = frame["graph"]
    left, right = st.columns(2)
    with left:
        st.subheader("1 · Camera (S1 + S3)")
        camera_view(frame)
    with right:
        st.subheader("3 · Scene graph (S4)")
        graph_view(graph)
    st.subheader("4 · Ask the scene (S5 → S6)")
    goal = chat_view(graph, cfg, parser)
    st.subheader("2 · 3D view (S2 + S6)")
    view_3d(frame, goal)


main()
