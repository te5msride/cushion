"""Parse simulation outputs back for Grasshopper.

Two artifacts per run:
  monitor/<body>_x.txt : SofaValidation Monitor gnuplot export.
      '#' comment header, then rows: time \t x y z [x y z ...]
  output/output.csv    : controller export, rows: time, p1..pN (kPa).
"""

import os


def read_monitor(project_dir, body_name):
    """Return (times, frames) where frames[i] = [(x,y,z), ...] per particle."""
    path = os.path.join(project_dir, "monitor", body_name + "_x.txt")
    if not os.path.isfile(path):
        raise FileNotFoundError(path)
    times, frames = [], []
    with open(path, errors="replace") as f:
        for line in f:
            # NUL bytes appear when a run is killed mid-write
            line = line.replace("\x00", "").strip()
            if not line or line.startswith("#"):
                continue
            try:
                vals = [float(v) for v in line.split()]
            except ValueError:
                continue  # corrupted row
            t, coords = vals[0], vals[1:]
            if not coords or len(coords) % 3 != 0:
                continue  # truncated row (sim killed mid-write)
            times.append(t)
            frames.append([(coords[i], coords[i + 1], coords[i + 2])
                           for i in range(0, len(coords), 3)])
    return times, frames


def read_pressures(project_dir):
    """Return (times, channels) from output/output.csv.

    channels[k] = list of pressures (kPa) for channel k+1 over time.
    """
    path = os.path.join(project_dir, "output", "output.csv")
    if not os.path.isfile(path):
        raise FileNotFoundError(path)
    times, rows = [], []
    with open(path, errors="replace") as f:
        for line in f:
            line = line.replace("\x00", "").strip()
            if not line:
                continue
            try:
                vals = [float(v) for v in line.split(",")]
            except ValueError:
                continue  # corrupted row
            times.append(vals[0])
            rows.append(vals[1:])
    n = max((len(r) for r in rows), default=0)
    channels = [[r[k] if k < len(r) else 0.0 for r in rows] for k in range(n)]
    return times, channels


def read_cables(project_dir):
    """Parse output/cables.csv.

    Returns (names, times, disp, force): disp[k]/force[k] = history of
    cable k (mm / mN), names from the header comment.
    """
    path = os.path.join(project_dir, "output", "cables.csv")
    if not os.path.isfile(path):
        raise FileNotFoundError(path)
    names, times, rows = [], [], []
    with open(path, errors="replace") as f:
        for line in f:
            line = line.replace("\x00", "").strip()
            if not line:
                continue
            if line.startswith("#"):
                cols = [c.strip() for c in line.lstrip("# ").split(",")][1:]
                names = [c[:-len("_disp_mm")] for c in cols if c.endswith("_disp_mm")]
                continue
            try:
                vals = [float(v) for v in line.split(",")]
            except ValueError:
                continue
            times.append(vals[0])
            rows.append(vals[1:])
    n = len(names) or (max((len(r) for r in rows), default=0) // 2)
    disp = [[r[2 * k] if 2 * k < len(r) else 0.0 for r in rows] for k in range(n)]
    force = [[r[2 * k + 1] if 2 * k + 1 < len(r) else 0.0 for r in rows] for k in range(n)]
    if not names:
        names = [f"cable{k + 1}" for k in range(n)]
    return names, times, disp, force


def list_shape_frames(project_dir, body_name):
    """Sorted list of VTKExporter frame files for a body ([] if none)."""
    import glob
    import re
    pattern = os.path.join(project_dir, "shape", body_name + "*.vtk")
    files = glob.glob(pattern)

    def framekey(p):
        m = re.search(r"(\d+)\.vtk$", os.path.basename(p))
        return int(m.group(1)) if m else -1

    return sorted(files, key=framekey)


def read_vtk_frame(path):
    """Parse a legacy ASCII VTK unstructured grid (VTKExporter output).

    Returns (points, tetras): points = [(x,y,z)...], tetras = [(a,b,c,d)...]
    """
    points, tetras = [], []
    with open(path) as f:
        tokens = f.read().split()
    i = 0
    n = len(tokens)
    while i < n:
        tok = tokens[i].upper()
        if tok == "POINTS":
            npts = int(tokens[i + 1])
            base = i + 3  # skip count + dtype
            for k in range(npts):
                j = base + 3 * k
                points.append((float(tokens[j]), float(tokens[j + 1]),
                               float(tokens[j + 2])))
            i = base + 3 * npts
        elif tok == "CELLS":
            ncells = int(tokens[i + 1])
            j = i + 3
            for _ in range(ncells):
                cnt = int(tokens[j])
                if cnt == 4:
                    tetras.append(tuple(int(tokens[j + m]) for m in range(1, 5)))
                j += cnt + 1
            i = j
        else:
            i += 1
    return points, tetras


def boundary_triangles(tetras):
    """Surface triangles of a tet mesh (faces belonging to exactly one tet)."""
    faces = {}
    for a, b, c, d in tetras:
        for tri in ((a, b, c), (a, b, d), (a, c, d), (b, c, d)):
            key = tuple(sorted(tri))
            if key in faces:
                del faces[key]  # shared face -> interior
            else:
                faces[key] = tri
    return list(faces.values())


def read_log_tail(project_dir, lines=40):
    path = os.path.join(project_dir, "runsofa.log")
    if not os.path.isfile(path):
        return ""
    with open(path, errors="replace") as f:
        return "".join(f.readlines()[-lines:])
