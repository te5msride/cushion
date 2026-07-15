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
#   run       : bool — set True to launch                     [item, bool]
# Outputs:
#   status    : str
#
# Batch runs block Grasshopper until done (minutes for MU-sized meshes).
# GUI runs return immediately (detached window); press Animate in SOFA.

import sys

status = "set run=True"

if run and scenePath:
    scenePath = scenePath.strip().strip('"\'')
    if sofaRoot:
        sofaRoot = sofaRoot.strip().strip('"\'').rstrip("\\/")
    if repo:
        repo = repo.strip().strip('"\'').rstrip("\\/")
        if repo not in sys.path:
            sys.path.append(repo)
    from sofagh import runner

    use_gui = True if gui is None else bool(gui)
    rc, log = runner.run(scenePath, sofa_root=sofaRoot or None,
                         gui=use_gui, blocking=not use_gui)
    if rc is None:
        status = f"runSofa launched (GUI). Log: {log}"
    elif rc == 0:
        status = f"batch run finished OK. Log: {log}"
    else:
        from sofagh import results
        import os
        tail = results.read_log_tail(os.path.dirname(scenePath))
        status = f"runSofa exited {rc}. Log tail:\n{tail}"
