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
import math
import os
import select
import sys

import numpy as np
import Sofa.Core


def _rot_matrix(axis, angle):
    """Rodrigues rotation matrix for `angle` radians about unit `axis`."""
    a = np.asarray(axis, dtype=float)
    a = a / (np.linalg.norm(a) or 1.0)
    x, y, z = a
    c, s, C = math.cos(angle), math.sin(angle), 1.0 - math.cos(angle)
    return np.array([
        [c + x * x * C,     x * y * C - z * s, x * z * C + y * s],
        [y * x * C + z * s, c + y * y * C,     y * z * C - x * s],
        [z * x * C - y * s, z * y * C + x * s, c + z * z * C],
    ])


def _transform_rest(dofs, translate, angle, axis, pivot):
    """Rigidly move a body's REST shape: rotate `angle` rad about `axis`
    through `pivot`, then translate. Applied to rest positions so the body
    is dragged there through its fixations (same mechanism as SofaProtocol).
    Insertion (translate along axis) and roll (about the same axis) commute,
    so callers may apply either or both per step in any order."""
    rest = np.array(dofs.rest_position.value, dtype=float)
    if abs(angle) > 1e-12:
        rest = (rest - pivot) @ _rot_matrix(axis, angle).T + pivot
    t = np.asarray(translate, dtype=float)
    if np.any(np.abs(t) > 1e-12):
        rest = rest + t
    dofs.rest_position.value = rest.tolist()


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
        # required for the controller to receive input (keypress) events
        self.listening = True
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
        try:
            with open(csv_path) as f:
                for row in csv.reader(f):
                    for k, val in enumerate(row, start=1):
                        self.schedule.setdefault(k, []).append(float(val))
        except FileNotFoundError:
            pass  # teleop runs need no schedule
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
                # Monitor object may be absent (component not shipped in some
                # SOFA builds, e.g. the v26.06 binary bundle); skip if so.
                monitor = getattr(body_node, "monitor_" + body["name"], None)
                if monitor is not None:
                    self.monitors.append((body_node, monitor, body["monitor_points"]))

        # scheduled rigid motion (SofaProtocol): keyframed offset applied
        # through rest positions -- drags the body via its fixations
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
            posetrack = getattr(tnode.collision, "posetrack", None)
            if posetrack is not None:
                self.target_monitors.append(posetrack)

        self.channels = sorted({a["channel"] for a in self.actuators})

        # --- Teleoperation (keyboard) -------------------------------------
        # Live control instead of / alongside the schedule. Enable via a
        # scene.json "teleop" block or the CUSHION_TELEOP env var (so it
        # works with no GH change). Keys are letters (GUI-agnostic):
        #   I / K or + / -  : pressure up / down (active channel)
        #   W / S           : insert  forward / back  (along axis)
        #   A / D           : twist   left / right     (roll about axis)
        #   X               : reset pressure/insert/twist to zero
        tele = self.spec.get("teleop") or {}
        self.tele_on = bool(tele.get("enabled")) or os.environ.get("CUSHION_TELEOP")
        if self.tele_on:
            self.tele_channel = int(tele.get("channel", self.channels[0]
                                              if self.channels else 1))
            self.tele_p_step = float(tele.get("pressure_step", 1.0))   # kPa
            self.tele_p_min = float(tele.get("pressure_min", 0.0))
            self.tele_p_max = float(tele.get("pressure_max", 50.0))
            self.tele_ins_step = float(tele.get("insert_step", 1.0))   # mm
            self.tele_tw_step = float(tele.get("twist_step", 5.0))     # deg
            axis = np.asarray(tele.get("axis", [0.0, 0.0, 1.0]), dtype=float)
            self.tele_axis = axis / (np.linalg.norm(axis) or 1.0)
            self.tele_pivot = (np.asarray(tele["pivot"], dtype=float)
                               if tele.get("pivot") else None)  # else 1st step
            body_name = tele.get("body")
            bodies = self.spec.get("bodies", [])
            if body_name is None and bodies:
                body_name = bodies[0]["name"]
            self.tele_dofs = (getattr(getattr(self.node, body_name), "tetras")
                              if body_name else None)
            self.tele_pressure = 0.0     # commanded, kPa
            self.tele_insert = 0.0        # commanded, mm  (target)
            self.tele_twist = 0.0         # commanded, deg (target)
            self._ins_applied = 0.0
            self._tw_applied = 0.0
            # stdin fallback: works even if the GUI does not forward keys.
            # Type the letters in this terminal + Enter.
            self._stdin_ok = bool(getattr(sys.stdin, "isatty", lambda: False)())
            print("[sofagh] TELEOP on  ch{}  keys: I/K pressure  W/S insert  "
                  "A/D twist  X reset".format(self.tele_channel))
            print("[sofagh] type keys in the SOFA window, OR in this terminal "
                  "+ Enter (e.g. 'iii' then Enter = +3 pressure steps)")

        # Purge stale VTK shape frames from previous runs. VTKExporter uses
        # overwrite=False and restarts its counter at 0 each run, so a
        # shorter run leaves higher-numbered frames behind and SofaShape
        # (which globs the folder) reports an inflated frame count.
        import glob
        shape_dir = os.path.join(self.here, "shape")
        for body in self.spec.get("bodies", []):
            if not body.get("export_shape"):
                continue
            base = os.path.join(shape_dir, body["name"])
            for old in glob.glob(base + "*.vtk") + glob.glob(base + "*.vtu"):
                try:
                    os.remove(old)
                except OSError:
                    pass

        # ContactListeners (B1): (name, object) per (body, target) pair.
        # Read at step end for contact points + count.
        self.listeners = []  # (base_name, listener_object)
        for entry in self.spec.get("contact_listeners", []):
            base, nm = entry if isinstance(entry, (list, tuple)) else (entry, entry)
            obj = getattr(self.node, nm, None)
            if obj is not None:
                self.listeners.append((base, obj))

        if self.save:
            self.out_csv = os.path.join(self.here, "output", "output.csv")
            if os.path.exists(self.out_csv):
                os.remove(self.out_csv)
            # contact map: one row per (step, pair): time, pair, count,
            # then x,y,z per contact point (on the body/finger side)
            self.contacts_csv = os.path.join(self.here, "output", "contacts.csv")
            if os.path.exists(self.contacts_csv):
                os.remove(self.contacts_csv)
            if self.listeners:
                with open(self.contacts_csv, "w", newline="") as f:
                    f.write("# time,pair,count,then x,y,z per contact "
                            "(on body side)\n")
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
            if not getattr(self, "_cam_framed", False):
                self._frame_camera()
            for body_node, monitor, points in self.monitors:
                idx = closest_node_indices(points, body_node.tetras.position.value)
                monitor.indices = idx
                print(f"[sofagh] monitor nodes: {idx}")
            for pm in self.target_monitors:
                n = len(pm.getContext().points.position.value)
                pm.indices = sorted({0, n // 3, (2 * n) // 3})

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

        # teleop: pull any keys typed in the terminal (GUI-independent)
        self._poll_stdin()

        # teleop: apply commanded base insert/twist to the rest shape
        if self.tele_on and self.tele_dofs is not None:
            if self.tele_pivot is None:
                rest0 = np.array(self.tele_dofs.rest_position.value, dtype=float)
                self.tele_pivot = rest0.mean(axis=0)
            d_ins = self.tele_insert - self._ins_applied
            d_tw = math.radians(self.tele_twist - self._tw_applied)
            if abs(d_ins) > 1e-12 or abs(d_tw) > 1e-12:
                _transform_rest(self.tele_dofs, self.tele_axis * d_ins,
                                d_tw, self.tele_axis, self.tele_pivot)
                self._ins_applied = self.tele_insert
                self._tw_applied = self.tele_twist

        # command actuators from the schedule (skips the teleop channel)
        if self.schedule and self.pre_time < t < (self.duration - self.pos_time):
            row = int((t - self.pre_time) * self.sample_rate)
            for act in self.actuators:
                if self.tele_on and act["channel"] == self.tele_channel:
                    continue
                samples = self.schedule.get(act["channel"], [])
                if samples:
                    v = samples[min(row, len(samples) - 1)]
                    act["constraint"].value[0] = v * dt if act["scale_dt"] else v

        # teleop: drive the active channel's pressure live every step
        if self.tele_on:
            for act in self.actuators:
                if act["channel"] == self.tele_channel:
                    v = self.tele_pressure
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

        if t > self.duration and not self.tele_on:
            print("[sofagh] schedule complete, stopping animation")
            self.node.animate.value = False

    def _frame_camera(self):
        """Point the scene camera at the geometry AABB. v26.06 GUIs ignore
        the old Qt view file, so frame it here for a usable default view."""
        if getattr(self, "_cam_framed", False) or self.spec.get("camera"):
            return  # already framed, or explicit camera in scene.json wins
        cam = getattr(self.node, "camera", None)
        if cam is None:
            return
        pts = []
        for body in self.spec.get("bodies", []):
            bn = getattr(self.node, body["name"], None)
            if bn is not None and hasattr(bn, "tetras"):
                pts.append(np.asarray(bn.tetras.position.value))
        for tgt in self.spec.get("targets", []):
            tn = getattr(self.node, tgt["name"], None)
            col = getattr(tn, "collision", None) if tn is not None else None
            pos = getattr(col, "points", None) if col is not None else None
            if pos is not None:
                pts.append(np.asarray(pos.position.value))
        if not pts:
            return
        P = np.vstack(pts)
        lo, hi = P.min(axis=0), P.max(axis=0)
        center = (lo + hi) / 2.0
        diag = float(np.linalg.norm(hi - lo)) or 100.0
        # 3/4 view from -Y / +Z (scene is Z-up, gravity -Z)
        eye = center + np.array([0.0, -1.6, 0.9]) * diag
        try:
            cam.position.value = eye.tolist()
            cam.lookAt.value = center.tolist()
            cam.zNear.value = max(diag * 0.01, 0.1)
            cam.zFar.value = diag * 20.0
            self._cam_framed = True
            print("[sofagh] camera framed on geometry (diag={:.1f}mm)".format(diag))
        except Exception:  # noqa: BLE001
            pass

    def onSimulationInitDoneEvent(self, event):
        self._frame_camera()

    def _poll_stdin(self):
        """Non-blocking read of teleop keys typed into the terminal.
        Line-buffered: user types letters then Enter."""
        if not (self.tele_on and self._stdin_ok):
            return
        while select.select([sys.stdin], [], [], 0)[0]:
            line = sys.stdin.readline()
            if not line:
                break
            for ch in line.strip():
                self._apply_key(ch)

    def onKeypressedEvent(self, event):
        try:
            self._apply_key(event["key"])
        except Exception:  # noqa: BLE001
            pass

    def _apply_key(self, raw):
        if not self.tele_on:
            return
        key = str(raw).upper()
        if key in ("I", "+", "="):
            self.tele_pressure = min(self.tele_p_max,
                                     self.tele_pressure + self.tele_p_step)
        elif key in ("K", "-"):
            self.tele_pressure = max(self.tele_p_min,
                                     self.tele_pressure - self.tele_p_step)
        elif key == "W":
            self.tele_insert += self.tele_ins_step
        elif key == "S":
            self.tele_insert -= self.tele_ins_step
        elif key == "D":
            self.tele_twist += self.tele_tw_step
        elif key == "A":
            self.tele_twist -= self.tele_tw_step
        elif key == "X":
            self.tele_pressure = self.tele_insert = self.tele_twist = 0.0
        else:
            return
        msg = "[teleop] P={:.1f}kPa  insert={:+.1f}mm  twist={:+.1f}deg".format(
            self.tele_pressure, self.tele_insert, self.tele_twist)
        print(msg)                 # -> launching terminal's stdout
        try:
            Sofa.msg_info(self, msg)   # -> in-GUI Log panel
        except Exception:  # noqa: BLE001
            pass

    def onAnimateEndEvent(self, event):
        # contact map: sampled after the step (collision resolved this step)
        if not (self.save and self.listeners):
            return
        t = self.node.time.value
        if t <= self.pre_time:
            return
        # aggregate the per-element-type sub-listeners under their base
        # pair name (point-tri + tri-point + line-line -> one count/pair)
        agg = {}  # base -> [count, coords]
        for base, listener in self.listeners:
            try:
                n = int(listener.getNumberOfContacts())
            except Exception:
                n = 0
            coords = []
            if n:
                try:
                    # getContactPoints -> [(modelA, posA, modelB, posB), ...];
                    # posA is on collisionModel1 (the body). Not all SOFA
                    # builds bind this -> fall back to count only.
                    for tup in listener.getContactPoints():
                        p = tup[1]
                        coords.extend([float(p[0]), float(p[1]), float(p[2])])
                except Exception:
                    coords = []
            slot = agg.setdefault(base, [0, []])
            slot[0] += n
            slot[1].extend(coords)
        with open(self.contacts_csv, "a", newline="") as f:
            w = csv.writer(f)
            for base, (n, coords) in agg.items():
                w.writerow([t, base, n] + coords)
