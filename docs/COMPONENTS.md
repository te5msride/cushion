# Component reference

All components are Rhino 8 **Script components** (Python 3). Create the
component, paste the script from `gh/components/`, then add the inputs/
outputs below (right-click input → rename, set *Type hint* and
*item/list access*). Names must match exactly — the scripts refer to
them as variables.

General rules:

* Components pass data to each other as **token strings** (e.g.
  `sofagh::cavity::3::140...`) referencing a shared in-session registry —
  immune to Grasshopper type marshalling. Any type hint works on these
  inputs (`str` or none). Tokens are session-bound: after restarting
  Rhino, recompute upstream components (the consuming component will
  say so explicitly).
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
| gmshOpts | str | list | extra gmsh options as `key = value` lines (defaults MU-matching): friendly keys/names (`algo2d = MeshAdapt`, `algo3d = Delaunay`, `smoothing = 1`, `sizeFactor = 0.5`) or raw gmsh names (`Mesh.Algorithm = 1`); overrides meshSize if it sets MeshSizeFactor |
| cavities | str/none | list | from SofaCavity |
| tendons | str/none | list | from SofaTendon |
| regions | str/none | list | from SofaRegion |
| fixations | Box | list | nodes inside are clamped (RestShapeSprings 1e12) |
| hollow | bool | item | cavities become internal voids of the tet mesh (default True — the physical membrane); False = solid body, pressure on an internal surface |
| orient | Transform | item | rigid placement of the WHOLE body assembly (geo, cavities, tendons, fixations, monitor points) — design flat, wire e.g. an Orient component's X output; rotation+translation only |
| rotate | Vector3d | item | OR euler degrees about world X,Y,Z (applied X→Y→Z, SOFA convention); ignored if orient wired |
| translate | Vector3d | item | translation applied after rotate |
| monitorPts | Point3d | list | tracked points; snapped to closest mesh nodes at start; required for SofaResults trajectories |
| collisionGeo | Geometry | item | collision surface; only wire when contact matters (costs compute) |
| collisionFile | str | item | OR existing collision `.stl` path |
| visualGeo | Geometry | list | display-only surfaces (e.g. lattice), barycentric-mapped |
| visualFiles | str | list | display-only `.stl` paths, used as-is |
| visualFaces | int | item | decimate visualGeo to this face count on export (0 = off) |
| protocol | str | item | keyframed rigid motion from SofaProtocol; needs fixations (the motion drags the body by its clamps) |
| exportShape | int | item | export the full deformed volume every N steps (0 = off); read back with SofaShape (N=10 at dt 0.01 → 10 frames/s of sim) |

Output: `body` (object).

Monitor points also record **force**: SofaResults returns the nodal force
(mN) at each monitorPt, so points placed on a contact pad read out the grip
reaction.

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
| ptsFile | str | item | OR JSON `[[x,y,z],...]` path (LETIAS `interpolated_trunk_cable_N.json`) |
| channel | int | item | input.csv column |
| name | str | item | default `cable_<channel>` |
| valueType | str | item | `displacement` (mm, default) or `force` (mN) |
| pullPoint | Point3d | item | optional external anchor (motor/pulley) |

Outputs: `tendon` (token), `pathPts` (routing points, preview).

Control: same PressureProfile/channel system as cavities — `valueType`
decides interpretation (displacement mm, applied raw; force mN, ×dt like
pressures). Multi-cable systems: use `force` (simultaneous displacement
control of coupled cables fights the constraint solver — LETIAS note).
Telemetry: every run writes `output/cables.csv` (displacement + force
per cable per step) — read back via SofaResults `cableDisp`/`cableForce`.

## SofaTendons / SofaProfiles — multi-channel variants

Same as SofaTendon/PressureProfile but one component drives N channels
via **tree-access** inputs (right-click input → Access → Tree):

* `SofaTendons`: `pts` tree, one branch per tendon (don't flatten a
  Divide Curve over a list of curves — its output is already the right
  tree); `channels` list optional (default 1..N); one `valueType` for
  all; `pullPoints` list matched by index. Output `tendons` = list →
  SofaBody.tendons directly, no Merge.
* `SofaProfiles`: `values` tree (branch per channel), `times` tree
  (single branch = shared timeline), `channels` list optional. Output
  `profiles` = list → SofaScene.profiles.

Per-component variants stay available; plural ones keep the canvas
compact for 3+ channels.

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

## SofaProtocol — keyframed rigid body motion

Keyframes an offset of the whole body over time (pick-and-place moves:
carry the gripper down, hold, lift). Applied through the body's rest
positions — the body is dragged by its **fixations**; a body without a
fixation box will not follow.

| Input | Hint | Access | Notes |
|---|---|---|---|
| times | float | list | keyframe times, s |
| offsets | Vector3d | list | body offset from its start position per keyframe; first usually (0,0,0) |
| name | str | item | optional |

Output: `protocol` (token) → new `SofaBody.protocol` input. Linear
interpolation; held outside the keyframe span. Time the actuation
profiles to match (e.g. inflate while the offset holds at the object).

## AnimationPreview — scrub the finished sim in the viewport (experimental, not in v0.1)

Frame slider → deformed body volumes (needs `exportShape` on bodies),
rigid targets at their frame pose (automatic 3-point pose track),
monitored points at that instant, static fixation boxes + tendon paths.

| Input | Hint | Access | Notes |
|---|---|---|---|
| scenePath | str | item | |
| frame | int | item | empty = last; wire slider 0..nFrames−1 |
| repo | str | item | |
| refresh | bool | item | |

Outputs: `volumes`, `targets`, `trackPts`, `tendonCrvs` (static),
`fixBoxes`, `nFrames`, `time`, `info`.

## SetupPreview — scene preview in the Rhino viewport

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
(Mesh lists), `tendonCrvs` (cable routing paths), `tendonChs` (channel per
tendon — Text Tag the start points), `monitorPts` (points), `fixBoxes`
(boxes), `info`.

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
| bodies | str/none | list | |
| profiles | str/none | list | |
| targets | str/none | list | optional, from SofaTarget |
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
`meshes/`, `scene.json`, `input.csv`, copies `sofagh/runtime/scene.py` +
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
frame, items = tracked points), `lastPts` (final frame), `forces`
(DataTree of Vector3d — nodal force in mN at the monitor points, branch per
frame; the grip reaction where points sit on a contact pad), `pTimes`,
`pressures` (DataTree — branch per channel), and when tendons exist:
`cableNames`, `cableDisp` (mm), `cableForce` (mN) — branch per cable.

When the scene has targets and collision, a contact map comes back too:
`contactPairs` (list of `body__target` names), `contactCount` (DataTree —
contacts per step, branch per pair), `contactTimes` (branch per pair), and
`contactPts` (DataTree — contact locations on the body surface, branch per
`pair; frame`). This is contact **geometry** — where and how many — not the
resolved contact force; for a force reading use `forces` at monitor points
on the pad.

Typical use: `points` → Tree Branch + slider = scrub motion; Flip
Matrix → Polyline = trajectories; `pressures` → Quick Graph;
`contactPts` → point cloud at a frame = the grasp contact map.
