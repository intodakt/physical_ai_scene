# G1 dashboard redesign proposal

Status: implemented on `codex/light-scene-studio` and running at `http://127.0.0.1:8602/`.

## Scope

Redesign the **latest virtual twin only**: `demo/twin/static/index.html` from the `twin-photo-objects` branch in PR #25, the version used in today's recording demo. Keep its Photo/Stylised switch, label correction, and all existing controls. The Streamlit pages are outside this proposal.

## References

- [Viam 3D scene interface](https://docs.viam.com/visualization/3d-scene/the-3d-scene-interface/): a large viewport with an object list, selected-object details, and a compact toolbar. Use this as the main layout pattern.
- [Foxglove visualization](https://docs.foxglove.dev/docs/visualization): separate image, 3D, and diagnostic panels; sidebars hold secondary information. Use this as the model for progressive disclosure and recorded-data inspection.
- [Foxglove layouts](https://docs.foxglove.dev/docs/visualization/layouts): task-specific arrangements. Use one clean demonstration view and one detailed diagnostics view, rather than showing every module at once.

These are interaction references. Use original G1 colors, type, artwork, and code; do not copy their branding or assets.

## Visual direction

- Light, calm instrument UI: `#F5F7F8` page, white panels, `#202A35` text, `#256D7B` active controls. Green means verified; amber means a blocked or uncertain action.
- Standard sans-serif typography, restrained borders, no glow, gradients, ornamental chips, or emoji controls.
- A larger 3D scene in the center. Left: objects and scenarios. Right: question, verified answer, action, and selected-object details.
- Keep essential status in view; place JSON, stage latency, S4 relations, and per-frame logs in a collapsible **Technical details** area.
- At narrow widths, stack the scene first, then answer, then objects and diagnostics. Controls must remain reachable by keyboard and touch.

## Shorter product copy

| Current | Proposed |
| --- | --- |
| G1 Virtual Table | Scene Studio |
| Built from this recording | Source |
| Objects on the table | Objects |
| Backup scenarios | Scenarios |
| Let time pass | Next frame |
| Reset to recording | Reset table |
| S5 answer → S6 action | Answer & action |
| What the pipeline saw | Camera frame |
| What the language model understood (S5 JSON) | Parsed question |

Remove the long pipeline explanation under the object list and the latency explanation below the rendered frame. Put these in a short help or technical details view. Keep S1–S7 names in diagnostics and presentations, where they matter.

## Implementation

1. Added shared color, type, spacing, button, tab, and status styles in `demo/twin/static/scene-studio.css` without changing the twin API.
2. Rearranged the UI into the three-column scene layout while retaining move, hide, show, rotate, rename, reset, scenarios, question, planner, robot, obstacle, Photo/Stylised, and layer controls.
3. Moved logs, scene relations, latency, and frame diagnostics behind **Technical details**. The verified answer and action result remain separate.
4. Ran the latest recording (`my_old_recording`, 40 imported frames, seven twin objects), checked desktop and mobile layouts, exercised key browser interactions, and ran the twin test suite.

The imported recording rendered its thin objects as flat photo planes with the current `twin-photo-objects` code. No engine change was needed for this UI update.

## Preview

`scene-studio-light-preview.html` is the original static concept. The running implementation uses the existing 3D renderer and recording data. Browser captures are in `output/playwright/`.
