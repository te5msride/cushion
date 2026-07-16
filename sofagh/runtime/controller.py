"""Generic pressure-schedule controller for sofagh scenes.

Responsibilities (generalized from the Monolithic Unit WholeGripperController):
  * read input.csv (rows @ sample_rate Hz, column k = channel k pressure, kPa)
  * each step, drive every cavity's SurfacePressureConstraint from its channel
    (SOFA constraint 'value' is pressure * dt — the dt scaling lives here)
  * bind Monitor indices to the mesh nodes closest to the requested
    monitor_points (first step, after loading)
  * export output/output.csv rows: time, p1..pN (measured, kPa)
  * stop animation pre_time + input + pos_time after start
"""

import csv
import os

import numpy as np
import Sofa.Core


def closest_node_indices(points, positions):
    positions = np.asarray(positions)
    out = []
    for p in points:
        d = np.linalg.norm(positions - np.asarray(p, dtype=float), axis=1)
        out.append(int(np.argmin(d)))
    return out


class PressureScheduleController(Sofa.Core.Controller):

    def __init__(self, *args, **kwargs):
        Sofa.Core.Controller.__init__(self, *args, **kwargs)
        self.node = kwargs["node"]
        self.spec = kwargs["spec"]
        self.here = kwargs["here"]

        self.sample_rate = self.spec.get("sample_rate", 100)
        self.pre_time = self.spec.get("pre_time", 0.1)
        self.pos_time = self.spec.get("pos_time", 0.3)
        self.save = self.spec.get("save_output", True)
        self.first_step = True
        self._print_counter = 0

        # schedule[channel] = list of pressures (kPa) at sample_rate
        self.schedule = {}
        csv_path = os.path.join(self.here, self.spec.get("input_csv", "input.csv"))
        with open(csv_path) as f:
            for row in csv.reader(f):
                for k, val in enumerate(row, start=1):
                    self.schedule.setdefault(k, []).append(float(val))
        n_rows = len(next(iter(self.schedule.values()), []))
        self.duration = self.pre_time + n_rows / self.sample_rate + self.pos_time

        # actuators: pressures (x dt), cable force (x dt), cable
        # displacement (raw mm). One entry per constraint + channel.
        self.actuators = []
        self.monitors = []  # (body_node, monitor_object, points)
        for body in self.spec.get("bodies", []):
            body_node = getattr(self.node, body["name"])
            for cavity in body.get("cavities", []):
                self.actuators.append({
                    "constraint": getattr(body_node, cavity["name"]).SurfacePressureConstraint,
                    "channel": int(cavity["channel"]),
                    "kind": "pressure", "scale_dt": True, "unit": "kPa"})
            for cable in body.get("cables", []):
                is_force = cable.get("value_type", "displacement") == "force"
                self.actuators.append({
                    "constraint": getattr(body_node, cable["name"]).CableConstraint,
                    "channel": int(cable["channel"]),
                    "kind": "cable", "scale_dt": is_force,
                    "name": f"{body['name']}.{cable['name']}",
                    "unit": "mN" if is_force else "mm"})
            if body.get("monitor_points"):
                monitor = getattr(body_node, "monitor_" + body["name"])
                self.monitors.append((body_node, monitor, body["monitor_points"]))

        self.channels = sorted({a["channel"] for a in self.actuators})

        if self.save:
            self.out_csv = os.path.join(self.here, "output", "output.csv")
            if os.path.exists(self.out_csv):
                os.remove(self.out_csv)
            # cable telemetry: displacement + force per cable per step
            self.cables = [a for a in self.actuators if a["kind"] == "cable"]
            self.cables_csv = os.path.join(self.here, "output", "cables.csv")
            if os.path.exists(self.cables_csv):
                os.remove(self.cables_csv)
            if self.cables:
                with open(self.cables_csv, "w", newline="") as f:
                    names = [a["name"] for a in self.cables]
                    f.write("# time," + ",".join(
                        f"{n}_disp_mm,{n}_force_mN" for n in names) + "\n")

        summary = [f"ch{a['channel']}:{a['kind']}" for a in self.actuators]
        print(f"[sofagh] actuators: {summary}, duration: {self.duration:.2f} s")

    def onAnimateBeginEvent(self, event):
        t = self.node.time.value
        dt = self.node.dt.value

        if self.first_step:
            self.first_step = False
            for body_node, monitor, points in self.monitors:
                idx = closest_node_indices(points, body_node.tetras.position.value)
                monitor.indices = idx
                print(f"[sofagh] monitor nodes: {idx}")

        # command actuators from the schedule
        if self.pre_time < t < (self.duration - self.pos_time):
            row = int((t - self.pre_time) * self.sample_rate)
            for act in self.actuators:
                samples = self.schedule.get(act["channel"], [])
                if samples:
                    v = samples[min(row, len(samples) - 1)]
                    act["constraint"].value[0] = v * dt if act["scale_dt"] else v

        # measured values (pressure kPa / cable force mN)
        measured = {}
        for act in self.actuators:
            if act["kind"] == "pressure":
                measured[act["channel"]] = float(act["constraint"].pressure.value) / dt
            else:
                measured[act["channel"]] = float(act["constraint"].force.value) / dt

        self._print_counter += 1
        if self._print_counter >= 100:
            self._print_counter = 0
            units = {a["channel"]: a["unit"] for a in self.actuators}
            summary = ", ".join(
                f"ch{c}={measured[c]:.2f}{'kPa' if units[c] == 'kPa' else 'mN'}"
                for c in self.channels)
            print(f"[sofagh] t={t:.2f}s  {summary}")

        if self.save and t > self.pre_time:
            with open(self.out_csv, "a", newline="") as f:
                writer = csv.writer(f)
                writer.writerow([t] + [measured.get(c, 0.0) for c in self.channels])
            if self.cables:
                row = [t]
                for a in self.cables:
                    row.append(float(a["constraint"].displacement.value))
                    row.append(float(a["constraint"].force.value) / dt)
                with open(self.cables_csv, "a", newline="") as f:
                    csv.writer(f).writerow(row)

        if t > self.duration:
            print("[sofagh] schedule complete, stopping animation")
            self.node.animate.value = False
