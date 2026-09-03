"""Generic SOFA scene, driven entirely by scene.json in the same folder.

Run with:  runSofa -l SofaPython3 -a scene.py   (or -g batch -n <steps>)

Scene graph mirrors the Monolithic Unit reference (Nardin/Exley):
FreeMotionAnimationLoop + GenericConstraintSolver, per-body implicit
Euler + SparseLDL, corotational tet FEM, MeshROI overlay stiffening for
membranes/sensors, SurfacePressureConstraint cavities, barycentric
collision/visual surfaces, Monitor on tracked points where available
(SofaValidation ships in v24.06 but not the v26.06 binary bundle).

Units: mm, kPa, kg, s (gravity -9810 mm/s^2).
"""

import json
import os

from controller import PressureScheduleController

HERE = os.path.dirname(os.path.abspath(__file__))

# Granular Sofa.Component.* modules exist in both v24.06 and v26.06. The old
# monolithic aliases (SofaLoader, SofaConstraint, SofaExporter, ...) were
# removed in v24.12, so they are omitted here for forward compatibility.
# VTKExporter (old SofaExporter) now lives in Sofa.Component.Playback.
# Each name is loaded independently (see _load_plugins) so a module that a
# given release renames or drops warns instead of aborting the whole scene.
PLUGINS = [
    "MultiThreading",
    "SoftRobots",
    "SofaPython3",
    "SofaValidation",  # Monitor: present in v24.06, absent from v26.06 bundle
                       # (loaded tolerantly; skipped where unavailable)
    "Sofa.Component.AnimationLoop",
    "Sofa.Component.Collision.Detection.Algorithm",
    "Sofa.Component.Collision.Detection.Intersection",
    "Sofa.Component.Collision.Geometry",
    "Sofa.Component.Collision.Response.Contact",
    "Sofa.Component.Constraint.Lagrangian.Correction",
    "Sofa.Component.Constraint.Lagrangian.Model",
    "Sofa.Component.Constraint.Lagrangian.Solver",
    "Sofa.Component.Engine.Select",
    "Sofa.Component.IO.Mesh",
    "Sofa.Component.LinearSolver.Direct",
    "Sofa.Component.LinearSolver.Iterative",
    "Sofa.Component.LinearSolver.Preconditioner",
    "Sofa.Component.Mapping.Linear",
    "Sofa.Component.Mapping.NonLinear",
    "Sofa.Component.Mass",
    "Sofa.Component.ODESolver.Backward",
    "Sofa.Component.Playback",  # VTKExporter (was in SofaExporter)
    "Sofa.Component.Setting",
    "Sofa.Component.SolidMechanics.FEM.Elastic",
    "Sofa.Component.SolidMechanics.Spring",
    "Sofa.Component.StateContainer",
    "Sofa.Component.Topology.Container.Constant",
    "Sofa.Component.Topology.Container.Dynamic",
    "Sofa.Component.Visual",
    "Sofa.GL.Component.Rendering3D",
]


def _load_plugins(rootNode):
    """Load each plugin on its own so a name a given SOFA release does not
    ship (v24.06 vs v26.06 module churn) is logged and skipped instead of
    killing the scene. Check runsofa.log for '[cushion] plugin skipped'."""
    for p in PLUGINS:
        try:
            # sanitise the node name: dotted plugin ids trip the
            # special-character scene check (v26.06) if used verbatim.
            rootNode.addObject("RequiredPlugin", name=p.replace(".", "_"),
                               pluginName=p)
        except Exception as exc:  # noqa: BLE001
            print(f"[cushion] plugin skipped: {p} ({exc})")


def _try_add(node, comp, **kwargs):
    """addObject `comp`, returning the object or None if this SOFA build
    does not provide that component (unknown types raise in SofaPython3).
    Version-agnostic: no dependency on any factory-introspection API."""
    try:
        return node.addObject(comp, **kwargs)
    except Exception:  # noqa: BLE001
        return None


def _add_first(node, comps, **kwargs):
    """addObject the first component in `comps` this SOFA build provides.
    Lets one scene span releases that renamed components (e.g.
    GenericConstraintSolver -> BlockGaussSeidelConstraintSolver in v25.12,
    DefaultContactManager -> CollisionResponse in v24.12)."""
    for comp in comps:
        obj = _try_add(node, comp, **kwargs)
        if obj is not None:
            return obj
    print(f"[cushion] none of {comps} available in this SOFA build")
    return None


def _abspath(rel):
    return rel if os.path.isabs(rel) else os.path.join(HERE, rel)


