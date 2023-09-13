import dataclasses
from typing import BinaryIO

from starhopper.formats.common import Location
from starhopper.io import BinaryReader


@dataclasses.dataclass
class Mesh:
    version: int
    triangle_count: int
    triangle_data: Location
    coordinate_scale: float
    weights_per_vertex: int
    vertex_count: int
    vertex_data: Location
    uv_count: int
    uv_data: Location
    unknown_count: int
    unknown_data: Location
    color_count: int
    color_data: Location
    normal_count: int
    normal_data: Location
    tangents_count: int
    tangents_data: Location


def parse_mesh(file: BinaryIO) -> Mesh:
    """
    Parses a mesh file.

    .. note::

        This file format is described here:
        https://github.com/fo76utils/ce2utils/blob/main/src/meshfile.cpp#L2
    """
    reader = BinaryReader(file)
    with reader as header:
        return Mesh(
            **header.uint32("version")
            .ensure("version", 1)
            .uint32("triangle_count")
            .set(
                "triangle_data",
                Location(
                    header.pos,
                    header.pos + (2 * header["triangle_count"]),
                ),
            )
            .skip(header["triangle_data"].size)
            .float_("coordinate_scale")
            # .change(lambda cs: cs / 32767)
            .uint32("weights_per_vertex")
            .uint32("vertex_count")
            .set(
                "vertex_data",
                Location(
                    header.pos,
                    header.pos + (2 * header["vertex_count"] * 3),
                ),
            )
            .skip(header["vertex_data"].size)
            .uint32("uv_count")
            .set(
                "uv_data",
                Location(
                    header.pos,
                    header.pos + (2 * header["uv_count"] * 2),
                ),
            )
            .skip(header["uv_data"].size)
            .uint32("unknown_count")
            .set(
                "unknown_data",
                Location(
                    header.pos,
                    header.pos + (4 * header["unknown_count"]),
                ),
            )
            .skip(header["unknown_data"].size)
            .uint32("color_count")
            .set(
                "color_data",
                Location(
                    header.pos,
                    header.pos + (4 * header["color_count"]),
                ),
            )
            .skip(header["color_data"].size)
            .uint32("normal_count")
            .set(
                "normal_data",
                Location(
                    header.pos,
                    header.pos + (2 * header["normal_count"]),
                ),
            )
            .skip(header["normal_data"].size)
            .uint32("tangents_count")
            .set(
                "tangents_data",
                Location(
                    header.pos,
                    header.pos + (4 * header["tangents_count"]),
                ),
            )
            .skip(header["tangents_data"].size)
            .data
        )


def mesh_to_obj(file: BinaryIO, destination: BinaryIO):
    """
    Converts a mesh file to an OBJ file.
    """
    # https://en.wikipedia.org/wiki/Wavefront_.obj_file
    # https://blender.stackexchange.com/a/32502
    header = parse_mesh(file)
    reader = BinaryReader(file)

    destination.write("# Exported using StarHopper :)\n".encode("ascii"))
    destination.write(b"\n")

    # List of geometric vertices, with (x, y, z [,w]) coordinates, w is optional
    reader.seek(header.vertex_data.start)
    for i in range(header.vertex_count):
        x = reader.int16() * header.coordinate_scale / 32767
        y = reader.int16() * header.coordinate_scale / 32767
        z = reader.int16() * header.coordinate_scale / 32767

        destination.write(f"v {x:.4f} {y:.4f} {z:.4f}\n".encode("ascii"))

    # List of texture coordinates, in (u, v [,w]) coordinates, these will vary
    # between 0 and 1
    reader.seek(header.uv_data.start)
    for i in range(header.uv_count):
        u = reader.half()
        v = reader.half()

        destination.write(f"vt {u} {v}\n".encode("ascii"))

    # List of vertex normals in (x,y,z) form
    reader.seek(header.triangle_data.start)
    for i in range(header.triangle_count // 3):
        # I don't honestly know _why_ we always add +1 (maybe to ensure the
        # value is never less than 0?) but it's what all the blender examples
        # do, so c'est la vie.
        a = reader.uint16() + 1
        b = reader.uint16() + 1
        c = reader.uint16() + 1

        destination.write(f"f {a:d} {b:d} {c:d}\n".encode("ascii"))
