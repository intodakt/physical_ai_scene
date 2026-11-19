"""S6 multi-term tracker: persistent IDs, track states, confidence decay and object events.

Roadmap §11.6 (P1): multi-term / Hungarian association; track states; confidence decay; event
generation (APPEARED / MOVED / OCCLUDED / REAPPEARED / PICKED_UP / PLACED_ON / REMOVED).

Per frame:
1. predict   every observed track moves on with its smoothed velocity (constant-velocity model)
2. cost      for each (track, detection) pair:
                 d / gate                      position term (to the predicted centre)
               + w_label · label term          0 same label · 0.5 shared label candidate · else forbidden
               + w_size  · relative size change
             observed tracks are gated at ``gate_m``; occluded tracks at ``reid_gate_m`` (an object may
             come back somewhere else, e.g. after being picked up and put down)
3. assign    Hungarian on the cost matrix; pairs above the gate are left unmatched
4. update    matched → observed; unmatched track → occluded (confidence × decay) → removed after
             ``max_missed_frames``; unmatched detection → a removed track from the long-term memory
             (same label and size, within ``reid_gate_m``, removed ≤ ``long_memory_frames`` ago) gets its
             ID back (REAPPEARED, W10), otherwise a new track (APPEARED)
5. events    from the state changes and from where the object rests

Input/output contract is the S2 frame payload: ``update(objects)`` writes ``persistent_id`` into each
object dict (ID format ``<label>_NN``, as in the Week-5 baseline) and nothing else, so S4 and the
contracts are unchanged. Track states and events are exported separately (TrackState JSON and
event_log.jsonl).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import numpy as np

from .assignment import linear_sum_assignment

SCHEMA_VERSION = "s6-track-state-1.0"
FORBIDDEN = 1e6


@dataclass
class Track:
    persistent_id: str
    label: str
    labels: set
    center: np.ndarray
    size: Optional[np.ndarray]
    confidence: float
    first_seen: float
    last_seen: float
    state: str = "observed"            # observed | occluded | removed
    missed: int = 0
    hits: int = 1
    velocity: np.ndarray = field(default_factory=lambda: np.zeros(3))
    rest: Optional[np.ndarray] = None  # where the object last came to rest (for MOVED)
    lifted: bool = False
    history: list = field(default_factory=list)  # [(timestamp, [x, y, z])]
    removed_frame: int = -1

    def to_dict(self) -> dict:
        return {"persistent_id": self.persistent_id, "label": self.label, "label_candidates": sorted(self.labels),
                "state": self.state, "center_map": [round(float(x), 4) for x in self.center],
                "size": None if self.size is None else [round(float(x), 4) for x in self.size],
                "confidence": round(float(self.confidence), 4), "first_seen": self.first_seen,
                "last_seen": self.last_seen, "missed_frames": self.missed, "hits": self.hits,
                "lifted": self.lifted, "n_history": len(self.history)}


def _center(o) -> np.ndarray:
    box = o.get("box_map") or {}
    return np.asarray(box.get("center") or o.get("centroid_map") or o["centroid"], dtype=float)


def _size(o) -> Optional[np.ndarray]:
    dims = (o.get("box_map") or {}).get("dimensions") or o.get("box_dimensions")
    return None if not dims else np.asarray(dims, dtype=float)


def _bottom_z(o) -> Optional[float]:
    box = o.get("box_map") or {}
    if box.get("center") is None or not box.get("dimensions"):
        return None
    return float(box["center"][2]) - float(box["dimensions"][1]) / 2      # S2 box dims are [W, H, D]


@dataclass
class MultiTermTracker:
    gate_m: float = 0.15               # observed track: same object if it moved less than this per frame
    max_missed_frames: int = 10        # occlusion memory (TTL), then REMOVED
    reid_gate_m: float = 0.60          # occluded track: may come back this far away (relocation)
    w_label: float = 1.0
    w_size: float = 0.5
    move_threshold_m: float = 0.03     # rest position changed more than this → MOVED
    confidence_decay: float = 0.85     # per missed frame
    velocity_smoothing: float = 0.5
    desk_top_z: float = 0.0
    lift_threshold_m: float = 0.03     # box bottom this far above the desk → lifted (PICKED_UP)
    history_len: int = 300
    long_memory_frames: int = 150      # W10: removed tracks can still be re-identified this long (0 = off)
    tracks: list = field(default_factory=list)
    last_motion: dict = field(default_factory=dict)   # persistent_id -> metres moved since last frame
    events: list = field(default_factory=list)        # this frame's events
    event_log: list = field(default_factory=list)     # all events
    lost: list = field(default_factory=list)          # removed tracks kept for long-term re-identification
    _counts: dict = field(default_factory=dict)
    _frame: int = -1

    # ------------------------------------------------------------ association
    def _label_term(self, t: Track, o: dict) -> float:
        lab = o["semantic_label"]
        if lab == t.label:
            return 0.0
        cands = set(o.get("label_candidates") or []) | {lab}
        return 0.5 if cands & t.labels else FORBIDDEN

    def _cost(self, live: list, objects: list) -> np.ndarray:
        C = np.full((len(live), len(objects)), FORBIDDEN)
        for i, t in enumerate(live):
            pred = t.center + (t.velocity if t.state == "observed" else 0)
            gate = self.gate_m if t.state == "observed" else self.reid_gate_m
            for j, o in enumerate(objects):
                lt = self._label_term(t, o)
                if lt >= FORBIDDEN:
                    continue
                c = _center(o)       # predicted or last position, whichever is closer (a stop is not a jump)
                d = float(min(np.linalg.norm(c - pred), np.linalg.norm(c - t.center)))
                if d > gate:
                    continue
                s = _size(o)
                st = 0.0 if (s is None or t.size is None) else float(np.mean(np.abs(s - t.size) / np.maximum(t.size, 1e-3)))
                # re-identifying an occluded track costs a little more, so a visible track wins a tie
                C[i, j] = d / gate + self.w_label * lt + self.w_size * min(st, 1.0) + (0.25 if t.state == "occluded" else 0.0)
        return C

    # ------------------------------------------------------------ events
    def _event(self, kind: str, t: Track, ts: float, **extra):
        e = {"frame": self._frame, "timestamp": ts, "event": kind, "persistent_id": t.persistent_id, "label": t.label,
             "center_map": [round(float(x), 4) for x in t.center], **extra}
        self.events.append(e)
        self.event_log.append(e)

    def _rest_and_lift(self, t: Track, o: dict, ts: float, reappeared: bool):
        bottom = _bottom_z(o)
        lifted = bottom is not None and bottom > self.desk_top_z + self.lift_threshold_m
        if lifted and not t.lifted:
            self._event("PICKED_UP", t, ts)
        if t.lifted and not lifted:
            self._event("PLACED_ON", t, ts, support="desk")
        t.lifted = lifted
        if lifted:
            return
        if t.rest is None:
            t.rest = t.center.copy()
            return
        shift = float(np.linalg.norm(t.center[:2] - t.rest[:2]))
        speed = float(np.linalg.norm(t.velocity[:2]))
        # an object "has moved" once it is at rest again away from its old rest position
        if shift > self.move_threshold_m and (speed < self.move_threshold_m / 3 or reappeared):
            self._event("MOVED", t, ts, from_map=[round(float(x), 4) for x in t.rest], distance_m=round(shift, 4))
            if reappeared:
                self._event("PLACED_ON", t, ts, support="desk")
            t.rest = t.center.copy()

    # ------------------------------------------------------------ main
    def update(self, objects: list, timestamp: Optional[float] = None) -> list:
        """Fill ``persistent_id`` on S2 objects (dicts with box_map / centroid_map). Returns ``objects``."""
        self._frame += 1
        ts = float(timestamp if timestamp is not None else self._frame)
        self.last_motion, self.events = {}, []
        live = [t for t in self.tracks if t.state != "removed"]
        C = self._cost(live, objects)
        matched_t, matched_o = set(), set()
        if live and objects:
            for i, j in zip(*linear_sum_assignment(C)):
                if C[i, j] >= FORBIDDEN:
                    continue
                matched_t.add(i)
                matched_o.add(j)
                t, o = live[i], objects[j]
                c = _center(o)
                moved = float(np.linalg.norm(c - t.center))
                reappeared = t.state == "occluded"
                if not reappeared:
                    a = self.velocity_smoothing
                    t.velocity = a * (c - t.center) + (1 - a) * t.velocity
                else:
                    t.velocity = np.zeros(3)
                    self._event("REAPPEARED", t, ts, after_frames=t.missed)
                t.center, t.state, t.missed, t.hits, t.last_seen = c, "observed", 0, t.hits + 1, ts
                s = _size(o)
                t.size = s if t.size is None or s is None else 0.7 * t.size + 0.3 * s
                t.labels |= set(o.get("label_candidates") or []) | {o["semantic_label"]}
                t.confidence = float(o.get("fused_confidence") or t.confidence)
                t.history = (t.history + [(ts, [round(float(x), 4) for x in c])])[-self.history_len:]
                o["persistent_id"] = t.persistent_id
                self.last_motion[t.persistent_id] = round(moved, 4)
                self._rest_and_lift(t, o, ts, reappeared)
        for i, t in enumerate(live):
            if i in matched_t:
                continue
            t.missed += 1
            t.confidence *= self.confidence_decay
            t.velocity = np.zeros(3)
            if t.state == "observed":
                t.state = "occluded"
                self._event("OCCLUDED", t, ts)
            if t.missed > self.max_missed_frames:
                t.state = "removed"
                self._event("REMOVED", t, ts, after_frames=t.missed)
                if self.long_memory_frames:
                    t.removed_frame = self._frame
                    self.lost.append(t)
        for j, o in enumerate(objects):
            if j in matched_o:
                continue
            old = self._from_long_memory(o)
            if old is not None:                      # W10: an object hidden longer than the TTL comes back
                c = _center(o)
                old.center, old.state, old.missed, old.hits, old.last_seen, old.velocity = c, "observed", 0, old.hits + 1, ts, np.zeros(3)
                old.history = (old.history + [(ts, [round(float(x), 4) for x in c])])[-self.history_len:]
                self.tracks.append(old)
                o["persistent_id"] = old.persistent_id
                self._event("REAPPEARED", old, ts, after_frames=self._frame - old.removed_frame + self.max_missed_frames + 1,
                            from_long_memory=True)
                self._rest_and_lift(old, o, ts, True)
                continue
            label = o["semantic_label"]
            self._counts[label] = self._counts.get(label, 0) + 1
            pid = f"{label.replace(' ', '_')}_{self._counts[label]:02d}"
            c = _center(o)
            t = Track(pid, label, set(o.get("label_candidates") or []) | {label}, c, _size(o),
                      float(o.get("fused_confidence") or 0.0), ts, ts, history=[(ts, [round(float(x), 4) for x in c])])
            self.tracks.append(t)
            o["persistent_id"] = pid
            self._event("APPEARED", t, ts)
            self._rest_and_lift(t, o, ts, False)
        self.tracks = [t for t in self.tracks if t.state != "removed"]
        self.lost = [t for t in self.lost if t.state == "removed" and self._frame - t.removed_frame <= self.long_memory_frames]
        return objects

    def _from_long_memory(self, o: dict) -> Optional["Track"]:
        """Nearest removed track with a compatible label within ``reid_gate_m`` (and similar size), or None."""
        best, best_d = None, self.reid_gate_m
        for t in self.lost:
            if self._label_term(t, o) >= FORBIDDEN:
                continue
            d = float(np.linalg.norm(_center(o) - t.center))
            s = _size(o)
            if s is not None and t.size is not None and np.mean(np.abs(s - t.size) / np.maximum(t.size, 1e-3)) > 0.5:
                continue
            if d <= best_d:
                best, best_d = t, d
        if best is not None:
            self.lost.remove(best)
        return best

    # ------------------------------------------------------------ export
    def state(self, timestamp: Optional[float] = None) -> dict:
        """TrackState JSON (one per frame)."""
        return {"schema_version": SCHEMA_VERSION, "frame": self._frame, "timestamp": timestamp,
                "tracks": [t.to_dict() for t in self.tracks], "events": list(self.events)}

    def history(self, persistent_id: str) -> list:
        """[(timestamp, [x, y, z])] of one track, for temporal queries ("where was the mug before?")."""
        return next((list(t.history) for t in self.tracks if t.persistent_id == persistent_id), [])

    def write_event_log(self, path) -> Path:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("".join(json.dumps(e) + "\n" for e in self.event_log), encoding="utf-8")
        return p
