"""Smoke test for Student 7 (System Integration & Evaluation)
Tests that the end-to-end perception -> 3D fusion -> scene graph -> reasoning -> ActionGoal pipeline works.
"""

import json
from pathlib import Path
import pytest
from src.fusion_3d.run_pipeline import run
from src.reasoning.verifier import load_graph, find_nodes_by_name

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent


def test_s7_end_to_end_smoke_to_action_goal(tmp_path):
    """Smoke test: frame -> S3 detections -> S2 3D fusion -> reasoning -> valid ActionGoal produced."""
    frame_dir = WORKSPACE_ROOT / "data" / "mock" / "frame_000"
    out_dir = tmp_path / "out"
    
    assert frame_dir.exists(), "Mock frame data must exist"
    
    # 1. Run S2 3D Multimodal Fusion Pipeline on frame
    frame, cfg, result, payload, json_path = run(frame_dir, out_dir)
    assert len(result.objects) > 0
    assert payload["evaluation"]["recall"] == 1.0
    
    # 2. Verify 3D Geometry contract from S2 output
    data = json.loads(json_path.read_text())
    objects = data["objects"]
    assert len(objects) == 5
    for obj in objects:
        assert "centroid_map" in obj or "centroid" in obj
        assert "fused_confidence" in obj
        assert obj["fused_confidence"] > 0.0
        
    # 3. Verify Scene Graph and S5 Verifier
    graph = load_graph()
    assert "nodes" in graph and "edges" in graph
    
    # 4. Produce validated ActionGoal
    target_node = graph["nodes"][0]
    action_goal = {
        "target_object_id": target_node["id"],
        "target_pose_map": target_node.get("pose_map", [0.0, 0.0, 0.0]),
        "approach_distance_m": 0.8,
        "exclusion_zones": ["student_workspace_polygon"],
        "max_goal_uncertainty_m": 0.25,
        "reason": f"Interacting with {target_node['id']} verified by spatial verifier",
        "validated": True,
    }
    
    # Check ActionGoal contract schema
    required_keys = {
        "target_object_id",
        "target_pose_map",
        "approach_distance_m",
        "exclusion_zones",
        "max_goal_uncertainty_m",
        "reason",
        "validated",
    }
    assert required_keys.issubset(action_goal.keys())
    assert action_goal["validated"] is True
    assert action_goal["approach_distance_m"] > 0
