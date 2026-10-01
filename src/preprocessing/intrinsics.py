"""Camera intrinsics loading (S1 -> S2 handshake).

Accepts two YAML layouts so S1 can export whichever is easier:

1. Flat layout::

       width: 640
       height: 480
       fx: 615.0
       fy: 615.0
       cx: 320.0
       cy: 240.0
       depth_scale: 0.001   # metres per raw depth unit (RealSense = 1 mm)

2. ROS ``sensor_msgs/CameraInfo`` dump (``ros2 topic echo --once
   /camera/color/camera_info``), where ``k`` (or ``K``) is the row-major 3x3
   camera matrix.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import yaml


@dataclass(frozen=True)
class CameraIntrinsics:
    width: int
    height: int
    fx: float
    fy: float
    cx: float
    cy: float
    depth_scale: float = 0.001

    @property
    def K(self) -> np.ndarray:
        return np.array(
            [[self.fx, 0.0, self.cx], [0.0, self.fy, self.cy], [0.0, 0.0, 1.0]]
        )

    def to_dict(self) -> dict:
        return asdict(self)


def _from_mapping(data: dict) -> CameraIntrinsics:
    if all(k in data for k in ("fx", "fy", "cx", "cy")):
        fx, fy, cx, cy = data["fx"], data["fy"], data["cx"], data["cy"]
    else:
        k = data.get("k", data.get("K"))
        if isinstance(k, dict):  # OpenCV style {rows, cols, data}
            k = k["data"]
        if k is None or len(k) != 9:
            raise ValueError("Intrinsics YAML needs fx/fy/cx/cy or a 9-element K matrix")
        fx, cx, fy, cy = k[0], k[2], k[4], k[5]
    width = data.get("width", data.get("image_width"))
    height = data.get("height", data.get("image_height"))
    if width is None or height is None:
        raise ValueError("Intrinsics YAML needs width and height")
    return CameraIntrinsics(
        width=int(width),
        height=int(height),
        fx=float(fx),
        fy=float(fy),
        cx=float(cx),
        cy=float(cy),
        depth_scale=float(data.get("depth_scale", 0.001)),
    )


def load_intrinsics(path: str | Path) -> CameraIntrinsics:
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if "camera_info" in data:
        data = data["camera_info"]
    return _from_mapping(data)


def save_intrinsics(intr: CameraIntrinsics, path: str | Path) -> None:
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(intr.to_dict(), f, sort_keys=False)
