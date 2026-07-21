# SofaRun — launch runSofa on a project
#
# Rhino 8 Grasshopper Script component (Python 3).
# Inputs:
#   scenePath : str — from SofaScene                          [item, str]
#   sofaRoot  : str — SOFA binaries folder, e.g.              [item, str]
#               C:\Users\me\Desktop\SOFA\SOFA_v24.06.00_Win64
#               (optional if SOFA_ROOT env var is set)
#   repo      : str — path to the sofa-gh folder              [item, str]
#   gui       : bool — True: interactive window; False: batch [item, bool]
#   winRect   : list of 4 ints — x, y, width, height to place [list, int]
#               the SOFA window (Windows only; e.g. 0,600,900,700
#               = bottom-left tile). Empty = wherever Qt puts it.
#   run       : bool — set True to launch                     [item, bool]
# Outputs:
#   status    : str
#
# Batch runs block Grasshopper until done (minutes for MU-sized meshes).
# GUI runs return immediately (detached window); press Animate in SOFA.

import sys

winRect = globals().get("winRect")

status = "set run=True"

if run and scenePath:
    scenePath = scenePath.strip().strip('"\'')
    if sofaRoot:
        sofaRoot = sofaRoot.strip().strip('"\'').rstrip("\\/")
    repo = repo or __import__("os").environ.get("SOFAGH_ROOT")
    if repo:
        repo = repo.strip().strip('"\'').rstrip("\\/")
        if repo not in sys.path:
            sys.path.append(repo)
    from sofagh import runner

    # robust bool coercion: without a bool type hint GH delivers a
    # wrapped object whose truthiness is always True
    if gui is None:
        use_gui = True
    else:
        _v = getattr(gui, "Value", gui)
        use_gui = _v if isinstance(_v, bool) else str(_v).strip().lower() not in ("false", "0", "")
    rect = [int(v) for v in winRect] if winRect and len(winRect) == 4 else None
    rc, log = runner.run(scenePath, sofa_root=sofaRoot or None,
                         gui=use_gui, blocking=not use_gui, window=rect)
    if rc is None:
        status = f"runSofa launched (GUI). Log: {log}"
    elif rc == 0:
        status = f"batch run finished OK. Log: {log}"
    else:
        from sofagh import results
        import os
        tail = results.read_log_tail(os.path.dirname(scenePath))
        status = f"runSofa exited {rc}. Log tail:\n{tail}"
