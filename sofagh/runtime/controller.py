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


def _euler_matrix(deg):
    """Rotation matrix R = Rz*Ry*Rx from euler degrees [rx, ry, rz]
    (matches SofaScene's placement decomposition)."""
    rx, ry, rz = [math.radians(a) for a in deg]
    ca, sa = math.cos(rx), math.sin(rx)
    cb, sb = math.cos(ry), math.sin(ry)
    cg, sg = math.cos(rz), math.sin(rz)
    Rx = np.array([[1, 0, 0], [0, ca, -sa], [0, sa, ca]])
    Ry = np.array([[cb, 0, sb], [0, 1, 0], [-sb, 0, cb]])
    Rz = np.array([[cg, -sg, 0], [sg, cg, 0], [0, 0, 1]])
    return Rz @ Ry @ Rx


def fixed_indices(positions, boxes, placement):
    """Node indices inside any axis-aligned design box. If placed,
    inverse-transform world positions into the design frame first."""
    P = np.asarray(positions, dtype=float)
    if placement:
        R = _euler_matrix(placement["rotation"])
        t = np.asarray(placement["translation"], dtype=float)
        P = (P - t) @ R  # R^T (p - t), since (p-t)·R == R^T·(p-t)
    sel = set()
    for bx in boxes:
        x0, y0, z0, x1, y1, z1 = bx
        lo = np.array([min(x0, x1), min(y0, y1), min(z0, z1)])
        hi = np.array([max(x0, x1), max(y0, y1), max(z0, z1)])
        inside = np.all((P >= lo) & (P <= hi), axis=1)
        sel.update(np.nonzero(inside)[0].tolist())
    return sorted(sel)


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
            if body.get("fixations_design"):
                self.fixations.append({
                    "node": body_node,
                    "spring": body_node.fixspring,
                    "boxes": body["fixations_design"],
                    "placement": body.get("placement"),
                })

        # scheduled rigid motion (SofaProtocol): keyframed offset applied
        # through rest positions -- drags the body via its fixations
        self.fixations = []
        self.protocols = []
        for body in self.spec.get("bodies", []):
            proto = body.get("protocol")
            if proto and proto.get("times"):
                self.protocols.append({
                    "node": getattr(self.node, body["name"]),
                    "times": [float(v) for v in proto["times"]],
                    "offsets": [list(map(float, o)) for o in proto["offsets"]],
                    "applied": [0.0, 0.0, 0.0],
                })

        # target pose tracks: bind 3 spread indices at first step
        self.target_monitors = []
        for tgt in self.spec.get("targets", []):
            tnode = getattr(self.node, tgt["name"])
            self.target_monitors.append(tnode.collision.posetrack)

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
            for pm in self.target_monitors:
                n = len(pm.getContext().points.position.value)
                pm.indices = sorted({0, n // 3, (2 * n) // 3})
            for fx in self.fixations:
                idx = fixed_indices(fx["node"].tetras.position.value,
                                    fx["boxes"], fx["placement"])
                fx["spring"].points = idx
                print(f"[sofagh] {fx['node'].name.value} fixed nodes: {len(idx)}")
                if not idx:
                    print("[sofagh] WARNING: fixation selected 0 nodes -> "
                          "body will be unconstrained (check the box vs mesh)")

        # scheduled rigid motion: shift rest positions by the keyframed
        # offset delta (piecewise-linear interpolation)
        for proto in self.protocols:
            ts, offs = proto["times"], proto["offsets"]
            if t <= ts[0]:
                target = offs[0]
            elif t >= ts[-1]:
                target = offs[-1]
            else:
                k = next(i for i in range(1, len(ts)) if t <= ts[i])
                f = (t - ts[k - 1]) / (ts[k] - ts[k - 1] or 1.0)
                target = [offs[k - 1][j] + f * (offs[k][j] - offs[k - 1][j])
                          for j in range(3)]
            delta = [target[j] - proto["applied"][j] for j in range(3)]
            if any(abs(d) > 1e-12 for d in delta):
                dofs = proto["node"].tetras
                rest = np.array(dofs.rest_position.value)
                rest[:, 0] += delta[0]
                rest[:, 1] += delta[1]
                rest[:, 2] += delta[2]
                dofs.rest_position.value = rest.tolist()
                proto["applied"] = target

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
