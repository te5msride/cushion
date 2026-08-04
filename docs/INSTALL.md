# Installation

Two roles are involved conceptually: where Grasshopper runs and where
SOFA runs. In v0.1 they are the **same machine** (the runner launches a
local `runSofa`).

Work through the sections in order. The single most common failure is
the SOFA-side Python (§4). Get `runSofa` printing a Python version
before you touch Grasshopper.

---

## 1. Rhino 8

Rhino 8 with Grasshopper. Document units **must be millimeters**
(Cushion is mm/kPa/kg/s throughout). The components run in Rhino's
built-in CPython (Python 3, `py39-rh8`). No separate Python is needed
for the Grasshopper side.

## 2. Install the Cushion plugin (required, even for the examples)

The example definitions use the compiled Cushion components, so the
plugin must be installed before you open them. Two ways:

* **Package Manager (recommended):** in Rhino run `_PackageManager`,
  search **Cushion**, install, and restart Rhino.
* **Manual `.gha`:** copy `dist/Cushion.Components.gha` into Grasshopper's
  components folder (*File ▸ Special Folders ▸ Components Folder*). On
  Windows, right-click the file ▸ Properties ▸ **Unblock** first, then
  restart Rhino.

Either way the components appear under a **Cushion** tab in Grasshopper.
The listing (with the download) is on food4Rhino:
https://www.food4rhino.com/en/app/cushion

### Pufferfish

The examples also use the **Reduce Mesh** component from the free
**Pufferfish** plugin (food4Rhino). Install it the same way (Package
Manager or drop-in) before opening the examples.

### Open an example

With both plugins installed, open `examples/continuum_robot.gh` or
`examples/simple_gripper.gh`, then set the path inputs (§6).

## 3. SOFA v24.06.00

Download the **full binary bundle** for your OS from the pinned release:

> https://github.com/sofa-framework/sofa/releases/tag/v24.06.00

The bundle already contains the required plugins: `SofaPython3`,
`SoftRobots`, `STLIB`, `SofaValidation`, `MultiThreading`. Confirm they
exist under `<SOFA>/plugins/`. Use **exactly v24.06.00**: SofaPython3 is
built against a specific Python (3.10) and other releases will not load
the bundled plugins cleanly.

Platform extraction details are in §5 (Windows) / §6 (macOS).

## 4. Python 3.10 + numpy (for SOFA's embedded interpreter)

This is **separate** from Rhino's Python; it is the interpreter
SofaPython3 links against. Details per platform in §5 / §6. Verify SOFA
works **before** Grasshopper by just launching it:

```
<SOFA>/bin/runSofa
```

The SOFA GUI should open. In its startup log, look for
`[SofaPython3] Initializing with python version 3.10.x` and no
`Plugin loading failed`. If you see a missing-Python error, §5/§6 fix it.

## 5. gmsh (manual: into Rhino's CPython)

Cushion meshes geometry with the `gmsh` Python package, which must live
in **Rhino's own CPython**. Install it once, explicitly. Do **not**
assume Rhino auto-installs it.

**First, make Rhino generate its Python.** The `.rhinocode/py39-rh8`
folder does not exist on a fresh install; Rhino creates it only after a
Python 3 script component has run at least once. So before the commands
below: launch Rhino, drop any **Python 3 Script component** onto a
Grasshopper canvas (or just open one of the example definitions and let
it load). Then the folder exists.

> New to Grasshopper? To find the component: **double-click an empty spot
> on the canvas** and type "Python 3 Script" to search, or grab it from
> the **Math** tab → **Script** panel (the Python icon). Drop it on the
> canvas and it runs once, which is all that's needed here.

Locate Rhino 8's Python:

* **Windows:** `%USERPROFILE%\.rhinocode\py39-rh8\python.exe`
* **macOS:**   `~/.rhinocode/py39-rh8/python3.9`

If the path isn't there yet, you skipped the step above. Run a Python
component in Grasshopper first.

Install and verify (quote the path if it has spaces):

