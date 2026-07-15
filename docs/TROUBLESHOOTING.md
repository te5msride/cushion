# Troubleshooting

Field-tested failures, in the order you're likely to hit them.

## Grasshopper side

**`No module named 'ghcommon'` / `No module named 'sofagh'`**
`repo` doesn't point at the sofa-gh folder. Check
`<repo>/gh/ghcommon.py` and `<repo>/sofagh/__init__.py` exist (partial
copies and zip double-nesting are the usual cause). Panels: no trailing
newline (right-click panel → uncheck *Multiline Data*), no quotes.

**`string indices must be integers`, or a component output shows a
list of key names (`kind, geo, name, ...`)**
A dict-carrying input has a type hint. Set `bodies`, `profiles`,
`cavities`, `tendons`, `regions` inputs to **No Type Hint**. Dicts are
passed wrapped in `GH_ObjectWrapper`; outputs showing
`Grasshopper.Kernel.Types.GH_ObjectWrapper` in a panel is correct.

**`volumeFile not found: '/path/...'` with quotes in the message**
Path pasted with literal quotes. Current scripts strip them; if you see
this, the component holds an old script — re-paste.

**"Collecting gmsh" hangs**
First-run pip install into Rhino's CPython (~90 MB). 1–3 min normal.
Stuck: check internet/proxy or install manually:
`~/.rhinocode/py39-rh8/python3.9 -m pip install gmsh` (path analogous
on Windows), restart component.

**Changes to sofagh/*.py not taking effect**
Python module cache. Restart Rhino after editing package files
(component scripts re-paste live; package files don't).

## SOFA side

**SOFA window opens but scene is empty (only DefaultAnimationLoop,
Mouse...), Reload Scene crashes**
SofaPython3 failed to load → `.py` scene silently skipped. Check
`<projDir>/runsofa.log` for `Plugin loading failed`. Cause is almost
always the Python 3.10 dependency → see INSTALL.md platform steps.
(macOS: `Library not loaded: /usr/local/opt/python@3.10/...` → install
python.org 3.10; the dyld fallback finds it in /Library/Frameworks.)

**`runSofa not found ... Checked:` list**
`sofaRoot` wrong level or unset. Point at the folder containing `bin/`.
The error lists every path tried — read it.

**`ModuleNotFoundError: No module named 'numpy'` in runsofa.log**
numpy missing from SOFA's Python (3.10), not Rhino's. Install per
INSTALL.md (macOS: use `arch -x86_64`).

**`RequiredPlugin` errors in log**
Plugin missing from `<SOFA>/plugins/`. The official v24.06 bundle has
everything; partial/nightly builds may not.

**Sim runs but body free-falls or drifts instead of deforming**
Fixation box doesn't intersect the mesh — BoxROI selected 0 nodes
(check log). Box must contain mesh nodes. Or gravity is on without any
fixation: set `gravityZ` 0 or add a clamp.

**Body invisible in SOFA, only cavity visible (green)**
Normal: FEM volume has no visual by default; green = SurfacePressure
debug draw. Wire the body surface (or lattice) into `visualGeo`, or in
the SOFA GUI View panel enable *Behavior Models* to see the tets.

## Results side

**SofaResults outputs empty**
Read its `info` output — it says which file it looked for. Usual causes:
`write` toggled off (SofaScene emits `scenePath` only while True); sim
never animated (GUI mode requires pressing **Animate**); no
`monitorPts` were wired when the scene was written; `bodyName`
mismatch.

**Monitor nodes list has duplicates**
Several monitorPts snapped to the same closest mesh node — points
outside the volume or closer together than the mesh resolution. Space
them out / keep them inside the body.

## Environment

**OneDrive**: fine for the repo (read-only imports; restart Rhino after
sync updates), bad for `projDir` (per-timestep writes fight the sync
client) — keep project output on local disk.

**macOS performance**: x86_64 build under Rosetta ≈ half native speed.
MU-scale mesh (~8.5k nodes): a few minutes per grasp cycle. Batch
(`gui` False) is faster than GUI.
