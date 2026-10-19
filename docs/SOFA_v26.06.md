# Cushion on SOFA v26.06 — Install & Use

This branch makes Cushion run on **SOFA v26.06** (still runs on v24.06). The
Grasshopper components are unchanged from `master`; only the Python runtime
(`sofagh/runtime/scene.py`, `controller.py`) changed. **Lightly tested on
v26.06 — expect rough edges. Please report issues.**

## Fresh install (the one that actually works)

The compiled plugin **bundles its own copy of the Python runtime** — so you
must install the **v26.06 package** below, not the old food4Rhino one. Pointing
a `Repository` input at a checkout does **not** override the bundled runtime
when the compiled `.gha` is installed.

1. **SOFA v26.06** installed, with SofaPython3, SoftRobots, STLIB.
2. **numpy into SOFA's embedded Python** (Python 3.12 in the macOS bundle):
   ```
   python3.12 -m pip install --target \
     "/Applications/SOFA_v26.06.00_MacOS/plugins/SofaPython3/lib/python3/site-packages" numpy
   ```
   (Windows/Linux: install numpy into the Python that `runSofa` reports in its
   startup log: `[SofaPython3] Initializing with python version 3.x`.)
3. **gmsh** into Rhino's CPython (for tet-meshing): in Rhino, a Python 3 Script
   component with `# r: gmsh` triggers the install (needs internet, ~1 min).
4. **Install the Cushion v26.06 plugin** — `dist/cushion-0.2.0-any-any.yak`:
   - Rhino → `_PackageManager` → gear/▾ → *Install from file…* → pick the `.yak`, **or**
   - CLI: `"/Applications/Rhino 8.app/Contents/Resources/bin/yak" install --source <path-to>/dist cushion`
   - **Uninstall any older Cushion first** so the old runtime can't shadow it.
5. **Restart Rhino** after installing.

Verify a generated project uses the v26.06 runtime:
```
grep -c "_load_plugins" <project dir>/scene.py
```
`3` = v26.06 runtime. `0` = old 24.06 runtime (wrong package still installed).

### If you get the OLD runtime after installing (important on machines that ever had an older Cushion)

Rhino caches a plugin's Python at `~/.rhinocode/libs/<hash>/` and does **not**
refresh that cache when you reinstall a package that reuses the same hash
folder — and uninstalling the package never deletes it. So a machine that
previously had an older Cushion keeps running the old runtime even after you
install this one. Symptoms:
- `scene.py` tries to load `SofaLoader`, `SofaSimpleFem`, `SofaEngine`, … (the
  monolithic plugins removed in SOFA v24.12), or
- teleop throws `OSError: [WinError 10038] ... not a socket`.

Fix (Windows), with **Rhino fully closed**: unzip `cushion_fix.zip` (keeps
`fix_cushion_runtime.ps1` next to a `sofagh/` folder) and run
```
powershell -ExecutionPolicy Bypass -File fix_cushion_runtime.ps1
```
It force-overwrites the cached runtime with the correct one, prints `PORT` for
each cache folder, then: start Rhino, **regenerate the scene** (SofaScene
`write=True`) so the project picks up the fixed `controller.py`. The same script
lives in `scripts/` here; pass `-YakPath "<path>\cushion-0.2.0-any-any.yak"` if
no Cushion is installed yet.

## Run

Use `-g imgui` (the full GUI); `-g glfw` is a bare viewer, `-g batch` is headless.
```
export SOFA_ROOT=/Applications/SOFA_v26.06.00_MacOS
"$SOFA_ROOT/bin/runSofa" -g imgui -l SofaPython3 -a scene.py
```
Try an example (`examples/simple_gripper.gh`, `continuum_robot.gh`): set
`write=True` on SofaScene, `run=True` on SofaRun.

## What changed for v26.06

- **Plugins:** legacy monolithic names (`SofaLoader`, `SofaConstraint`, …) were
  removed in v24.12 → granular `Sofa.Component.*` are loaded, each independently
  (a missing one is skipped, not fatal).
- **Renamed components** (try/except fallback, works on both versions):
  `GenericConstraintSolver`→`BlockGaussSeidelConstraintSolver`,
  `DefaultPipeline`→`CollisionPipeline`, `DefaultContactManager`→`CollisionResponse`.
- **Monitor** (`SofaValidation`) isn't in the v26.06 bundle → guarded
  (point-tracking export off on 26.06). The `SofaValidation not found` and
  `MousePosition` lines in the log are benign.
- **Camera:** v26.06 GUIs ignore the old Qt view file → the scene always adds an
  `InteractiveCamera`, auto-framed if none is given.

## Interactive teleop — TERMINAL ONLY

A keyboard teleop is built in to drive a body's base (translate + rotate) and
cavity pressure live. **The v26.06 GUIs do not forward keyboard to Python, and a
Rhino/GH-launched runSofa has no terminal — so teleop only works when you launch
runSofa yourself from a terminal and type the keys IN THE TERMINAL.** A run
started from the GH `SofaRun` button runs the scripted protocol only, no live
input.

```
export SOFA_ROOT=/Applications/SOFA_v26.06.00_MacOS
cd <project dir>
CUSHION_TELEOP=1 "$SOFA_ROOT/bin/runSofa" -g imgui -l SofaPython3 -a scene.py
```
Keys (type in the terminal, then Enter): `I`/`K` pressure, `W`/`S` insert
(translate base), `A`/`D` **rotate base**, `X` reset. Env: `CUSHION_NO_PROTOCOL=1`
free-drive (drop the scripted protocol); `CUSHION_P_STEP` / `CUSHION_INS_STEP`
/ `CUSHION_TW_STEP` set step sizes.

A `teleop` block in `scene.json` sets which body + axis/pivot/steps:
```json
"teleop": {
  "body": "<body name>", "channel": 1,
  "pressure_step": 1.0, "pressure_max": 50.0,
  "insert_step": 1.0, "twist_step": 5.0,
  "axis": [0,0,1], "pivot": [x,y,z]
}
```

## Soft body attached to a rigid frame + rotating the domain

- **Attach a soft (FEM) body to a rigid frame:** `SofaBody` `fixations` input
  (a box) clamps those nodes rigid; the rest deforms.
- **Rotate the domain (interactive):** teleop `A`/`D` rotates the chosen body's
  base about `axis` through `pivot` (set in the `teleop` block). Terminal only.
- **Rotate the domain (scripted):** the stock `SofaProtocol` keyframes
  TRANSLATION only. To script rotation, extend it with the runtime's
  `controller._transform_rest(dofs, translate, angle, axis, pivot)` (the same
  helper the teleop uses) and apply rotation keyframes in
  `controller.onAnimateBeginEvent` the way the translation `offsets` are applied.

## Caveat

Research tool, lightly tested on v26.06. When a scene errors, run from a terminal
(`-g batch -n 5`) to see the message — GH hides it. If a body segfaults with
`TetrahedronFEMForceField ... no tetrahedric topology`, the geometry isn't a
closed solid (Rhino `ShowEdges` → zero naked edges; or set SofaBody `hollow=False`).
