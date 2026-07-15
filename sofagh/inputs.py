"""Actuation input CSV generation.

Format matches Anderson's input/input_grasp.csv: one row per sample at
`sample_rate` Hz, one column per pressure channel (kPa). Channel k is
column k (1-based), matching SofaCavity's `channel` input.

A profile is {"channel": int, "times": [s...], "values": [kPa...]}:
piecewise-linear keyframes, resampled at sample_rate. Outside the
keyframe span the value holds at the nearest endpoint.
"""

import csv


def _interp(t, times, values):
    if not times:
        return 0.0
    if t <= times[0]:
        return values[0]
    if t >= times[-1]:
        return values[-1]
    for i in range(1, len(times)):
        if t <= times[i]:
            t0, t1 = times[i - 1], times[i]
            v0, v1 = values[i - 1], values[i]
            if t1 == t0:
                return v1
            return v0 + (v1 - v0) * (t - t0) / (t1 - t0)
    return values[-1]


def write_csv(profiles, path, sample_rate=100, n_channels=10):
    """Write the actuation CSV. Returns (path, n_rows, duration_seconds)."""
    profiles = list(profiles)
    for p in profiles:
        if not (1 <= int(p["channel"]) <= n_channels):
            raise ValueError(f"channel {p['channel']} outside 1..{n_channels}")
        if len(p["times"]) != len(p["values"]):
            raise ValueError("times and values length mismatch")
        pairs = sorted(zip(p["times"], p["values"]))
        p["times"] = [float(t) for t, _ in pairs]
        p["values"] = [float(v) for _, v in pairs]

    t_end = max((p["times"][-1] for p in profiles if p["times"]), default=0.0)
    n_rows = max(int(round(t_end * sample_rate)) + 1, 1)

    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        for row_i in range(n_rows):
            t = row_i / sample_rate
            row = [0.0] * n_channels
            for p in profiles:
                row[int(p["channel"]) - 1] = _interp(t, p["times"], p["values"])
            writer.writerow(row)

    return path, n_rows, n_rows / sample_rate
