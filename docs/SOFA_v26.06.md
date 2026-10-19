# Cushion on SOFA v26.06

Cushion ported to **SOFA v26.06** (still runs on v24.06). Only the runtime
(`sofagh/runtime/scene.py`, `sofagh/runtime/controller.py`) changed — the
Grasshopper components are unchanged from `master`. **Lightly tested on v26.06;
expect rough edges.** Please report issues.

## What breaks on v26.06 (and is handled here)

- **Plugin names.** The legacy monolithic plugins (`SofaLoader`, `SofaConstraint`,
  `SofaOpenglVisual`, …) were removed in v24.12. The scene now loads the granular
  `Sofa.Component.*` plugins, each **independently** (a name a given build lacks is
  skipped with a log note, not fatal).
- **Renamed components.** Resolved via try/except fallback so one scene runs on
  both 24.06 and 26.06:
  - `GenericConstraintSolver` → `BlockGaussSeidelConstraintSolver` (v25.12)
  - `DefaultPipeline` → `CollisionPipeline` (alias gone v24.12)
  - `DefaultContactManager` → `CollisionResponse` (alias gone v24.12)
- **Monitor.** The `SofaValidation` plugin / `Monitor` component is not in the
  v26.06 binary bundle → guarded (point-tracking export is disabled on 26.06, still
  works on 24.06).
- **Camera.** The v26.06 GUIs (imgui/glfw) ignore the old Qt `.qglviewer.view`
  file, so the scene **always adds an `InteractiveCamera`**, auto-framed to the
  geometry when `scene.json` has none.
- **GUI.** Use `-g imgui` (full GUI). `-g glfw` is a bare viewer; `-g batch` is
  headless.

## Setup (v26.06, macOS)

SOFA v26.06 with SofaPython3, SoftRobots, STLIB. numpy must be in **SOFA's**
embedded Python (3.12 in the macOS bundle):

```
python3.12 -m pip install --target \
  "/Applications/SOFA_v26.06.00_MacOS/plugins/SofaPython3/lib/python3/site-packages" numpy
```

Run a generated project:

```
export SOFA_ROOT=/Applications/SOFA_v26.06.00_MacOS
"$SOFA_ROOT/bin/runSofa" -g imgui -l SofaPython3 -a scene.py
```

## Interactive teleop (drive a body base + cavity pressure by keyboard)

A small teleop is built into the controller for interactively moving a body's
base (**translate + rotate**) and setting cavity pressure.

- **Enable:** set `CUSHION_TELEOP=1` before launching, or add a `teleop` block to
  `scene.json` (below).
- **Key forwarding:** the v26.06 GUIs do **not** forward keyboard to Python.
  Launch runSofa **from a terminal** and type the keys **in the terminal + Enter**
  (not in the SOFA window):

```
export SOFA_ROOT=/Applications/SOFA_v26.06.00_MacOS
CUSHION_TELEOP=1 "$SOFA_ROOT/bin/runSofa" -g imgui -l SofaPython3 -a scene.py
```

- **Keys** (type in the terminal, then Enter): `I`/`K` pressure up/down,
  `W`/`S` insert (translate base), `A`/`D` twist (rotate base), `X` reset.
- **Step sizes** via env: `CUSHION_P_STEP`, `CUSHION_INS_STEP`, `CUSHION_TW_STEP`.
  `CUSHION_NO_PROTOCOL=1` disables any scripted protocol so you free-drive.

`teleop` block (optional, in `scene.json`; sets axis/pivot/steps and which body):

```json
"teleop": {
  "body": "<body name>",
  "channel": 1,
  "pressure_step": 1.0, "pressure_min": 0.0, "pressure_max": 50.0,
  "insert_step": 1.0, "twist_step": 5.0,
  "axis": [0, 0, 1], "pivot": [x, y, z]
}
```

## Soft body attached to a rigid body + rotating the domain

(Your stated use case.) With the stock components:

- **Attach a soft (FEM) body to a rigid frame:** use the body's **fixation box**
  (`SofaBody` `fixations` input) to clamp the proximal region — those nodes are
  held rigid; the rest of the body deforms. A rigid interaction object is a
  `SofaTarget`.
- **Rotate the domain (interactive):** the teleop `A`/`D` **twist** rotates the
  chosen body's base (its rest frame) about `axis` through `pivot` — set them in
  the `teleop` block above, pick `body`. Insert (`W`/`S`) translates it.
- **Rotate the domain (scripted):** the stock `SofaProtocol` component keyframes
  **translation only**. To add scripted rotation, extend it: the runtime already
  has a rest-frame transform that rotates about an axis/pivot
  (`controller._transform_rest(dofs, translate, angle, axis, pivot)`), used by the
  teleop. Wire rotation keyframes through `SofaProtocol` / `scene.json` and apply
  them in `controller.onAnimateBeginEvent` the same way the translation `offsets`
  are applied there. Interactive teleop twist is the quick path; protocol rotation
  is the scripted path.

## Caveat

Research tool, lightly tested on v26.06. If a component errors, run from a
terminal (`-g batch -n 5`) to see the message — GH hides it.
