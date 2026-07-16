"""Generic SOFA scene, driven entirely by scene.json in the same folder.

Run with:  runSofa -l SofaPython3 -a scene.py   (or -g batch -n <steps>)

Scene graph mirrors the Monolithic Unit reference (Nardin/Exley):
FreeMotionAnimationLoop + GenericConstraintSolver, per-body implicit
Euler + SparseLDL, corotational tet FEM, MeshROI overlay stiffening for
membranes/sensors, SurfacePressureConstraint cavities, barycentric
collision/visual surfaces, SofaValidation Monitor on tracked points.

Units: mm, kPa, kg, s (gravity -9810 mm/s^2).
"""

import json
import os

from controller import PressureScheduleController

HERE = os.path.dirname(os.path.abspath(__file__))

PLUGINS = (
    "MultiThreading SoftRobots SofaPython3 SofaLoader SofaSimpleFem SofaEngine "
    "SofaDeformable SofaImplicitOdeSolver SofaConstraint SofaSparseSolver SofaRigid "
    "SofaOpenglVisual Sofa.Component.AnimationLoop "
    "Sofa.Component.Collision.Detection.Algorithm Sofa.Component.Collision.Detection.Intersection "
    "Sofa.Component.Collision.Geometry Sofa.Component.Collision.Response.Contact "
    "Sofa.Component.Topology.Container.Constant Sofa.Component.Constraint.Lagrangian.Solver "
    "Sofa.Component.IO.Mesh Sofa.Component.LinearSolver.Direct Sofa.Component.Mass "
    "Sofa.Component.StateContainer Sofa.Component.LinearSolver.Iterative "
    "Sofa.Component.Mapping.Linear Sofa.Component.ODESolver.Backward Sofa.Component.Setting "
    "Sofa.Component.SolidMechanics.FEM.Elastic Sofa.Component.Visual "
    "Sofa.Component.Constraint.Lagrangian.Correction Sofa.Component.SolidMechanics.Spring "
    "Sofa.GL.Component.Rendering3D Sofa.Component.LinearSolver.Preconditioner "
    "Sofa.Component.Engine.Select Sofa.Component.Mapping.NonLinear "
    "Sofa.Component.Constraint.Lagrangian.Model Sofa.Component.Topology.Container.Dynamic "
    "SofaValidation SofaExporter"
)


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
    node.addObject("OglModel", position=positions, triangles=triangles,
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
    col.addObject("MechanicalObject")
    col.addObject("TriangleCollisionModel", name="target")
    col.addObject("LineCollisionModel", name="target")
    col.addObject("PointCollisionModel", name="target")
    col.addObject("RigidMapping")

    visu = t.addChild("visual")
    visu.addObject("MeshSTLLoader", name="loader", filename=_abspath(tgt["mesh"]))
    visu.addObject("OglModel", src="@loader",
                   color=tgt.get("color", [0.3, 0.3, 0.3, 1.0]))
    visu.addObject("RigidMapping")
    return t


def _add_body(rootNode, body, spec):
    b = rootNode.addChild(body["name"])
    b.addObject("EulerImplicitSolver", name="odesolver",
                rayleighStiffness=0.1, rayleighMass=0.1)
    b.addObject("SparseLDLSolver", name="preconditioner")
    b.addObject("MeshVTKLoader", name="loader",
                filename=_abspath(body["volume_vtk"]))
    b.addObject("TetrahedronSetTopologyContainer", tetrahedra="@loader.tetrahedra",
                position="@loader.position", name="container")
    b.addObject("MechanicalObject", name="tetras", template="Vec3")
    b.addObject("LinearSolverConstraintCorrection")
    b.addObject("TetrahedronFEMForceField", template="Vec3", name="FEM",
                method="large",
                poissonRatio=body.get("poisson_ratio", 0.4),
                youngModulus=body.get("young_modulus", 18.0))
    b.addObject("UniformMass", totalMass=body.get("total_mass", 0.05))

    # Fixations: rigidly spring selected nodes to rest shape
    for fi, box in enumerate(body.get("fixations", [])):
        b.addObject("BoxROI", name=f"fixBox{fi}", box=box, drawBoxes=True,
                    doUpdate=False)
        b.addObject("RestShapeSpringsForceField", points=f"@fixBox{fi}.indices",
                    stiffness=1e12, angularStiffness=1e12)

    # Monitor tracked points (indices bound by controller on first step)
    if body.get("monitor_points"):
        b.addObject("Monitor", name="monitor_" + body["name"], template="Vec3d",
                    listening=1, showPositions=True, PositionsColor="1 0 1 1",
                    sizeFactor=10, ExportPositions=True,
                    fileName=os.path.join(HERE, "monitor", body["name"]))

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
                    filename=_abspath(region["mesh"]))
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
                    filename=_abspath(cavity["mesh"]))
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
                      filename=_abspath(body["collision_mesh"]))
        col.addObject("MeshTopology", src="@loader", name="topo")
        col.addObject("MechanicalObject", name="collisMech")
        col.addObject("TriangleCollisionModel", selfCollision=False)
        col.addObject("LineCollisionModel", selfCollision=False,
                      name=body.get("contact_group", body["name"]))
        col.addObject("PointCollisionModel", selfCollision=False)
        col.addObject("BarycentricMapping")

    # Visual surfaces (barycentric-mapped onto the deforming volume)
    for vi, visual in enumerate(body.get("visuals", [])):
        v = b.addChild(f"visual{vi}")
        v.addObject("MeshSTLLoader", name="loader",
                    filename=_abspath(visual["mesh"]))
        v.addObject("OglModel", src="@loader",
                    color=visual.get("color", [0.7, 0.9, 0.9, 0.5]))
        v.addObject("BarycentricMapping")

    return b