def _add_floor(rootNode, floor):
    cx, cy, cz = floor.get("point", [0.0, 0.0, 0.0])
    s = floor.get("size", 400.0) / 2.0
    positions = [[cx - s, cy - s, cz], [cx + s, cy - s, cz],
                 [cx + s, cy + s, cz], [cx - s, cy + s, cz]]
    triangles = [[0, 1, 2], [0, 2, 3]]
    node = rootNode.addChild("floor")
    node.addObject("MeshTopology", position=positions, triangles=triangles)
    node.addObject("MechanicalObject")
    node.addObject("TriangleCollisionModel", simulated=False, moving=False)
    node.addObject("LineCollisionModel", simulated=False, moving=False)
    node.addObject("PointCollisionModel", simulated=False, moving=False)
    # OglModel is a BaseState; keep it in its own child so it does not clash
    # with the node's MechanicalObject (v26.06 flags two states per node).
    node.addChild("visual").addObject("OglModel", position=positions,
                                      triangles=triangles,
                                      color=[0.5, 0.5, 0.5, 0.4])


def _add_target(rootNode, tgt):
    """Rigid interaction object (graspable target). Approximation: unit
    rotational inertia (UniformMass totalMass on Rigid3); fine for
    objects that mostly translate / rest until grasped."""
    t = rootNode.addChild(tgt["name"])
    t.addObject("EulerImplicitSolver", name="odesolver")
    t.addObject("SparseLDLSolver", name="linearSolver")
    t.addObject("MechanicalObject", template="Rigid3",
                position=tgt.get("frame", [0, 0, 0, 0, 0, 0, 1]))
    t.addObject("UniformMass", totalMass=tgt.get("mass", 0.01))
    t.addObject("UncoupledConstraintCorrection")

    col = t.addChild("collision")
    col.addObject("MeshSTLLoader", name="loader", filename=_abspath(tgt["mesh"]))
    col.addObject("MeshTopology", src="@loader")
    col.addObject("MechanicalObject", name="points")
    col.addObject("TriangleCollisionModel", name="target_tri")
    col.addObject("LineCollisionModel", name="target")
    col.addObject("PointCollisionModel", name="target_pt")
    col.addObject("RigidMapping")
    # 3-point pose track (indices bound by the controller) so
    # AnimationPreview can replay the target's rigid motion
    if _try_add(col, "Monitor", name="posetrack", template="Vec3d", listening=1,
                showPositions=False, ExportPositions=True,
                fileName=os.path.join(HERE, "monitor", "target_" + tgt["name"])) is None:
        print("[cushion] Monitor unavailable in this SOFA build; "
              "target pose-track export disabled")

    visu = t.addChild("visual")
    visu.addObject("MeshSTLLoader", name="loader", filename=_abspath(tgt["mesh"]))
    visu.addObject("OglModel", src="@loader",
                   color=tgt.get("color", [0.3, 0.3, 0.3, 1.0]))
    visu.addObject("RigidMapping")
    return t


