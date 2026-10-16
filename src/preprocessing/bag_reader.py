"""ROS 2 bag → synchronized RGB-D frames (S1 → S2 hand-off, Week 6).

Works without a ROS installation (pure-Python ``rosbags``). Topic names come
from a camera profile; G1 records with the ZED Mini ROS 2 wrapper, the
RealSense profile is kept for the original guide.

    # export every 10th synchronized frame of S1's static-baseline bag
    python -m src.preprocessing.bag_reader --bag data/bags/20261006_desk_S1_run01 \\
        --out data/frames/static_baseline --profile zed_mini --every 10

Each exported frame directory has the layout ``frame_loader.load_frame`` reads
(rgb.png, depth.npy in metres, camera_intrinsics.yaml, frame_meta.json); S3
writes its observation.json next to it.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, Optional

import numpy as np
from PIL import Image

from .frame_loader import SynchronizedFrame
from .intrinsics import CameraIntrinsics, save_intrinsics

PROFILES = {
    # ZED ROS 2 wrapper (zed_wrapper): depth is 32FC1 metres, registered to the left RGB image
    "zed_mini": {
        "rgb": "/zed/zed_node/rgb/image_rect_color",
        "depth": "/zed/zed_node/depth/depth_registered",
        "info": "/zed/zed_node/rgb/camera_info",
        "frame_id": "zed_left_camera_optical_frame",
    },
    # realsense2_camera with align_depth.enable:=true: depth is 16UC1 millimetres
    "realsense": {
        "rgb": "/camera/color/image_raw",
        "depth": "/camera/aligned_depth_to_color/image_raw",
        "info": "/camera/color/camera_info",
        "frame_id": "camera_color_optical_frame",
    },
}


def decode_image(msg) -> np.ndarray:
    """sensor_msgs/Image → RGB uint8 (H, W, 3) or depth (H, W) float32 metres / uint16 mm."""
    h, w, enc = int(msg.height), int(msg.width), msg.encoding.lower()
    buf = np.asarray(msg.data, dtype=np.uint8)
    channels = {"rgb8": 3, "bgr8": 3, "rgba8": 4, "bgra8": 4, "mono8": 1}
    if enc in channels:
        c = channels[enc]
        img = buf.reshape(h, int(msg.step))[:, : w * c].reshape(h, w, c)
        if enc.startswith("bgr"):
            img = img[..., [2, 1, 0]]
        elif enc == "mono8":
            img = np.repeat(img, 3, axis=2)
        return np.ascontiguousarray(img[..., :3])
    if enc == "32fc1":
        dt = np.dtype("<f4") if not msg.is_bigendian else np.dtype(">f4")
        return buf.reshape(h, int(msg.step))[:, : w * 4].copy().view(dt).reshape(h, w).astype(np.float32)
    if enc in ("16uc1", "mono16"):
        dt = np.dtype("<u2") if not msg.is_bigendian else np.dtype(">u2")
        return buf.reshape(h, int(msg.step))[:, : w * 2].copy().view(dt).reshape(h, w).astype(np.uint16)
    raise ValueError(f"unsupported image encoding {msg.encoding!r}")


def intrinsics_from_camera_info(msg, depth_scale: float = 0.001) -> CameraIntrinsics:
    k = np.asarray(msg.k, dtype=float)
    return CameraIntrinsics(int(msg.width), int(msg.height), float(k[0]), float(k[4]), float(k[2]), float(k[5]),
                            float(depth_scale))


def _stamp(msg) -> float:
    return float(msg.header.stamp.sec) + float(msg.header.stamp.nanosec) * 1e-9


@dataclass
class BagStats:
    rgb: int = 0
    depth: int = 0
    synced: int = 0
    dropped: int = 0


def iter_frames(bag: str | Path, profile: str = "zed_mini", topics: Optional[dict] = None,
                max_dt: float = 0.02, every: int = 1, stats: Optional[BagStats] = None,
                T_map_camera: Optional[np.ndarray] = None) -> Iterator[SynchronizedFrame]:
    """Yield RGB/depth pairs whose header stamps differ by ≤ ``max_dt`` seconds."""
    from rosbags.highlevel import AnyReader

    tp = dict(PROFILES[profile], **(topics or {}))
    stats = stats if stats is not None else BagStats()
    intr, last_rgb, last_depth, k = None, None, None, 0
    with AnyReader([Path(bag)]) as reader:
        conns = [c for c in reader.connections if c.topic in (tp["rgb"], tp["depth"], tp["info"])]
        missing = {tp["rgb"], tp["depth"]} - {c.topic for c in conns}
        if missing:
            raise ValueError(f"topics not in bag: {sorted(missing)} (profile {profile!r})")
        for conn, _, raw in reader.messages(connections=conns):
            msg = reader.deserialize(raw, conn.msgtype)
            if conn.topic == tp["info"]:
                if intr is None:
                    intr = intrinsics_from_camera_info(msg)
                continue
            item = (_stamp(msg), msg)
            if conn.topic == tp["rgb"]:
                stats.rgb += 1
                last_rgb = item
            else:
                stats.depth += 1
                last_depth = item
            if last_rgb is None or last_depth is None:
                continue
            dt = abs(last_rgb[0] - last_depth[0])
            if dt > max_dt:
                # keep the newer message, the older one has no partner any more
                if last_rgb[0] < last_depth[0]:
                    last_rgb = None
                else:
                    last_depth = None
                stats.dropped += 1
                continue
            if intr is None:
                raise ValueError(f"no CameraInfo on {tp['info']} before the first frame")
            rgb, depth = decode_image(last_rgb[1]), decode_image(last_depth[1])
            ts = min(last_rgb[0], last_depth[0])
            last_rgb = last_depth = None
            stats.synced += 1
            k += 1
            if (k - 1) % every:
                continue
            if depth.shape != rgb.shape[:2]:
                raise ValueError("depth is not registered to the RGB image "
                                 "(ZED: depth_registered; RealSense: align_depth.enable:=true)")
            scale = 1.0 if depth.dtype == np.float32 else 0.001
            yield SynchronizedFrame(rgb=rgb, depth_raw=depth,
                                    intrinsics=CameraIntrinsics(**{**intr.to_dict(), "depth_scale": scale}),
                                    timestamp=ts, frame_id=tp["frame_id"], T_map_camera=T_map_camera,
                                    source=f"{Path(bag).name}@{ts:.3f}")


def save_frame(frame: SynchronizedFrame, out_dir: str | Path) -> Path:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    Image.fromarray(frame.rgb).save(out / "rgb.png")
    if frame.depth_raw.dtype == np.uint16:
        Image.fromarray(frame.depth_raw).save(out / "depth.png")
    else:
        np.save(out / "depth.npy", frame.depth_raw.astype(np.float32))
    save_intrinsics(frame.intrinsics, out / "camera_intrinsics.yaml")
    meta = {"timestamp": frame.timestamp, "frame_id": frame.frame_id, "source": frame.source}
    if frame.T_map_camera is not None:
        meta["T_map_camera"] = np.asarray(frame.T_map_camera).tolist()
    (out / "frame_meta.json").write_text(json.dumps(meta, indent=2))
    return out


def export_frames(bag, out_dir, profile="zed_mini", every=1, limit=None, max_dt=0.02) -> tuple[list[Path], BagStats]:
    stats, paths = BagStats(), []
    for i, fr in enumerate(iter_frames(bag, profile, every=every, max_dt=max_dt, stats=stats)):
        if limit is not None and i >= limit:
            break
        paths.append(save_frame(fr, Path(out_dir) / f"frame_{i:04d}"))
    return paths, stats


# ---------------------------------------------------------------- writing (tests / mock bags)
def write_bag(frames: list[SynchronizedFrame], bag_path: str | Path, profile: str = "zed_mini",
              depth_offset_s: float = 0.004) -> Path:
    """Write frames as a ROS 2 bag with the profile's topics (used to test the reader)."""
    from rosbags.rosbag2 import Writer
    from rosbags.typesys import Stores, get_typestore

    ts_store = get_typestore(Stores.ROS2_HUMBLE)
    Image_, Info, Header, Time, ROI = (ts_store.types[t] for t in (
        "sensor_msgs/msg/Image", "sensor_msgs/msg/CameraInfo", "std_msgs/msg/Header",
        "builtin_interfaces/msg/Time", "sensor_msgs/msg/RegionOfInterest"))
    tp = PROFILES[profile]

    def header(t):
        return Header(stamp=Time(sec=int(t), nanosec=int(round((t - int(t)) * 1e9))), frame_id=tp["frame_id"])

    bag_path = Path(bag_path)
    with Writer(bag_path, version=8) as w:
        c_rgb = w.add_connection(tp["rgb"], Image_.__msgtype__, typestore=ts_store)
        c_dep = w.add_connection(tp["depth"], Image_.__msgtype__, typestore=ts_store)
        c_inf = w.add_connection(tp["info"], Info.__msgtype__, typestore=ts_store)
        for fr in frames:
            t, intr = fr.timestamp, fr.intrinsics
            h, wd = fr.rgb.shape[:2]
            k = np.array([intr.fx, 0, intr.cx, 0, intr.fy, intr.cy, 0, 0, 1], dtype=np.float64)
            info = Info(header=header(t), height=h, width=wd, distortion_model="plumb_bob", d=np.zeros(5),
                        k=k, r=np.eye(3).ravel(), p=np.r_[k[:3], 0, k[3:6], 0, k[6:], 0].astype(np.float64),
                        binning_x=0, binning_y=0, roi=ROI(x_offset=0, y_offset=0, height=0, width=0, do_rectify=False))
            bgra = np.dstack([fr.rgb[..., ::-1], np.full((h, wd), 255, np.uint8)])
            rgb_msg = Image_(header=header(t), height=h, width=wd, encoding="bgra8", is_bigendian=0, step=wd * 4,
                             data=bgra.reshape(-1))
            if profile == "zed_mini":
                d = fr.depth_raw.astype(np.float32) if fr.depth_raw.dtype != np.uint16 else fr.depth_raw * np.float32(0.001)
                dep_msg = Image_(header=header(t + depth_offset_s), height=h, width=wd, encoding="32FC1",
                                 is_bigendian=0, step=wd * 4, data=d.astype("<f4").view(np.uint8).reshape(-1))
            else:
                d = fr.depth_raw if fr.depth_raw.dtype == np.uint16 else np.nan_to_num(fr.depth_raw * 1000).astype(np.uint16)
                dep_msg = Image_(header=header(t + depth_offset_s), height=h, width=wd, encoding="16UC1",
                                 is_bigendian=0, step=wd * 2, data=d.astype("<u2").view(np.uint8).reshape(-1))
            ns = int(t * 1e9)
            w.write(c_inf, ns, ts_store.serialize_cdr(info, Info.__msgtype__))
            w.write(c_rgb, ns, ts_store.serialize_cdr(rgb_msg, Image_.__msgtype__))
            w.write(c_dep, ns + int(depth_offset_s * 1e9), ts_store.serialize_cdr(dep_msg, Image_.__msgtype__))
    return bag_path


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--bag", required=True, help="ROS 2 bag directory (relative path)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--profile", choices=sorted(PROFILES), default="zed_mini")
    ap.add_argument("--every", type=int, default=1, help="keep every N-th synchronized frame")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--max-dt", type=float, default=0.02, help="max RGB/depth stamp difference (s)")
    a = ap.parse_args()
    paths, st = export_frames(a.bag, a.out, a.profile, a.every, a.limit, a.max_dt)
    print(f"rgb={st.rgb} depth={st.depth} synced={st.synced} dropped={st.dropped} → exported {len(paths)} frames to {a.out}")


if __name__ == "__main__":
    main()
