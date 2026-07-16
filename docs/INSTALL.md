# Installation

Two machines are involved conceptually: where Grasshopper runs and
where SOFA runs. In v0.1 they are the same machine (the runner launches
a local `runSofa`).

## Common (both platforms)

1. **Rhino 8** with Grasshopper.
2. **SOFA v24.06 binaries** from
   https://www.sofa-framework.org/download/ — take the full bundle; it
   already contains the required plugins: `SofaPython3`, `SoftRobots`,
   `STLIB`, `SofaValidation`, `MultiThreading`. Verify they exist in
   `<SOFA>/plugins/`.
3. **This repository**, anywhere readable. Either wire its path into
   the components' `repo` inputs, or set the **`SOFAGH_ROOT`**
   environment variable to it once (then `repo` inputs can stay empty).
   Similarly `SOFA_ROOT` replaces the `sofaRoot` input on SofaRun.
4. **gmsh** is installed automatically into Rhino's own CPython by the
   `# r: gmsh` directive in SofaScene on first run (needs internet,
   1–3 min, ~90 MB, once per machine). No system install needed.
   Manual fallback: `<rhino-python> -m pip install gmsh` where
   `<rhino-python>` lives under `~/.rhinocode/py39-rh8/`.
5. **Python 3.10 + numpy** for SOFA's embedded interpreter — see
   platform sections; this is the most common setup failure.

Verify the SOFA side works before touching Grasshopper:

```
<SOFA>/bin/runSofa -l SofaPython3 -g batch -n 1
```

Expected: `[SofaPython3] Initializing with python version 3.10.x`, no
`Plugin loading failed`.

## Windows

* Extract the SOFA zip somewhere stable, e.g.
  `C:\SOFA\SOFA_v24.06.00_Win64`. Watch for double-nesting when
  extracting (`...\SOFA_v24.06.00_Win64\SOFA_v24.06.00_Win64\bin\...`).
* `sofaRoot` (SofaRun input) = the folder **containing** `bin\`, not
  `bin\` itself. (The runner tolerates either, plus one level above.)
* Install **Python 3.10** (python.org, 64-bit) if
  `runSofa -l SofaPython3` complains about a missing python DLL, then:
  `py -3.10 -m pip install numpy`.
* Keep project output folders (`projDir`) on the local disk, not
  OneDrive — the controller writes CSV/monitor files every timestep and
  sync clients interfere.

## macOS

Extra steps — the macOS build is x86_64 and hard-links a specific
Python:

1. Move the extracted folder to `/Applications/SOFA_v24.06.00_MacOS`
   (any stable path works).
2. **Clear quarantine** (Gatekeeper blocks downloaded binaries):
   ```
   xattr -rd com.apple.quarantine /Applications/SOFA_v24.06.00_MacOS
   ```
3. **Install Python 3.10 from python.org** (the universal2 installer,
   e.g. `python-3.10.11-macos11.pkg`). SofaPython3 dlopens a Homebrew
   Intel path first but falls back to
   `/Library/Frameworks/Python.framework/Versions/3.10/Python`, which
   is exactly where the python.org pkg installs. Homebrew Python does
   NOT work on Apple Silicon (wrong prefix and/or wrong architecture).
4. **numpy into that Python, x86_64 slice**:
   ```
   arch -x86_64 /Library/Frameworks/Python.framework/Versions/3.10/bin/python3.10 -m pip install numpy
   ```
5. Apple Silicon: runSofa executes under **Rosetta 2** (installs itself
   on first launch if missing). Works; expect roughly half the speed of
   a comparable Windows/Linux x86 machine.
6. Optional: `export SOFA_ROOT=/Applications/SOFA_v24.06.00_MacOS` in
   your shell profile; the runner also auto-scans `/Applications`.

## Moving a .gh definition between platforms

The definition itself is portable (components, wires, type hints all
travel). Only **panel contents** need changing: `repo`, `projDir`,
`sofaRoot`, and any mesh-file paths. Keep two path panels per machine
(or one panel per platform, disabled/enabled), everything else is
shared. Paths must have no surrounding quotes; the components strip
stray quotes and whitespace, but clean input avoids surprises.

Re-check after switching: `projDir` should always be a local disk path
on the machine currently running SOFA.
