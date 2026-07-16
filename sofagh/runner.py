"""Locate SOFA binaries and launch runSofa on a project.

Matches Anderson's multiple.py environment setup: PYTHONPATH must point
at SofaPython3 and STLIB site-packages inside the SOFA binary tree.
Tested layout: SOFA_v24.06.00_Win64 (also works for the Linux tree).
"""

import json
import os
import subprocess
import sys


def find_sofa(sofa_root=None):
    """Resolve the SOFA root dir. Order: arg, SOFA_ROOT env, common spots.

    Accepts the root itself, its bin/ subfolder, or a folder one level
    above the root (nested zip extraction) — all normalized to the root.
    """
    candidates = []
    if sofa_root:
        sofa_root = str(sofa_root).strip().strip('"').rstrip("\\/")
        candidates.append(sofa_root)
        # user pointed at bin/ -> parent is the root
        if os.path.basename(sofa_root).lower() == "bin":
            candidates.append(os.path.dirname(sofa_root))
        # user pointed one level above the root (nested extraction)
        if os.path.isdir(sofa_root):
            for entry in sorted(os.listdir(sofa_root), reverse=True):
                sub = os.path.join(sofa_root, entry)
                if os.path.isdir(sub):
                    candidates.append(sub)
    if os.environ.get("SOFA_ROOT"):
        candidates.append(os.environ["SOFA_ROOT"])
    home = os.path.expanduser("~")
    for base in (os.path.join(home, "Desktop", "SOFA"), home, "/Applications",
                 "C:\\", "C:\\SOFA"):
        if os.path.isdir(base):
            for entry in sorted(os.listdir(base), reverse=True):
                if entry.startswith("SOFA_v"):
                    candidates.append(os.path.join(base, entry))
    for c in candidates:
        if c and os.path.isfile(_runsofa_path(c)):
            return os.path.abspath(c)
    checked = "\n  ".join(_runsofa_path(c) for c in candidates if c)
    raise FileNotFoundError(
        "runSofa not found. Set SOFA_ROOT or pass sofa_root "
        "(folder containing bin/runSofa[.exe]). Checked:\n  " + checked)


def _runsofa_path(sofa_root):
    exe = "runSofa.exe" if os.name == "nt" else "runSofa"
    return os.path.join(sofa_root, "bin", exe)


def _sofa_env(sofa_root):
    env = dict(os.environ)
    sep = ";" if os.name == "nt" else ":"
    pp = [os.path.join(sofa_root, "plugins", "SofaPython3", "lib", "python3", "site-packages"),
          os.path.join(sofa_root, "plugins", "STLIB", "lib", "python3", "site-packages")]
    if env.get("PYTHONPATH"):
        pp.append(env["PYTHONPATH"])
    env["PYTHONPATH"] = sep.join(pp)
    env["SOFA_ROOT"] = sofa_root
    return env


def place_sofa_window(rect, timeout=15.0):
    """Move the runSofa window to rect=(x, y, w, h). Windows only;
    polls in a daemon thread until the window appears."""
    if os.name != "nt":
        return  # macOS needs Accessibility permission; not supported

    import ctypes
    import threading
    import time as _time
    user32 = ctypes.windll.user32

    def _find_and_move():
        deadline = _time.time() + timeout
        while _time.time() < deadline:
            found = []

            @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
            def _enum(hwnd, _):
                buf = ctypes.create_unicode_buffer(256)
                user32.GetWindowTextW(hwnd, buf, 256)
                if buf.value.startswith("SOFA v") and user32.IsWindowVisible(hwnd):
                    found.append(hwnd)
                return True

            user32.EnumWindows(_enum, None)
            if found:
                x, y, w, h = [int(v) for v in rect]
                user32.MoveWindow(found[0], x, y, w, h, True)
                return
            _time.sleep(0.5)

    threading.Thread(target=_find_and_move, daemon=True).start()


def run(scene_path, sofa_root=None, gui=True, n_steps=None, blocking=True,
        log_path=None, window=None):
    """Launch runSofa on scene_path.

    gui=True  -> interactive window (design/debug).
    gui=False -> batch mode, n_steps taken from scene.json if not given.
    window    -> optional (x, y, w, h) to place the GUI window (Windows).
    Returns (returncode_or_None, log_path). returncode None if non-blocking.
    """
    scene_path = os.path.abspath(scene_path)
    project_dir = os.path.dirname(scene_path)
    sofa_root = find_sofa(sofa_root)

    if n_steps is None:
        spec_file = os.path.join(project_dir, "scene.json")
        if os.path.isfile(spec_file):
            with open(spec_file) as f:
                n_steps = json.load(f).get("n_steps", 1000)
        else:
            n_steps = 1000

    cmd = [_runsofa_path(sofa_root), "-l", "SofaPython3"]
    if not gui:
        cmd += ["-g", "batch", "-n", str(int(n_steps))]
    cmd += ["-a", scene_path]

    if log_path is None:
        log_path = os.path.join(project_dir, "runsofa.log")

    # cwd = project dir so relative mesh paths in scene.json resolve.
    logf = open(log_path, "w")
    proc = subprocess.Popen(cmd, cwd=project_dir, env=_sofa_env(sofa_root),
                            stdout=logf, stderr=subprocess.STDOUT)
    if gui and window:
        place_sofa_window(window)
    if not blocking:
        return None, log_path
    proc.wait()
    logf.close()
    return proc.returncode, log_path


def main():
    import argparse
    p = argparse.ArgumentParser(description="Run a sofagh project in SOFA")
    p.add_argument("scene", help="path to project scene.py")
    p.add_argument("--sofa-root", default=None)
    p.add_argument("--batch", action="store_true")
    p.add_argument("--steps", type=int, default=None)
    a = p.parse_args()
    rc, log = run(a.scene, a.sofa_root, gui=not a.batch, n_steps=a.steps)
    print(f"runSofa exited {rc}; log: {log}")
    sys.exit(rc or 0)


if __name__ == "__main__":
    main()