def _add_body(rootNode, body, spec):
    # rigid placement (SofaBody.orient): applied by every mesh loader
    pl = body.get("placement") or {}
    place = ({"rotation": pl["rotation"], "translation": pl["translation"]}
             if pl else {})

    b = rootNode.addChild(body["name"])
    b.addObject("EulerImplicitSolver", name="odesolver",
                rayleighStiffness=0.1, rayleighMass=0.1)
    b.addObject("SparseLDLSolver", name="preconditioner")
    b.addObject("MeshVTKLoader", name="loader",
                filename=_abspath(body["volume_vtk"]), **place)
    b.addObject("TetrahedronSetTopologyContainer", tetrahedra="@loader.tetrahedra",
                position="@loader.position", name="container")
    b.addObject("MechanicalObject", name="tetras", template="Vec3")
    b.addObject("LinearSolverConstraintCorrection")
    b.addObject("TetrahedronFEMForceField", template="Vec3", name="FEM",
                method="large",
                poissonRatio=body.get("poisson_ratio", 0.4),
                youngModulus=body.get("young_modulus", 18.0))
    b.addObject("UniformMass", totalMass=body.get("total_mass", 0.05))

    # Fixations: axis-aligned BoxROI springs selected nodes to rest.
    # (Placed bodies get a world-AABB box computed in SofaScene, so no
    # winding-fragile orientedBox is needed.)
    for fi, box in enumerate(body.get("fixations", [])):
        b.addObject("BoxROI", name=f"fixBox{fi}", box=box, drawBoxes=True,
                    doUpdate=False)
        b.addObject("RestShapeSpringsForceField", points=f"@fixBox{fi}.indices",
                    stiffness=1e12, angularStiffness=1e12)

    # Monitor tracked points (indices bound by controller on first step)
    if body.get("monitor_points"):
        if _try_add(b, "Monitor", name="monitor_" + body["name"], template="Vec3d",
                    listening=1, showPositions=True, PositionsColor="1 0 1 1",
                    sizeFactor=10, ExportPositions=True, ExportForces=True,
                    fileName=os.path.join(HERE, "monitor", body["name"])) is None:
            print("[cushion] Monitor unavailable in this SOFA build; "
                  f"point tracking disabled for body '{body['name']}'")

    # Full deformed-shape export (legacy VTK series, read back by SofaShape)
    if body.get("export_shape"):
        os.makedirs(os.path.join(HERE, "shape"), exist_ok=True)
        b.addObject("VTKExporter",
                    filename=os.path.join(HERE, "shape", body["name"]),
                    listening=True, XMLformat=False, overwrite=False,
                    tetras=True,
                    exportEveryNumberOfSteps=int(body["export_shape"]))

    # Stiffened sub-regions (membranes / sensors): MeshROI overlay FEM
    for region in body.get("regions", []):
        r = b.addChild(region["name"])
        r.addObject("MeshSTLLoader", name="ROIloader",
                    filename=_abspath(region["mesh"]), **place)
        r.addObject("MeshROI", name="ROI", doUpdate="0",
                    position="@../loader.position",
                    tetrahedra="@../loader.tetrahedra",
                    ROIposition="@ROIloader.position",
                    ROItriangles="@ROIloader.triangles")
        r.addObject("TetrahedronSetTopologyContainer",
                    position="@loader.position",
                    tetrahedra="@ROI.tetrahedraInROI", name="container")
        r.addObject("TetrahedronFEMForceField", template="Vec3", method="large",
                    poissonRatio=region.get("poisson_ratio", 0.4),
                    youngModulus=region.get("young_modulus", 2.0e3))

    # Pneumatic cavities
    for cavity in body.get("cavities", []):
        c = b.addChild(cavity["name"])
        c.addObject("MeshSTLLoader", name="loader",
                    filename=_abspath(cavity["mesh"]), **place)
        c.addObject("MeshTopology", src="@loader", name="topo")
        c.addObject("MechanicalObject", name="cavity")
        c.addObject("SurfacePressureConstraint", name="SurfacePressureConstraint",
                    template="Vec3", value=0.0, triangles="@topo.triangles",
                    valueType="pressure")
        c.addObject("BarycentricMapping", name="mapping",
                    mapForces=False, mapMasses=False)

    # Tendons/cables (SoftRobots CableConstraint, points mapped into volume)
    # per-channel colors, same palette as docs: 1 red, 2 green, 3 blue,
    # 4 yellow, 5 magenta, 6 cyan (repeats after 6)
    palette = [[0.9, 0.15, 0.15, 1.0], [0.15, 0.8, 0.15, 1.0],
               [0.15, 0.3, 0.9, 1.0], [0.9, 0.8, 0.1, 1.0],
               [0.85, 0.2, 0.85, 1.0], [0.1, 0.8, 0.8, 1.0]]
    for cable in body.get("cables", []):
        color = palette[(int(cable.get("channel", 1)) - 1) % len(palette)]
        c = b.addChild(cable["name"])
        c.addObject("MechanicalObject", position=cable["points"],
                    showObject=True, showObjectScale=2.5, drawMode=1,
                    showColor=color)
        kwargs = dict(name="CableConstraint",
                      indices=list(range(len(cable["points"]))),
                      value=0.0,
                      valueType=cable.get("value_type", "displacement"))
        if cable.get("pull_point"):
            kwargs["pullPoint"] = cable["pull_point"]
            kwargs["hasPullPoint"] = True
        else:
            kwargs["hasPullPoint"] = False
        c.addObject("CableConstraint", **kwargs)
        c.addObject("BarycentricMapping", name="mapping",
                    mapForces=False, mapMasses=False)

    # Collision surface
    if body.get("collision_mesh"):
        col = b.addChild("collision")
        col.addObject("MeshSTLLoader", name="loader",
                      filename=_abspath(body["collision_mesh"]), **place)
        col.addObject("MeshTopology", src="@loader", name="topo")
        col.addObject("MechanicalObject", name="collisMech")
        col.addObject("TriangleCollisionModel", selfCollision=False,
                      name=body["name"] + "_tri")
        col.addObject("LineCollisionModel", selfCollision=False,
                      name=body.get("contact_group", body["name"]))
        col.addObject("PointCollisionModel", selfCollision=False,
                      name=body["name"] + "_pt")
        col.addObject("BarycentricMapping")

    # Visual surfaces (barycentric-mapped onto the deforming volume)
    for vi, visual in enumerate(body.get("visuals", [])):
        v = b.addChild(f"visual{vi}")
        v.addObject("MeshSTLLoader", name="loader",
                    filename=_abspath(visual["mesh"]), **place)
        v.addObject("OglModel", src="@loader",
                    color=visual.get("color", [0.7, 0.9, 0.9, 0.5]))
        v.addObject("BarycentricMapping")

    return b


