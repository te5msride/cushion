# Component reference

All components are Rhino 8 **Script components** (Python 3). Create the
component, paste the script from `gh/components/`, then add the inputs/
outputs below (right-click input → rename, set *Type hint* and
*item/list access*). Names must match exactly — the scripts refer to
them as variables.

General rules:

* Inputs marked **object** must have Type hint = **No Type Hint** —
  they carry Python dicts between components (wrapped in
  `GH_ObjectWrapper`; a str/other hint destroys them).
* Every path input tolerates stray quotes/whitespace.
* `repo` = path to the sofa-gh folder. Needed on every component that
  imports the package (Region/Scene/Run/Results) while running from
  pasted scripts; the published plugin will bundle it.

---

## SofaBody — deformable FEM body

| Input | Hint | Access | Notes |
|---|---|---|---|
| geo | Geometry | item | closed solid (Brep preferred → STEP → gmsh) |
| volumeFile | str | item | alternative to geo: `.vtk` used as-is (pre-meshed), `.step`/`.stl` gets gmsh-meshed |
| name | str | item | node name, unique per body (default `actuator1`) |
| E | float | item | effective Young's modulus, kPa (MU 1.0×: 18.34) |
| nu | float | item | Poisson ratio (default 0.4) |
| mass | float | item | total mass, kg |
| meshSize | float | item | gmsh MeshSizeFactor (MU jvolume: 0.22) |
| cavities | *No Type Hint* | list | from SofaCavity |
| tendons | *No Type Hint* | list | from SofaTendon |
| regions | *No Type Hint* | list | from SofaRegion |
| fixations | Box | list | nodes inside are clamped (RestShapeSprings 1e12) |
| monitorPts | Point3d | list | tracked points; snapped to closest mesh nodes at start; required for SofaResults trajectories |
| collisionGeo | Geometry | item | collision surface; only wire when contact matters (costs compute) |
| visualGeo | Geometry | list | display-only surfaces (e.g. lattice), barycentric-mapped |
| visualFiles | str | list | display-only `.stl` paths, used as-is |
| visualFaces | int | item | decimate visualGeo to this face count on export (0 = off) |

Output: `body` (object).

## SofaCavity — pneumatic chamber

| Input | Hint | Access | Notes |
|---|---|---|---|
| geo | Geometry | item | closed surface fully inside the body |
| meshFile | str | item | alternative: existing closed `.stl` |
| channel | int | item | input.csv column driving it (1-based) |
| name | str | item | default `cavity_<channel>` |

Output: `cavity` (object). Pressure in kPa; the ×dt scaling SOFA's
SurfacePressureConstraint expects is handled by the controller.

## SofaTendon — cable actuation

| Input | Hint | Access | Notes |
|---|---|---|---|
| pts | Point3d | list | ordered routing points, all inside the body (Divide Curve → pts) |
| channel | int | item | input.csv column |
| name | str | item | default `cable_<channel>` |
| valueType | str | item | `displacement` (mm, default) or `force` (mN) |
| pullPoint | Point3d | item | optional external anchor (motor/pulley) |

Output: `tendon` (object).

## SofaRegion — locally stiffened sub-region

Three definition modes: ready closed mesh (`geo`), auto-shell
(`surface` + `thickness` — builds a closed hollow shell via mesh
offset; this is how "membrane with no inlet" geometry that GH cannot
represent as a Brep is made), or existing file (`meshFile`).

| Input | Hint | Access | Notes |
|---|---|---|---|
| geo | Geometry | item | closed mesh enclosing tets to stiffen |
| surface | Geometry | item | base surface for auto-shell |
| thickness | float | item | shell offset, mm |
| meshFile | str | item | existing closed `.stl` |
| name | str | item | |
| E | float | item | overlay modulus, kPa (added on top of body FEM; MU membrane 2000, sensor 5000) |
| nu | float | item | default 0.4 |
| repo | str | item | needed for auto-shell mode |

Outputs: `region` (object), `shell` (preview mesh, auto-shell mode).

Mechanism: SOFA `MeshROI` selects the body tets inside the closed mesh
and an overlay `TetrahedronFEMForceField` adds stiffness — no remeshing,
regions never exist as separate bodies.