```
"<rhino-python>" -m pip install gmsh
"<rhino-python>" -c "import gmsh; print(gmsh.__version__)"
```

The second line must print a version. If `pip` is missing, run
`"<rhino-python>" -m ensurepip` first.

> Note: SofaScene carries a `# r: gmsh` directive that *may* fetch gmsh
> on first run when the machine is online. Do not rely on it; offline,
> proxied, or locked-down machines fail silently. The manual install
> above is the sure path and only takes a minute.

## 6. Wiring the paths

Cushion needs three paths at runtime:

* **`repo`**: this repository's folder. Wire it into each component's
  `repo` input, **or** set the `SOFAGH_ROOT` environment variable once
  and leave the `repo` inputs empty.
* **`sofaRoot`** (SofaRun): the SOFA folder (the one **containing**
  `bin/`). Alternatively set `SOFA_ROOT`; the runner also auto-scans
  `/Applications` on macOS.
* **`projDir`** (SofaScene): a **local-disk** working folder for the
  written project. Never a synced folder (see below).

---

## Windows

* Extract the SOFA zip somewhere stable, e.g.
  `C:\SOFA\SOFA_v24.06.00_Win64`. Watch for double-nesting
  (`...\SOFA_v24.06.00_Win64\SOFA_v24.06.00_Win64\bin\...`).
* `sofaRoot` = the folder **containing** `bin\`, not `bin\` itself. (The
  runner tolerates either, plus one level above.)
* Install **Python 3.10, 64-bit** (python.org) **with "Add Python to
  PATH" checked** during setup — SofaPython3 loads `python310.dll` from
  PATH, and a missing/off-PATH 3.10 is the usual "specified module could
  not be found" / empty-scene failure. Then `py -3.10 -m pip install numpy`.
  (Already installed but off PATH? Add its folder to System Properties →
  Environment Variables → Path, or reinstall with the checkbox.)
* Keep `projDir` on the **local disk**, not OneDrive/Dropbox; the
  controller writes CSV/monitor files every timestep and sync clients
  corrupt or lock them mid-write.

## macOS

The macOS build is x86_64 and hard-links a specific Python.

1. Move the extracted folder to `/Applications/SOFA_v24.06.00_MacOS`
   (any stable path works).
2. **Clear quarantine** (Gatekeeper blocks downloaded binaries):
   ```
   xattr -rd com.apple.quarantine /Applications/SOFA_v24.06.00_MacOS
   ```
3. **Install Python 3.10 from python.org** (the universal2 installer,
   e.g. `python-3.10.11-macos11.pkg`). SofaPython3 tries a Homebrew
   Intel path first but falls back to
   `/Library/Frameworks/Python.framework/Versions/3.10/Python`, exactly
   where the python.org pkg installs. Homebrew Python does **not** work
   on Apple Silicon (wrong prefix and/or architecture).
4. **numpy into that Python, x86_64 slice:**
   ```
   arch -x86_64 /Library/Frameworks/Python.framework/Versions/3.10/bin/python3.10 -m pip install numpy
   ```
5. Apple Silicon: `runSofa` executes under **Rosetta 2** (self-installs
   on first launch if missing). Works; expect roughly half the speed of
   a comparable x86 machine.
6. Optional: `export SOFA_ROOT=/Applications/SOFA_v24.06.00_MacOS` in
   your shell profile; the runner also auto-scans `/Applications`.

> gmsh (§5) installs into Rhino's Python normally on Apple Silicon; that
> interpreter is native and unrelated to SOFA's x86_64 requirement.

---

## Moving a .gh definition between platforms

The definition itself is portable (components, wires, type hints all
travel). Only **panel contents** change: `repo`, `projDir`, `sofaRoot`,
and any mesh-file paths. Keep one path panel per platform
(disabled/enabled), everything else is shared. Paths need no surrounding
quotes; the components strip stray quotes and whitespace, but clean
input avoids surprises.

Re-check after switching: `projDir` must always be a local-disk path on
the machine currently running SOFA.