def createScene(rootNode):
    with open(os.path.join(HERE, "scene.json")) as f:
        spec = json.load(f)

    rootNode.addObject("RequiredPlugin", pluginName=PLUGINS)
    rootNode.dt = spec.get("dt", 0.01)
    rootNode.gravity.value = spec.get("gravity", [0.0, 0.0, -9810.0])
    rootNode.addObject("VisualStyle",
                       displayFlags="showVisualModels hideBehaviorModels "
                                    "hideCollisionModels hideBoundingCollisionModels "
                                    "hideForceFields showInteractionForceFields hideWireframe")
    rootNode.addObject("FreeMotionAnimationLoop")
    rootNode.addObject("GenericConstraintSolver", tolerance=1e-12,
                       maxIterations=10000)

    contacts = spec.get("contacts") or {}
    if contacts.get("enabled", True):
        rootNode.addObject("DefaultPipeline")
        rootNode.addObject("BruteForceBroadPhase")
        rootNode.addObject("BVHNarrowPhase")
        rules = contacts.get("rules", "")
        if rules:
            rootNode.addObject("RuleBasedContactManager",
                               response=contacts.get("response",
                                                     "FrictionContactConstraint"),
                               rules=rules)
        else:
            rootNode.addObject("DefaultContactManager",
                               response=contacts.get("response",
                                                     "FrictionContactConstraint"),
                               responseParams=contacts.get("response_params",
                                                           "mu=0.9"))
        rootNode.addObject("LocalMinDistance", name="Proximity",
                           alarmDistance=contacts.get("alarm_distance", 5.0),
                           contactDistance=contacts.get("contact_distance", 1.0),
                           angleCone=0.1)

    rootNode.addObject("BackgroundSetting", color=[1.0, 1.0, 1.0, 1.0])
    rootNode.addObject("OglSceneFrame", style="Arrows", alignment="TopRight")

    cam = spec.get("camera")
    if cam:
        rootNode.addObject("InteractiveCamera", name="camera",
                           position=cam["position"], lookAt=cam["look_at"])

    if spec.get("floor"):
        _add_floor(rootNode, spec["floor"])

    for tgt in spec.get("targets", []):
        _add_target(rootNode, tgt)

    for body in spec.get("bodies", []):
        _add_body(rootNode, body, spec)

    rootNode.addObject(PressureScheduleController(node=rootNode, spec=spec,
                                                  here=HERE))
    return rootNode
