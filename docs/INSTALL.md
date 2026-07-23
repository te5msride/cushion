# Installation

Two roles are involved conceptually: where Grasshopper runs and where
SOFA runs. In v0.1 they are the **same machine** (the runner launches a
local `runSofa`).

Work through the sections in order. The single most common failure is
the SOFA-side Python (§4) — get `runSofa` printing a Python version
before you touch Grasshopper.

---

## 1. Rhino 8

Rhino 8 with Grasshopper. Document units **must be millimeters**
(Cushion is mm/kPa/kg/s throughout). The components run in Rhino's
built-in CPython (Python 3, `py39-rh8`) — no separate Python needed for
the Grasshopper side.

## 2. Getting the Cushion components

Pick one — **A** is all you need to run the bundled examples.

**A. Run the examples (recommended to try it out).**
Clone or download this repository anywhere readable, then open
`examples/continuum_robot.gh` or `examples/simple_gripper.gh` in
Grasshopper. The Cushion components are already embedded in the
definition as **Script components** — nothing to register or compile.
You only set path inputs (§6).

**B. Build the components yourself (authoring a new definition).**
Create a Script component (Python 3) from each file in
`gh/components/*.py`: paste the script, then add the inputs/outputs
listed in that file's header comment. Exact signatures are in
[COMPONENTS.md](COMPONENTS.md).

**C. Compiled plugin `.gha` (end-user path, once released).**
When Cushion is published, install the **`.yak`** package via Rhino's
`_PackageManager` (search "Cushion") — this is the food4rhino route and
the intended way for non-developers. Manual fallback: drop the `.gha`
into Grasshopper's components folder
(*File ▸ Special Folders ▸ Components Folder*), right-click the file ▸
**Unblock** (Windows), and restart Rhino; the components then appear
under a **Cushion** tab. Not required to run the examples above.

## 3. SOFA v24.06.00

Download the **full binary bundle** for your OS from the pinned release:

> https://github.com/sofa-framework/sofa/releases/tag/v24.06.00

The bundle already contains the required plugins — `SofaPython3`,
`SoftRobots`, `STLIB`, `SofaValidation`, `MultiThreading`. Confirm they
exist under `<SOFA>/plugins/`. Use **exactly v24.06.00**: SofaPython3 is
built against a specific Python (3.10) and other releases will not load
the bundled plugins cleanly.

Platform extraction details are in §5 (Windows) / §6 (macOS).

## 4. Python 3.10 + numpy (for SOFA's embedded interpreter)

This is **separate** from Rhino's Python — it is the interpreter
SofaPython3 links against. Details per platform in §5 / §6. Verify SOFA
works **before** Grasshopper:

```
<SOFA>/bin/runSofa -l SofaPython3 -g batch -n 1
```

Expected: `[SofaPython3] Initializing with python version 3.10.x` and no
`Plugin loading failed`. If you see a missing-Python error, §5/§6 fix it.

## 5. gmsh (manual, into Rhino's CPython)

Cushion meshes geometry with the `gmsh` Python package, which must live
in **Rhino's own CPython**. Install it once, explicitly — do **not**
assume Rhino auto-installs it.

Locate Rhino 8's Python:

* **Windows:** `%USERPROFILE%\.rhinocode\py39-rh8\python.exe`
* **macOS:**   `~/.rhinocode/py39-rh8/python3`

Install and verify (quote the path if it has spaces):

```
"<rhino-python>" -m pip install gmsh
"<rhino-python>" -c "import gmsh; print(gmsh.__version__)"
```

The second line must print a version. If `pip` is missing, run
`"<rhino-python>" -m ensurepip` first.

> Note: SofaScene carries a `# r: gmsh` directive that *may* fetch gmsh
> on first run when the machine is online. Do not rely on it — offline,
> proxied, or locked-down machines fail silently. The manual install
> above is the sure path and only takes a minute.

## 6. Wiring the paths

Cushion needs three paths at runtime:

* **`repo`** — this repository's folder. Wire it into each component's
  `repo` input, **or** set the `SOFAGH_ROOT` environment variable once
  and leave the `repo` inputs empty.
* **`sofaRoot`** (SofaRun) — the SOFA folder (the one **containing**
  `bin/`). Alternatively set `SOFA_ROOT`; the runner also auto-scans
  `/Applications` on macOS.
* **`projDir`** (SofaScene) — a **local-disk** working folder for the
  written project. Never a synced folder (see below).

---

## Windows

* Extract the SOFA zip somewhere stable, e.g.
  `C:\SOFA\SOFA_v24.06.00_Win64`. Watch for double-nesting
  (`...\SOFA_v24.06.00_Win64\SOFA_v24.06.00_Win64\bin\...`).
* `sofaRoot` = the folder **containing** `bin\`, not `bin\` itself. (The
  runner tolerates either, plus one level above.)
* If `runSofa -l SofaPython3` complains about a missing Python DLL,
  install **Python 3.10** (python.org, 64-bit), then:
  `py -3.10 -m pip install numpy`.
* Keep `projDir` on the **local disk**, not OneDrive/Dropbox — the
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

> gmsh (§5) installs into Rhino's Python normally on Apple Silicon — that
> interpreter is native and unrelated to SOFA's x86_64 requirement.

---

## Moving a .gh definition between platforms

The definition itself is portable (components, wires, type hints all
travel). Only **panel contents** change: `repo`, `projDir`, `sofaRoot`,
and any mesh-file paths. Keep one path panel per platform
(disabled/enabled), everything else is shared. Paths need no surrounding
quotes — the components strip stray quotes and whitespace, but clean
input avoids surprises.

Re-check after switching: `projDir` must always be a local-disk path on
the machine currently running SOFA.
