"""Tetrahedral meshing via gmsh (STEP or watertight STL -> VTK legacy).

Mirrors Anderson's data/models/gmshe.py settings (Delaunay 3D, linear
tets, one smoothing pass) so results stay comparable to the Monolithic
Unit reference pipeline.
"""

import os


def volume_mesh(input_path, output_path=None, mesh_size=1.0, algorithm3d=1,
                verbose=False, voids=None):
    """Tet-mesh a solid and write a legacy VTK file SOFA's MeshVTKLoader reads.

    input_path: .step/.stp (preferred, exact geometry) or closed .stl surface.
    mesh_size:  gmsh Mesh.MeshSizeFactor (Anderson used 0.22 for jvolume).
    voids:      optional closed .stl surfaces fully inside the solid --
                meshed as internal cavities (no tets inside). Requires
                the .stl route for the outer surface too.
    Returns the output path.
    """
    import gmsh

    if output_path is None:
        output_path = os.path.splitext(input_path)[0] + ".vtk"

    ext = os.path.splitext(input_path)[1].lower()
    if voids and ext not in (".stl",):
        raise ValueError("voids require the outer surface as .stl")

    gmsh.initialize()
    try:
        gmsh.option.setNumber("General.Terminal", 1 if verbose else 0)
        gmsh.model.add("sofagh_volume")

        if ext in (".step", ".stp"):
            gmsh.model.occ.importShapes(input_path)
            gmsh.model.occ.removeAllDuplicates()
            gmsh.model.occ.synchronize()
            entities = gmsh.model.getEntities(3)
            if len(entities) > 1:
                gmsh.model.occ.fragment([(3, e[1]) for e in entities], [])
                gmsh.model.occ.synchronize()
        elif ext == ".stl":
            # Direct route: weld the triangle soup, keep the original
            # triangulation as the volume boundary (no surface
            # reparametrization — that route fails on many STLs with
            # "Invalid exterior boundary mesh for parametrization").
            # Voids: each void .stl becomes an inner surface loop, so
            # the tet mesh excludes the cavity interiors.
            gmsh.merge(input_path)
            outer = list(gmsh.model.getEntities(2))
            shell_groups = [outer]
            for vf in (voids or []):
                before = set(gmsh.model.getEntities(2))
                gmsh.merge(vf)
                shell_groups.append(
                    [s for s in gmsh.model.getEntities(2) if s not in before])
            gmsh.model.mesh.removeDuplicateNodes()
            gmsh.model.mesh.createTopology()
            if not shell_groups[0]:
                raise ValueError("no surface found in STL")
            loops = [gmsh.model.geo.addSurfaceLoop([s[1] for s in grp])
                     for grp in shell_groups if grp]
            gmsh.model.geo.addVolume(loops)  # first loop outer, rest holes
            gmsh.model.geo.synchronize()
        else:
            raise ValueError(f"Unsupported input for volume meshing: {ext}")

        gmsh.option.setNumber("Mesh.Algorithm3D", algorithm3d)  # 1=Delaunay, 4=Netgen
        gmsh.option.setNumber("Mesh.RecombinationAlgorithm", 3)
        gmsh.option.setNumber("Mesh.RecombineAll", 0)
        gmsh.option.setNumber("Mesh.SubdivisionAlgorithm", 0)
        gmsh.option.setNumber("Mesh.Smoothing", 1)
        gmsh.option.setNumber("Mesh.MeshSizeFactor", mesh_size)
        gmsh.option.setNumber("Mesh.CharacteristicLengthMin", 0)
        gmsh.option.setNumber("Mesh.CharacteristicLengthMax", 1e22)
        gmsh.option.setNumber("Mesh.ElementOrder", 1)
        gmsh.option.setNumber("Mesh.SecondOrderIncomplete", 0)

        gmsh.model.mesh.generate(3)
        gmsh.write(output_path)
    finally:
        gmsh.finalize()

    return output_path
