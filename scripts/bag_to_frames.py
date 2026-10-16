"""Export RGB / depth / intrinsics frames from a rosbag2 .db3 (ZED topics) in the S1 frame layout
that S2 expects: <out>/frame_NNN/{rgb.png, depth.npy, camera_intrinsics.yaml, frame_meta.json}.

    python scripts/bag_to_frames.py S1_static_bag_0.db3 --out data/real --frames 60 130 200

No ROS install needed: reads the sqlite file and decodes the CDR Image / CameraInfo messages itself.
Needs: numpy, opencv-python-headless.
"""
import argparse, json, sqlite3, struct
from pathlib import Path

import cv2
import numpy as np

# --- minimal CDR (little endian) decoding ---
class R:
    def __init__(s,b): s.b=b; s.o=4   # skip 4-byte encapsulation header
    def al(s,n): s.o += (-(s.o-4))%n
    def u32(s): s.al(4); v=struct.unpack_from('<I',s.b,s.o)[0]; s.o+=4; return v
    def i32(s): s.al(4); v=struct.unpack_from('<i',s.b,s.o)[0]; s.o+=4; return v
    def f64(s): s.al(8); v=struct.unpack_from('<d',s.b,s.o)[0]; s.o+=8; return v
    def u8(s): v=s.b[s.o]; s.o+=1; return v
    def str(s): n=s.u32(); v=s.b[s.o:s.o+n-1].decode(); s.o+=n; return v
def image(b):
    r=R(b); r.i32(); r.u32(); fid=r.str(); h=r.u32(); w=r.u32(); enc=r.str(); r.u8(); step=r.u32(); n=r.u32()
    return dict(frame_id=fid,h=h,w=w,enc=enc,step=step,data=b[r.o:r.o+n])
def caminfo(b):
    r=R(b); r.i32(); r.u32(); fid=r.str(); h=r.u32(); w=r.u32(); model=r.str()
    n=r.u32(); D=[r.f64() for _ in range(n)]; K=[r.f64() for _ in range(9)]
    return dict(frame_id=fid,h=h,w=w,model=model,D=D,K=K)
def tf(b):
    r=R(b); n=r.u32(); out=[]
    for _ in range(n):
        r.i32(); r.u32(); parent=r.str(); child=r.str(); t=[r.f64() for _ in range(3)]; q=[r.f64() for _ in range(4)]
        out.append((parent,child,t,q))
    return out


RGB, DEPTH, INFO = "/zed/zed_node/rgb/image_rect_color", "/zed/zed_node/depth/depth_registered", "/zed/zed_node/rgb/camera_info"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("bag"); ap.add_argument("--out", default="data/real")
    ap.add_argument("--frames", type=int, nargs="+", default=[0])
    a = ap.parse_args()
    con = sqlite3.connect(f"file:{a.bag}?mode=ro", uri=True)
    tid = {n: i for i, n in con.execute("select id, name from topics")}
    get = lambda topic, i: con.execute("select timestamp, data from messages where topic_id=? "
                                       "order by timestamp limit 1 offset ?", (tid[topic], i)).fetchone()
    K = caminfo(get(INFO, 0)[1])["K"]
    for i in a.frames:
        ts, rb = get(RGB, i); _, db = get(DEPTH, i)
        rgb, dep = image(rb), image(db)
        h, w = rgb["h"], rgb["w"]
        d = Path(a.out) / f"frame_{i:03d}"; d.mkdir(parents=True, exist_ok=True)
        ch = 4 if rgb["enc"] in ("bgra8", "rgba8") else 3
        cv2.imwrite(str(d / "rgb.png"), np.frombuffer(rgb["data"], np.uint8).reshape(h, w, ch)[:, :, :3])
        depth = np.frombuffer(dep["data"], np.float32).reshape(dep["h"], dep["w"]).copy()
        depth[~np.isfinite(depth)] = 0
        np.save(d / "depth.npy", depth)
        (d / "camera_intrinsics.yaml").write_text(
            "width: %d\nheight: %d\nfx: %s\nfy: %s\ncx: %s\ncy: %s\n" % (w, h, K[0], K[4], K[2], K[5]))
        (d / "frame_meta.json").write_text(json.dumps({"timestamp": ts / 1e9, "frame_id": rgb["frame_id"]}, indent=1))
        print("wrote", d)


if __name__ == "__main__":
    main()