## PressureProfile — actuation keyframes

| Input | Hint | Access | Notes |
|---|---|---|---|
| channel | int | item | must be wired |
| times | float | list | seconds |
| values | float | list | kPa (cavity) / mm or mN (tendon) |

Output: `profile` (object). Linear interpolation, resampled at 100 Hz
into input.csv. Value held at nearest endpoint outside the keyframe span.

## SofaPreview — scene preview in the Rhino viewport

Reads the written project folder and rebuilds everything as Rhino
geometry — including file-path meshes that never existed in GH and the
actual gmsh-meshed volume surface (meshing QA). Wire outputs through
Custom Preview components with per-role colors.

| Input | Hint | Access | Notes |
|---|---|---|---|
| scenePath | str | item | from SofaScene (write=True) |
| repo | str | item | |
| refresh | bool | item | |

Outputs: `volumes` (FEM surfaces), `cavities`, `regions`, `targets`
(Mesh lists), `monitorPts` (points), `fixBoxes` (boxes), `info`.

## SofaTarget — rigid interaction object

| Input | Hint | Access | Notes |
|---|---|---|---|
| geo | Geometry | item | closed surface, placed in world coords |
| meshFile | str | item | alternative: existing closed `.stl` |
| name | str | item | default `target1` |
| mass | float | item | kg (default 0.01) |

Output: `target` (object) → SofaScene.targets. Collision models named
`target` (usable in contactRules). Body needs `collisionGeo` wired and
usually a floor. v0 approximation: unit rotational inertia.

## SofaShape — deformed shape playback

Requires `exportShape` > 0 on SofaBody at scene-write time (exports the
volume mesh every N steps; N=10 at dt=0.01 → 10 frames/s of sim time).

| Input | Hint | Access | Notes |
|---|---|---|---|
| scenePath | str | item | |
| bodyName | str | item | |
| frame | int | item | index; −1/empty = last; wire slider 0..nFrames−1 |
| repo | str | item | |
| refresh | bool | item | |

Outputs: `mesh` (deformed surface at that frame), `nFrames`, `time`
(s), `info`.

## SofaScene — project writer

| Input | Hint | Access | Notes |
|---|---|---|---|
| bodies | *No Type Hint* | list | |
| profiles | *No Type Hint* | list | |
| targets | *No Type Hint* | list | optional, from SofaTarget |
| camPos | Point3d | item | optional SOFA camera position |
| camTarget | Point3d | item | optional camera look-at (both needed) |
| projDir | str | item | output folder, local disk (one per design) |
| repo | str | item | |
| dt | float | item | default 0.01 s |
| gravityZ | float | item | default −9810; use 0 while testing |
| floorZ | float | item | empty = no floor; value = static plane at that z |
| floorSize | float | item | default 400 mm |
| contactRules | str | item | RuleBasedContactManager rules (grasping); empty = default friction contact |
| write | bool | item | toggle True to (re)write |

Outputs: `scenePath` (str), `info` (str — read it). Writes
`meshes/`, `scene.json`, `input.csv`, copies `runtime/scene.py` +
`controller.py`. Note: `scenePath` is only emitted while `write` is
True.

## SofaRun — launcher

| Input | Hint | Access | Notes |
|---|---|---|---|
| scenePath | str | item | from SofaScene |
| sofaRoot | str | item | SOFA folder (or set SOFA_ROOT env) |
| repo | str | item | |
| gui | bool | item | True = SOFA window (press **Animate**); False = headless batch (blocks GH until done) |
| run | bool | item | toggle True to launch |

Output: `status` (str). Log written to `<projDir>/runsofa.log`.

## SofaResults — read back

| Input | Hint | Access | Notes |
|---|---|---|---|
| scenePath | str | item | |
| bodyName | str | item | must match SofaBody name |
| repo | str | item | |
| refresh | bool | item | toggle to re-read |

Outputs: `info` (read first), `times`, `points` (DataTree — branch per
frame, items = tracked points), `lastPts` (final frame), `pTimes`,
`pressures` (DataTree — branch per channel).

Typical use: `points` → Tree Branch + slider = scrub motion; Flip
Matrix → Polyline = trajectories; `pressures` → Quick Graph.
