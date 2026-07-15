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
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            vals = [float(v) for v in line.split()]
            t, coords = vals[0], vals[1:]
            if len(coords) % 3 != 0:
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
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            vals = [float(v) for v in line.split(",")]
            times.append(vals[0])
            rows.append(vals[1:])
    n = max((len(r) for r in rows), default=0)
    channels = [[r[k] if k < len(r) else 0.0 for r in rows] for k in range(n)]
    return times, channels


def read_log_tail(project_dir, lines=40):
    path = os.path.join(project_dir, "runsofa.log")
    if not os.path.isfile(path):
        return ""
    with open(path, errors="replace") as f:
        return "".join(f.readlines()[-lines:])