def createScene(rootNode):
    with open(os.path.join(HERE, "scene.json")) as f:
        spec = json.load(f)

    _load_plugins(rootNode)
    rootNode.dt = spec.get("dt", 0.01)
    rootNode.gravity.value = spec.get("gravity", [0.0, 0.0, -9810.0])
    rootNode.addObject("VisualStyle",
                       displayFlags="showVisualModels hideBehaviorModels "
                                    "hideCollisionModels hideBoundingCollisionModels "
                                    "hideForceFields showInteractionForceFields hideWireframe")
    rootNode.addObject("FreeMotionAnimationLoop")
    # GenericConstraintSolver was split into method-specific solvers in
    # v25.12; BlockGaussSeidelConstraintSolver is the ProjectedGaussSeidel
    # (default) replacement. Both take tolerance + maxIterations.
    _add_first(rootNode,
               ("GenericConstraintSolver", "BlockGaussSeidelConstraintSolver"),
               tolerance=1e-12, maxIterations=10000)

    contacts = spec.get("contacts") or {}
    if contacts.get("enabled", True):
        # DefaultPipeline was renamed CollisionPipeline (alias removed v24.12)
        _add_first(rootNode, ("CollisionPipeline", "DefaultPipeline"))
        rootNode.addObject("BruteForceBroadPhase")
        rootNode.addObject("BVHNarrowPhase")
        rules = contacts.get("rules", "")
        if rules:
            rootNode.addObject("RuleBasedContactManager",
                               response=contacts.get("response",
                                                     "FrictionContactConstraint"),
                               rules=rules)
        else:
            # DefaultContactManager alias was removed in v24.12 -> CollisionResponse
            _add_first(rootNode, ("DefaultContactManager", "CollisionResponse"),
                       response=contacts.get("response",
                                             "FrictionContactConstraint"),
                       responseParams=contacts.get("response_params", "mu=0.9"))
        rootNode.addObject("LocalMinDistance", name="Proximity",
                           alarmDistance=contacts.get("alarm_distance", 5.0),
                           contactDistance=contacts.get("contact_distance", 1.0),
                           angleCone=0.1)

    rootNode.addObject("BackgroundSetting", color=[1.0, 1.0, 1.0, 1.0])
    rootNode.addObject("OglSceneFrame", style="Arrows", alignment="TopRight")

    # Always add a camera. v26.06 GUIs (imgui/glfw) ignore the old Qt
    # .qglviewer.view file, so without one SOFA auto-creates a poorly-framed
    # camera. If scene.json gives explicit values use them, else the
    # controller frames it to the geometry AABB at load (see _frame_camera).
    cam = spec.get("camera")
    if cam:
        rootNode.addObject("InteractiveCamera", name="camera",
                           position=cam["position"], lookAt=cam["look_at"])
    else:
        rootNode.addObject("InteractiveCamera", name="camera")

    if spec.get("floor"):
        _add_floor(rootNode, spec["floor"])

    for tgt in spec.get("targets", []):
        _add_target(rootNode, tgt)

    for body in spec.get("bodies", []):
        _add_body(rootNode, body, spec)

    # ContactListeners: report contact points + count per (body, target)
    # pair to the controller (B1 grasp contact map). NOTE: ContactListener
    # exposes contact GEOMETRY only -- points/count/normals, not the
    # resolved contact force (that is the constraint solver's lambda).
    #
    # LocalMinDistance culls face-face contacts, so a Triangle-Triangle
    # listener sees ~nothing. Watch every element pair that actually fires
    # (point-into-face + edge-edge, both orders) and aggregate them under
    # one base name "cl_<body>__<target>" in the controller. LocalMinDistance
    # assigns each physical contact to a single element pair, so summing
    # across pairs does not double-count.
    listener_map = []  # [base_name, listener_name]
    if contacts.get("enabled", True):
        for body in spec.get("bodies", []):
            if not body.get("collision_mesh"):
                continue
            bn = body["name"]
            b_line = body.get("contact_group", bn)
            for tgt in spec.get("targets", []):
                tn = tgt["name"]
                base = "cl_%s__%s" % (bn, tn)
                # (suffix, body model, target model)
                combos = [
                    ("pt_tri", "%s_pt" % bn, "target_tri"),
                    ("tri_pt", "%s_tri" % bn, "target_pt"),
                    ("ln_ln", b_line, "target"),
                ]
                for suffix, bmodel, tmodel in combos:
                    nm = "%s_%s" % (base, suffix)
                    rootNode.addObject(
                        "ContactListener", name=nm,
                        collisionModel1="@/%s/collision/%s" % (bn, bmodel),
                        collisionModel2="@/%s/collision/%s" % (tn, tmodel))
                    listener_map.append([base, nm])
    spec["contact_listeners"] = listener_map

    rootNode.addObject(PressureScheduleController(node=rootNode, spec=spec,
                                                  here=HERE))
    return rootNode
