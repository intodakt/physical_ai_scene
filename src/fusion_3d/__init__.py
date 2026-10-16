"""S2 — 2D->3D projection, object geometry and uncertainty-aware fusion."""

from .object_instance import ObjectInstance3D
from .pipeline import FrameResult, load_config, process_frame

__all__ = ["ObjectInstance3D", "FrameResult", "load_config", "process_frame"]
