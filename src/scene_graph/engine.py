"""Builds and maintains the NetworkX scene graph and exports the S5 Scene Graph JSON."""
import json
from pathlib import Path

import networkx as nx

from . import rules

SCHEMA_VERSION = "0.1"
DESK_ID = "desk_01"


def load_objects(path):
    """Read an S2 `*_objects.json` file."""
    return json.loads(Path(path).read_text())


def _to_node(o):
    """S2 ObjectInstance3D -> node attributes. Uses the map frame (z up); S2 box dims are [W, H, D]."""
    box = o["box_map"]
    w, h, d = box["dimensions"]
    labels = o.get("label_candidates") or [o["semantic_label"]]
    score = o.get("detector_score", 1.0)
    return {
        "persistent_object_id": o.get("persistent_id") or o["object_id"],
        "names": [{"text": t, "score": round(score if i == 0 else score * 0.8, 3)} for i, t in enumerate(labels)],
        "center": list(box["center"]),
        "size": [w, d, h],                 # S5 contract: [width_x, depth_y, height_z]
        "yaw": box.get("yaw", 0.0),
        "cam_x": o["centroid"][0],
        "state": o.get("state", "observed"),
        "confidence": o.get("fused_confidence"),
        "depth_confidence": o.get("depth_confidence"),
    }


class SceneGraphEngine:
    """Feed one S2 frame at a time with `update()`; read the result with `export()`.

    S2 removes the desk by support-plane RANSAC, so the desk is not an object. It is added as a
    virtual node whose top surface sits at `desk_top_z` in the map frame (0.0 for S2's map).
    """

    def __init__(self, desk_top_z=0.0, desk_size=(1.2, 0.8, 0.04), session_id="s4_session"):
        self.graph = nx.MultiDiGraph()   # directed, one edge per predicate between a pair
        self.session_id = session_id
        self.timestamp = None
        self._edges = {}                    # (source, predicate, target) -> edge record, incl. ended ones
        w, d, h = desk_size
        self._desk = {
            "persistent_object_id": DESK_ID,
            "names": [{"text": "desk", "score": 1.0}, {"text": "table", "score": 0.9}],
            "center": [0.6, 0.0, desk_top_z - h / 2], "size": [w, d, h], "yaw": 0.0, "cam_x": None,
            "state": "static", "confidence": 1.0, "depth_confidence": 1.0,
            "virtual": True, "source": "support_plane",
        }

    # -- nodes -------------------------------------------------------------
    def update(self, s2_frame):
        ts = s2_frame.get("timestamp", 0.0)
        self.timestamp = ts
        seen = {DESK_ID}
        self._upsert(DESK_ID, dict(self._desk), ts)
        for o in s2_frame["objects"]:
            attrs = _to_node(o)
            nid = attrs["persistent_object_id"]
            seen.add(nid)
            self._upsert(nid, attrs, ts)
        for nid in self.graph.nodes:          # hidden objects stay in memory, flagged occluded
            if nid not in seen:
                self.graph.nodes[nid]["state"] = "occluded"
        self._update_edges(seen, ts)
        return self

    def _upsert(self, nid, attrs, ts):
        if nid in self.graph:                 # moved object: update the node, never duplicate it
            first = self.graph.nodes[nid]["first_seen"]
            self.graph.nodes[nid].update(attrs)
            self.graph.nodes[nid]["first_seen"] = first
        else:
            self.graph.add_node(nid, first_seen=ts, **attrs)
        self.graph.nodes[nid]["last_seen"] = ts

    # -- edges -------------------------------------------------------------
    def _candidates(self, ida, idb):
        a, b = self.graph.nodes[ida], self.graph.nodes[idb]
        found = []
        virtual = a.get("virtual") or b.get("virtual")   # the desk only supports things; no near/left_of
        for src, tgt, sa, sb in ((ida, idb, a, b), (idb, ida, b, a)):
            ok, ev = rules.check_on(sa, sb)
            if ok:
                found.append((src, "on", tgt, "vertical_support", ev))
            ok, ev = (False, {}) if virtual else rules.check_left_of(sa, sb)
            if ok:
                found.append((src, "left_of", tgt, "camera_side", ev))
        ok, ev = (False, {}) if virtual else rules.check_near(a, b)
        if ok:
            s, t = sorted((ida, idb))
            found.append((s, "near", t, "proximity", ev))
        return found

    def _update_edges(self, visible, ts):
        holding = set()
        ids = sorted(visible)
        for i, ida in enumerate(ids):
            for idb in ids[i + 1:]:
                for src, pred, tgt, rtype, ev in self._candidates(ida, idb):
                    key = (src, pred, tgt)
                    holding.add(key)
                    conf = min((self.graph.nodes[n]["confidence"] or 0.0) for n in (src, tgt))
                    rec = self._edges.get(key)
                    if rec is None or rec["end_time"] is not None:     # new, or re-established
                        rec = {"source": src, "predicate": pred, "target": tgt, "start_time": ts}
                        self._edges[key] = rec
                    rec.update(relation_type=rtype, evidence=ev, confidence=round(conf, 3), end_time=None)
        for key, rec in self._edges.items():     # relation stopped holding -> close it, keep history
            if key not in holding and rec["end_time"] is None and {key[0], key[2]} <= set(visible):
                rec["end_time"] = ts
        self.graph.remove_edges_from(list(self.graph.edges))
        for (src, pred, tgt), rec in self._edges.items():
            if rec["end_time"] is None:
                self.graph.add_edge(src, tgt, key=pred, **rec)

    # -- export ------------------------------------------------------------
    def export(self):
        nodes = []
        for nid, a in self.graph.nodes(data=True):
            node = {
                "id": nid, "persistent_object_id": a["persistent_object_id"], "names": a["names"],
                "pose_map": [round(v, 4) for v in a["center"]], "size": [round(v, 4) for v in a["size"]],
                "yaw": round(a.get("yaw", 0.0), 4),   # rotation of `size` about z; footprint = rotated box
                "state": a["state"], "first_seen": a["first_seen"], "last_seen": a["last_seen"],
                "confidence": a["confidence"], "depth_confidence": a["depth_confidence"],
            }
            if a.get("virtual"):
                node["virtual"], node["source"] = True, a["source"]
            nodes.append(node)
        edges = sorted(self._edges.values(), key=lambda e: (e["source"], e["predicate"], e["target"]))
        return {
            "schema_version": SCHEMA_VERSION, "sample": False, "session_id": self.session_id,
            "frame": "map", "units": "meters", "size_order": "[width_x, depth_y, height_z]",
            "timestamp": self.timestamp, "nodes": nodes, "edges": edges,
        }

    def save(self, path):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(json.dumps(self.export(), indent=2))
