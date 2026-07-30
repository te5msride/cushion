# Getting-started video — recording script

Record the screen actions, then dub the voiceover. Starts from a machine
that already has **Rhino 8 + Grasshopper** installed.

**Record:** what to do on screen · **Say:** voiceover to dub.

---

## 0. Intro (title card or talking head, ~15s)
- **Say:** "Cushion runs SOFA soft-body simulation inside Grasshopper. This
  video takes you from a fresh Rhino/Grasshopper install to running your
  first soft-robot simulation. Five things to set up: the plugin, SOFA,
  Python 3.10, gmsh, and one helper plugin."

## 1. Get the repository
- **Record — clone (with git):** terminal → `git clone https://github.com/te5msride/cushion.git`
  → `cd cushion` → show the folder (`dist/`, `examples/`, `docs/`).
- **Record — Download ZIP (no git):** GitHub page → green **Code** button →
  **Download ZIP** → unzip → show the same folder.
- **Say:** "First, grab the repository — this has everything: the plugin in
  the `dist` folder, the example files, and the docs. If you use git, clone
  it. If not, hit the green Code button and Download ZIP, then unzip.
  Remember where you put it — you'll point the plugin at this folder in a
  minute. Keep it somewhere stable, not your Downloads folder."

## 2. Install the plugin — Package Manager (easiest)
- **Record:** Rhino command line → `_PackageManager` → search **Cushion** →
  **Install** → **fully close Rhino** → **reopen** → show the **Cushion** tab
  in Grasshopper.
- **Say:** "Easiest way to install the plugin — Rhino's Package Manager. Run
  underscore-PackageManager, search Cushion, install. Then fully close and
  reopen Rhino so it loads. You'll see a Cushion tab appear in Grasshopper."

## 3. Install the plugin — drag the .gha (alternative)
- **Record:** Grasshopper → **File → Special Folders → Components Folder** →
  drag `dist/Cushion.Components.gha` (from the repo you cloned) into it →
  *(Windows: right-click the file → Properties → **Unblock**)* → restart Rhino
  → Cushion tab.
- **Say:** "Or install it manually: in Grasshopper open File, Special
  Folders, Components Folder, and drop `Cushion.Components.gha` from the
  repo's `dist` folder in there. On Windows, right-click it and Unblock
  first. Restart Rhino — same Cushion tab appears."

## 4. Install SOFA v24.06.00
- **Record:** browser → the pinned release
  (github.com/sofa-framework/sofa/releases/tag/v24.06.00) → download the
  bundle for your OS → extract somewhere stable (e.g.
  `C:\SOFA\SOFA_v24.06.00_Win64`) → terminal →
  `<SOFA>\bin\runSofa -l SofaPython3 -g batch -n 1` → highlight the line
  **"Initializing with python version 3.10.x"**.
- **Say:** "Cushion needs the free SOFA binaries — exactly version 24.06.00.
  Download, extract somewhere stable, and verify with this one command. You
  want to see 'Initializing with python version 3.10' and no plugin-loading
  errors."

## 5. Install Python 3.10 (the #1 gotcha)
- **Record:** python.org → **Python 3.10, 64-bit** installer → first screen,
  **check "Add Python to PATH"** (zoom/highlight it) → install → terminal
  `py -3.10 -m pip install numpy`.
- **Say:** "SOFA's Python side needs Python 3.10 specifically — not 3.11 or
  3.12. During install, check 'Add Python to PATH'. This is the single most
  common setup failure. Then install numpy into it."

## 6. Generate Rhino's Python folder (needed before gmsh)
- **Record:** Grasshopper → double-click the canvas → search **"Python 3
  Script"** → drop the component (or open one of the example files). Let it
  compute once.
- **Say:** "One quirk: Rhino only creates its Python folder after a Python
  component runs once. So drop a Python 3 Script component on the canvas — or
  open an example — to trigger it. Now the folder exists."

## 7. Install gmsh into Rhino's Python
- **Record:** terminal → pip install against Rhino's python:
  - Windows: `"%USERPROFILE%\.rhinocode\py39-rh8\python.exe" -m pip install gmsh`
  - macOS: `~/.rhinocode/py39-rh8/python3.9 -m pip install gmsh`
  → verify: `... -c "import gmsh; print(gmsh.__version__)"`.
- **Say:** "Cushion meshes with gmsh, which lives in Rhino's own Python.
  Install it once with this command — note the path points into Rhino's
  dot-rhinocode folder, not your system Python. Verify it prints a version."

## 8. Install Pufferfish (for the examples)
- **Record:** `_PackageManager` → search **Pufferfish** → Install → restart.
- **Say:** "The example files use the Reduce Mesh component from the free
  Pufferfish plugin — grab that from the Package Manager too."

## 9. Run your first example
- **Record:** open `examples/simple_gripper.gh` (or `continuum_robot.gh`) →
  show the three path panels → set **repo** (the cloned folder), **sofaRoot**
  (your SOFA folder), **projDir** (a local-disk folder, e.g.
  `C:\sofa_projects\gripper`) → **SofaScene** `write` → True → **SofaRun**
  `run` → True → SOFA window opens → press **Animate** → let it grasp → back
  in Grasshopper toggle **SofaResults** refresh → show trajectories/forces.
- **Say:** "Now the payoff. Open an example and set three paths — the Cushion
  folder you cloned, your SOFA folder, and a local output folder (keep it off
  OneDrive). Toggle write, then run. SOFA opens; press Animate and watch it
  simulate. Back in Grasshopper, refresh SofaResults and the trajectories and
  forces come right back onto the canvas."

## 10. Outro
- **Say:** "That's it — you're set up. Full docs, the manual, and both
  examples are on GitHub and food4Rhino, links below. Have fun building soft
  robots."

---

## Callouts to sprinkle in (scripted one-liners)
- **Exactly 3.10** (over the Python install): "3.11 and 3.12 won't work —
  SofaPython3 is built against 3.10."
- **Empty scene?** (if the SOFA window opens blank): "That almost always
  means Python 3.10 isn't on your PATH — recheck the Python step."
- **projDir must be local:** "Never point the project folder at OneDrive or
  Dropbox; per-timestep writes fight the sync client."
- **Wrong version:** "If runSofa logs 'Plugin not found: SofaLoader', you've
  got the wrong SOFA version — Cushion targets 24.06.00."
- **It's a round-trip:** "Grasshopper writes the scene files, SOFA does the
  physics, and the results come back — all without leaving Rhino."

## Recording tips
- Zoom / highlight the **"Add Python to PATH"** checkbox and the **three path
  panels** — that's where people fail.
- Keep the terminal font large.
- If a live run is slow, cut or speed it up in post.
- You need the repo either way: even installing the plugin from the Package
  Manager, the examples live in the repo and set the `repo` path to it.
