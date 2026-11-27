# Table-mounted robot, camera views, and coordinates

Status: implemented on 27 November 2026. The dashboard runs on port 8602 with the imported recording.

The implementation uses Unitree's hand-equipped G1 geometry at full mesh resolution (6.9 MB GLB), a fixed table mount, arm reach preview, camera and robot presets, locally saved user views, a recorded-camera frustum, object X/Y/Z and yaw, an XY grid, and a live orientation label. The mount currently clears the nearest object by about 17 cm on `my_old_recording` while the right arm can preview a reach to the apple. The recording's desk-plane estimate still leaves physical camera X/Y/yaw unknown; the page lets the presenter enter measured values for that recording. S6's two-dimensional path remains a desk overlay and is never presented as executed G1 motion. `tests/test_twin.py` passes (9 tests).

Concept image: `g1-robot-views-concept.png` (illustrative layout and fixed upper-body robot; the implementation will use the selected model asset).

## Goal

Make the digital twin explain **what is real, what is simulated, where objects are, and which side the viewer sees**. Use a **table-mounted Unitree G1 upper body**, like a robot barista: head, torso, articulated arms and hands, with no legs or walking. Keep the current light Scene Studio layout and S1–S7 behavior.

## What the current project actually knows

- Before this change, the page drew a simple rover or two-link arm in `demo/twin/static/index.html`. They were visual stand-ins. The S6 action path is two-dimensional on the table; it is not a validated G1 whole-body motion plan.
- `ST.camera` is the **virtual camera used to render new twin frames**. It is not the original ZED camera. The recorded-camera transform is in `run_summary.json` as `camera_tf.T_map_camera`, but `/api/source` does not yet expose it.
- The current recording's S1 desk-plane estimate gives a camera height of 0.321 m and downward pitch of 51.8°. The plane alone cannot recover physical x/y or yaw; this recording uses default x/y/yaw. A physical “camera is on the robot's right” claim therefore needs additional calibration.
- Scene coordinates use the map frame in metres: **+X forward, +Y left, +Z up**. The browser converts this to Three.js with `(-y, z, -x)`. Object `twin.xy` is the current editable position; S4 `nodes.pose` is the latest pipeline estimate.

## Screen design

```text
Scene  [Table] [Recorded camera] [Robot overview] [Robot views ▾] [My views ▾]
       ┌───────────────────────────────────────────────────────────┐
       │  3D table + mounted G1              View: robot right    │
       │  X →  Y ←  Z ↑                      [orientation widget] │
       │  object / path / camera markers                           │
       └───────────────────────────────────────────────────────────┘
Selected object   Apple 01   X 0.48 m   Y −0.25 m   Z 0.04 m
                  Twin position · S4 measured position in details
Robot             Table mounted · simulated   Facing +X   Fixed base
```

The direction widget stays visible while orbiting. “Robot right” means the viewing camera is **on the robot's right side**, computed from the avatar's heading. It does not mean screen-right or map-right. A front arrow on the floor and a small labelled axis triad make that relationship visible.

## Implementation steps

### 1. Replace the placeholder robot

- Start from Unitree's official G1 upper-body and dual-arm geometry. The official `g1_dual_arm` variant has no hand joints, so use the hand-equipped G1 variant for its arm and finger chains and remove the leg visuals. Convert and simplify the upper-body meshes into a compact glTF/GLB asset. Keep source attribution and license text with the asset. The current project has no robot model assets.
- Attach the upper body to a **fixed, bolted pedestal on a clear table edge**, away from the recorded object cluster. Choose the mount from candidate edge positions using the objects' footprint boxes: prefer at least **0.15 m clearance** from every object while retaining useful arm reach. Let the presenter adjust the mount if a recording is crowded. Keep measured object positions unchanged. Mount X/Y and heading are simulated scene properties, separate from S6's `agent_start`.
- Start with the arms and hands in a relaxed pose inside the robot's own space, leaving a visible gap to the nearest object. Animate torso yaw (within limits), shoulder, elbow, wrist, and finger open/close only for an explicit reach preview. Use model joint limits and a reachability check. Keep a lightweight fallback silhouette if the asset fails to load.
- Replace the `Mobile / Arm / Off` visual selector with `Mounted G1 / Off`; preserve the S6 path overlay. The base will never translate or walk. Label arm motion **reach preview**, and play it only for targets within the visual arm's workspace. S6's 2D `validated` result remains separate.

### 2. Add named views

- **Table:** today's close orbit for object editing.
- **Recorded camera:** recreate the ZED perspective from S1 `T_map_camera` and the saved camera intrinsics. Add the source-camera frustum to the other views. If only desk-plane calibration exists, label this view **estimated**.
- **Robot overview:** show the mounted upper body, pedestal, desk, and objects at once.
- **Robot front / left / right / rear / top:** presets derived from the avatar's base pose and heading, not fixed screen directions.
- **My views:** keep free orbit and let users save/restore named positions locally for each recording. Preserve Photo/Stylised as an independent appearance switch.
- Compute the live view label from the camera-to-robot vector projected onto the floor and the robot's forward/right vectors. Use a top label for steep elevation. Recompute after orbiting and after avatar heading changes.

### 3. Show positions and calibration honestly

- Draw an optional 0.10 m tabletop grid, labelled X/Y axes, origin marker, and scale bar. Keep this as a layer toggle to avoid cluttering the photo view.
- In the selected-object panel show current twin **X, Y, Z in metres** and yaw; after a drag, update the values immediately. Put the latest S4 measured pose and any difference in Technical details. Use `twin.xy` for the current placement and `nodes.pose` for the pipeline estimate.
- Show the simulated fixed mount X/Y and facing arrow separately from S6's tabletop `agent_start` marker. The mounted robot is not a recorded detection.
- Expose recorded camera transform, intrinsics, and calibration provenance through `/api/source`. Use the actual optical-to-map transform for the recorded view rather than the virtual rendering camera.
- Add an import-time or recording-settings field for **camera x, y, yaw** relative to a marked table origin. Until those values are measured or supplied from a trusted TF, show physical camera side as **unknown**. Height/pitch and virtual left/right labels remain available.

### 4. Validate with a professor-facing demo

- Verify transform math with known map points and test left/right/front/rear classification after changing the camera and robot yaw.
- Check selected-object coordinates before and after a move against `/api/state`; check the S4 readout separately. Verify the camera-frustum direction against the recorded RGB frame.
- Load the optimized upper-body model at full and mobile widths; check mount stability, object clearance, rest-pose separation, joint limits, hand animation, and reachability while keeping scene interaction responsive.
- Run the existing twin tests and browser flows on the real recording and synthetic demo. Show: **mounted G1 → robot right view → facing arrow → select apple and read X/Y → reach preview from fixed base → recorded camera (estimated) → explain calibration status**.

## Reference asset

Unitree's [G1 model description](https://github.com/unitreerobotics/unitree_ros/blob/master/robots/g1_description/README.md) lists both a dual-arm variant and a 29-DoF model with articulated hands. The [repository license](https://github.com/unitreerobotics/unitree_ros/blob/master/LICENSE) is BSD-3-Clause. The table pedestal is our own simulation design, not an official Unitree configuration. Confirm the exact files and attribution when preparing the browser asset.
