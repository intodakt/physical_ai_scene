"""Build an articulated browser asset from Unitree's G1 URDF and STL meshes.

Usage:
    python -m pip install trimesh
    python tools/build_g1_upper_body.py /path/to/unitree_ros/robots/g1_description

The generated model keeps URDF joint frames and names. Leg branches are omitted; the
table pedestal is created by the viewer. See static/assets/g1/SOURCE.md for attribution.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np
import trimesh
from trimesh.visual import TextureVisuals
from trimesh.visual.material import PBRMaterial


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "demo/twin/static/assets/g1"
URDF = "g1_29dof_with_hand_rev_1_0.urdf"


def values(raw: str | None, default: tuple[float, ...]) -> np.ndarray:
    return np.array([float(x) for x in raw.split()] if raw else default, dtype=float)


def pose(origin: ET.Element | None) -> np.ndarray:
    xyz = values(origin.get("xyz") if origin is not None else None, (0, 0, 0))
    rpy = values(origin.get("rpy") if origin is not None else None, (0, 0, 0))
    matrix = trimesh.transformations.euler_matrix(*rpy, axes="sxyz")
    matrix[:3, 3] = xyz
    return matrix


def build(source: Path, out: Path) -> None:
    root = ET.parse(source / URDF).getroot()
    links = {link.get("name"): link for link in root.findall("link")}
    children: dict[str, list[ET.Element]] = {}
    for joint in root.findall("joint"):
        children.setdefault(joint.find("parent").get("link"), []).append(joint)

    scene = trimesh.Scene()
    scene.graph.update(frame_to="pelvis", frame_from=scene.graph.base_frame, matrix=np.eye(4))
    metadata: dict = {"source_urdf": URDF, "base_link": "pelvis", "joints": {}}
    rendered = []

    def add_link(name: str) -> None:
        link = links[name]
        for i, visual in enumerate(link.findall("visual")):
            mesh_element = visual.find("geometry/mesh")
            if mesh_element is None:
                continue
            path = source / mesh_element.get("filename")
            mesh = trimesh.load(path, force="mesh", process=True)
            if not isinstance(mesh, trimesh.Trimesh) or mesh.is_empty:
                continue
            scale = values(mesh_element.get("scale"), (1, 1, 1))
            if not np.allclose(scale, 1):
                mesh.apply_scale(scale)
            mesh.remove_unreferenced_vertices()
            material_name = (visual.find("material").get("name") if visual.find("material") is not None else "dark")
            if material_name == "white":
                base_color, metallic, roughness = [207, 216, 219, 255], 0.28, 0.46
            else:
                base_color, metallic, roughness = [48, 60, 66, 255], 0.36, 0.52
            mesh.visual = TextureVisuals(material=PBRMaterial(
                name=f"g1_{material_name}", baseColorFactor=base_color,
                metallicFactor=metallic, roughnessFactor=roughness, doubleSided=True,
            ))
            scene.add_geometry(mesh, node_name=f"visual_{name}_{i}", parent_node_name=name,
                               transform=pose(visual.find("origin")))
            rendered.append(name)

        for joint in children.get(name, []):
            child = joint.find("child").get("link")
            if child.startswith(("left_hip", "right_hip")):
                continue
            joint_name = joint.get("name")
            scene.graph.update(frame_to=joint_name, frame_from=name, matrix=pose(joint.find("origin")))
            scene.graph.update(frame_to=child, frame_from=joint_name, matrix=np.eye(4))
            axis = values(joint.find("axis").get("xyz") if joint.find("axis") is not None else None, (0, 0, 1))
            limit = joint.find("limit")
            metadata["joints"][joint_name] = {
                "axis": [float(v) for v in axis], "type": joint.get("type"),
                "lower": float(limit.get("lower")) if limit is not None and limit.get("lower") else 0.0,
                "upper": float(limit.get("upper")) if limit is not None and limit.get("upper") else 0.0,
                "child": child,
            }
            add_link(child)

    add_link("pelvis")
    out.mkdir(parents=True, exist_ok=True)
    model = out / "g1-upper-body.glb"
    model.write_bytes(scene.export(file_type="glb"))
    (out / "g1-upper-body.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")

    repo = source.parents[1]
    license_file = repo / "LICENSE"
    if license_file.exists():
        shutil.copyfile(license_file, out / "LICENSE.unitree")
    try:
        revision = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        revision = "unknown"
    (out / "SOURCE.md").write_text(
        "# Unitree G1 upper-body browser asset\n\n"
        f"Generated from Unitree Robotics `unitree_ros` at revision `{revision}`.\n"
        f"Source: https://github.com/unitreerobotics/unitree_ros/tree/{revision}/robots/g1_description\n"
        f"URDF: `{URDF}`; {len(set(rendered))} visual links. Leg branches omitted.\n\n"
        "The model and derived mesh are under the repository's BSD-3-Clause license "
        "(see `LICENSE.unitree`). The table pedestal and visualization are project additions.\n",
        encoding="utf-8",
    )
    print(f"Built {model} ({model.stat().st_size / 1e6:.1f} MB, {len(set(rendered))} visual links)")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="unitree_ros/robots/g1_description folder")
    parser.add_argument("--out", type=Path, default=OUTPUT)
    args = parser.parse_args()
    build(args.source.resolve(), args.out.resolve())


if __name__ == "__main__":
    main()
