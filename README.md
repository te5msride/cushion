# Cushion

**Soft robotics simulation in Grasshopper, powered by [SOFA](https://www.sofa-framework.org/).**

Define a deformable body, its pneumatic cavities and/or tendons, and an
actuation schedule as Grasshopper components; Cushion meshes the
geometry, writes a runnable SOFA scene, launches the simulation, and
pulls trajectories, forces, and deformed shapes back into Grasshopper.

*Developed by Trevor Exley and Anderson Brazil Nardin.*

Scene structure follows the Monolithic Unit soft-robotics pipeline
(Exley, Nardin, Trunin, Cafiso, Beccai — [arXiv:2511.13120](https://arxiv.org/abs/2511.13120)):
corotational tet FEM, homogenized lattice material, MeshROI-based local
stiffening, SoftRobots pressure/cable constraints.

```
GH geometry ──► STL/STEP ──► gmsh tets ──► scene.json + input.csv
                                              │
      GH points/curves ◄── monitor data ◄── runSofa (GUI or batch)
```

## Status

Working prototype (v0.1). Tested on Windows 11 + macOS with Rhino 8 and
SOFA v24.06. Interface may change. License TBD (pending institutional
check) — do not redistribute yet.

## Requirements

* **Rhino 8** (Grasshopper Script components, Python 3 mode)
* **SOFA v24.06 binaries** with SofaPython3, SoftRobots, STLIB,
  SofaValidation plugins (all included in the official release bundle)
* **Python 3.10** on the system (SofaPython3 v24.06 is built against it)
  with `numpy`
* Internet on first run (Rhino auto-installs the `gmsh` Python package)

Full platform-specific steps: [docs/INSTALL.md](docs/INSTALL.md).

## Quickstart (inflate a cylinder)

1. Install per [docs/INSTALL.md](docs/INSTALL.md); clone/copy this repo.
2. In Grasshopper, create Script components from `gh/components/*.py`
   (paste script, add inputs/outputs per the header comment —
   see [docs/COMPONENTS.md](docs/COMPONENTS.md) for exact signatures).
3. Model a solid cylinder (r 15, h 100 mm) → `SofaBody.geo`.
   Smaller closed cylinder inside → `SofaCavity.geo`, channel 1.
4. Box around one end cap → `SofaBody.fixations`; a few points along
   the axis → `SofaBody.monitorPts`.
5. `PressureProfile`: channel 1, times `[0, 1.0]`, values `[0, 20]` (kPa).
6. `SofaScene`: wire body + profile, set `projDir` (local disk folder),
   `repo` (this folder), `gravityZ` 0, toggle `write` → True.
7. `SofaRun`: `sofaRoot` = your SOFA folder, `gui` True, `run` → True.
   Press **Animate** in the SOFA window.
8. `SofaResults`: wire `scenePath` + `bodyName`, toggle `refresh` →
   trajectories return as a DataTree (branch per frame).

## Components

| Component | Role |
|---|---|
| `SofaBody` | Deformable FEM body: solid + material + fixations + monitor points |
| `SofaCavity` | Pneumatic chamber (SurfacePressureConstraint), channel-driven |
| `SofaTendon` | Cable/tendon path (CableConstraint), displacement- or force-driven |
| `SofaRegion` | Locally stiffened sub-region (membrane/sensor), closed mesh or auto-shell |
| `PressureProfile` | Actuation keyframes for one channel (linear-interp, resampled) |
| `SofaTarget` | Rigid interaction object (graspable target, obstacle) |
| `SofaScene` | Writes the runnable project folder (meshes, scene.json, input.csv); optional camera + targets |
| `SofaRun` | Launches runSofa (GUI or headless batch) |
| `SofaResults` | Parses trajectories + actuation history back into GH |
| `SofaShape` | Rebuilds the deformed body surface at any exported frame |
| `SofaPreview` | Rebuilds the whole written scene (incl. file-path meshes and the gmsh volume) as Rhino geometry |

Details, input tables, modeling notes: [docs/COMPONENTS.md](docs/COMPONENTS.md).

## Units & conventions

mm / kPa / kg / s everywhere; gravity −9810 mm/s² in z (SOFA has no
intrinsic up-axis — the gravity vector defines it; geometry passes
Rhino→SOFA 1:1, no transform). Rhino document units must be millimeters.

Young's moduli are effective values: for lattice bodies use the
homogenized modulus (Monolithic Unit 1.0×: 18.34 kPa); heavy lattice
geometry goes into `visualGeo` only — it is displayed (barycentric-
mapped), never meshed or simulated.

## Repo layout

```
sofagh/          pure-Python core (no Rhino): meshing, project writer,
                 runner, results parsers — also usable from plain Python
sofagh/runtime/         generic SOFA scene + controller (copied into projects)
gh/ghcommon.py   RhinoCommon helpers (STL/STEP export, shell offset)
gh/components/   the Grasshopper component scripts
docs/            install, component reference, troubleshooting
examples/        walkthroughs incl. Monolithic Unit reproduction
```

Any written project folder is standalone:
`python -m sofagh.runner path/to/project/scene.py [--batch]`.

## Roadmap

* `.ghuser` component set → ScriptEditor project (`.rhproj`) → compiled
  `.gha` via Yak
* Tier 2: live bridge (headless SOFA loop streaming node positions into
  the Rhino viewport)
* Rigid grasp targets, contact rules component
* Homogenization helper (virtual compression test → effective modulus)
* Full deformed-mesh playback (VTK export)
