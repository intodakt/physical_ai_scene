"""CLI: python -m src.scene_graph.run_scene_graph --objects <S2 *_objects.json> --out <graph.json> [--watch]"""
import argparse
import time
from pathlib import Path

from .engine import SceneGraphEngine, load_objects


def main():
    p = argparse.ArgumentParser(description="S4 scene graph engine")
    p.add_argument("--objects", required=True, help="S2 ObjectInstance3D file (*_objects.json)")
    p.add_argument("--out", default="outputs/scene_graph/scene_graph.json")
    p.add_argument("--desk-top-z", type=float, default=0.0, help="desk surface height in the map frame")
    p.add_argument("--watch", action="store_true", help="re-read the input and rewrite the output every second")
    a = p.parse_args()

    engine = SceneGraphEngine(desk_top_z=a.desk_top_z)
    last = None
    while True:
        mtime = Path(a.objects).stat().st_mtime
        if mtime != last:
            engine.update(load_objects(a.objects)).save(a.out)
            g = engine.export()
            print(f"{len(g['nodes'])} nodes, {sum(e['end_time'] is None for e in g['edges'])} active edges -> {a.out}")
            last = mtime
        if not a.watch:
            return
        time.sleep(1.0)


if __name__ == "__main__":
    main()
