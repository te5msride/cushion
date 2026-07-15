"""Pure-Python mesh file readers for viewport preview (no Rhino deps).

read_stl:  binary or ASCII STL -> (points, triangles)
read_vtk:  legacy VTK unstructured grid, ASCII or BINARY (gmsh/SOFA
           exporter output) -> (points, tetras)
"""

import struct


def read_stl(path):
    """Return (points, triangles). Vertices are NOT welded (STL stores
    3 verts per facet); weld on the Rhino side if needed."""
    with open(path, "rb") as f:
        data = f.read()
    # ASCII iff it starts with 'solid' AND actually contains facet text
    # ('solid'-headed binary files exist in the wild)
    if data[:5] == b"solid" and b"vertex" in data[:1000]:
        return _ascii_stl(data.decode(errors="replace"))
    return _binary_stl(data)


def _binary_stl(data):
    if len(data) < 84:
        return [], []
    (n,) = struct.unpack_from("<I", data, 80)
    # tolerate truncated files / writers with an off-by-one facet count
    n = min(n, (len(data) - 84) // 50)
    pts, tris = [], []
    off = 84
    for i in range(n):
        vals = struct.unpack_from("<12f", data, off)  # normal + 3 verts
        base = len(pts)
        pts.append(vals[3:6])
        pts.append(vals[6:9])
        pts.append(vals[9:12])
        tris.append((base, base + 1, base + 2))
        off += 50
    return pts, tris


def _ascii_stl(text):
    pts, tris = [], []
    cur = []
    for line in text.splitlines():
        parts = line.split()
        if len(parts) == 4 and parts[0] == "vertex":
            cur.append((float(parts[1]), float(parts[2]), float(parts[3])))
            if len(cur) == 3:
                base = len(pts)
                pts.extend(cur)
                tris.append((base, base + 1, base + 2))
                cur = []
    return pts, tris


def read_vtk(path):
    """Legacy VTK unstructured grid -> (points, tetras). Handles the
    ASCII files VTKExporter writes and the BINARY (big-endian) files
    gmsh writes."""
    with open(path, "rb") as f:
        data = f.read()

    header = data[:256].decode(errors="replace").upper()
    if "BINARY" in header:
        return _binary_vtk(data)
    from .results import read_vtk_frame  # ASCII path shares that parser
    return read_vtk_frame(path)


def _binary_vtk(data):
    points, tetras = [], []
    pos = 0

    def find_line(keyword, start):
        i = data.index(keyword, start)
        end = data.index(b"\n", i)
        return data[i:end].split(), end + 1

    hdr, pos = find_line(b"POINTS", 0)
    npts = int(hdr[1])
    dtype = hdr[2].lower()
    fmt, size = (">%dd" % (npts * 3), 8) if dtype == b"double" else \
                (">%df" % (npts * 3), 4)
    vals = struct.unpack_from(fmt, data, pos)
    points = [(vals[i], vals[i + 1], vals[i + 2])
              for i in range(0, npts * 3, 3)]
    pos += npts * 3 * size

    hdr, pos = find_line(b"CELLS", pos)
    ntotal = int(hdr[2])
    ints = struct.unpack_from(">%di" % ntotal, data, pos)
    i = 0
    while i < ntotal:
        cnt = ints[i]
        if cnt == 4:
            tetras.append(tuple(ints[i + 1:i + 5]))
        i += cnt + 1
    return points, tetras
