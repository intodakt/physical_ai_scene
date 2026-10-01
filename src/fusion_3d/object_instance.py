"""ObjectInstance3D — the S2 -> S4/S6 output contract.

Required by the S2 guide (Phase 4):

    centroid          [X, Y, Z]  metres, camera optical frame
    box_dimensions    [W, H, D]  metres (H vertical when the map TF is known)
    semantic_label    str        best label from S3
    depth_confidence  0.0..1.0   valid depth pixels / mask pixels

Extra fields from the project guide (§7 data contracts / §21 interfaces):
map-frame pose, OBB, point subset reference, modality quality and fusion
weights, timestamps. ``persistent_id`` stays ``None`` — S6 assigns it.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field, fields
from typing import Optional

SCHEMA_VERSION = "1.0"


@dataclass
class ObjectInstance3D:
    # --- required contract fields -------------------------------------
    centroid: list
    box_dimensions: list
    semantic_label: str
    depth_confidence: float
    # --- identity / provenance ----------------------------------------
    object_id: str = ""  # frame-local, e.g. "mug_0"
    persistent_id: Optional[str] = None  # filled by S6 tracking
    timestamp: float = 0.0
    frame_id: str = "camera_color_optical_frame"
    source_observation_id: str = ""
    # --- semantics (passed through from S3) ---------------------------
    label_candidates: list = field(default_factory=list)
    detector_score: float = 0.0
    embedding: Optional[list] = None
    bbox_2d: list = field(default_factory=list)
    # --- geometry ------------------------------------------------------
    centroid_map: Optional[list] = None
    box_map: Optional[dict] = None  # gravity-aligned {center, yaw, dimensions}
    obb: dict = field(default_factory=dict)  # Open3D OBB, camera frame
    aabb: dict = field(default_factory=dict)  # camera frame
    num_points: int = 0
    point_density: float = 0.0
    points_ref: Optional[str] = None  # "<file>.npz#<object_id>"
    # --- uncertainty / fusion -----------------------------------------
    modality_quality: dict = field(default_factory=dict)
    fusion_mode: str = "adaptive"
    fusion_weights: dict = field(default_factory=dict)
    fused_confidence: float = 0.0
    state: str = "observed"
    schema_version: str = SCHEMA_VERSION

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self, **kw) -> str:
        return json.dumps(self.to_dict(), **kw)

    @classmethod
    def from_dict(cls, d: dict) -> "ObjectInstance3D":
        names = {f.name for f in fields(cls)}
        unknown = set(d) - names
        if unknown:
            raise ValueError(f"unknown ObjectInstance3D fields: {sorted(unknown)}")
        return cls(**d)

    @classmethod
    def from_json(cls, s: str) -> "ObjectInstance3D":
        return cls.from_dict(json.loads(s))


REQUIRED_FIELDS = ("centroid", "box_dimensions", "semantic_label", "depth_confidence")


def validate(d: dict) -> None:
    """Raise if a serialized instance breaks the minimum S4/S6 contract."""
    import math

    for k in REQUIRED_FIELDS:
        if k not in d:
            raise ValueError(f"missing field {k}")
    for k in ("centroid", "box_dimensions"):
        v = d[k]
        if len(v) != 3 or not all(isinstance(x, (int, float)) and math.isfinite(x) for x in v):
            raise ValueError(f"{k} must be 3 finite numbers, got {v}")
    if not 0.0 <= d["depth_confidence"] <= 1.0:
        raise ValueError("depth_confidence must be in [0, 1]")
