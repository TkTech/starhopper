import dataclasses
from typing import BinaryIO

from starhopper.io import BinaryReader, BinaryWriter


@dataclasses.dataclass
class Record:
    type_: bytes
    size: int
    data: bytes


class CompiledDBContainer:
    """
    Parser for a Bethesda CompiledDB file (.cdb).

    This file format is not yet fully understood. It appears to be a
    serialization of in-memory data structures used by the game engine and
    may change with each release.
    """

    def __init__(self, file: BinaryIO | None = None):
        self.records = []
        if file:
            self.read_from_file(file)

    def read_from_file(self, file: BinaryIO):
        io = BinaryReader(file)
        with io as header:
            header.bytes("magic", 4).ensure("magic", b"BETH").uint32(
                "size"
            ).ensure("size", 8).uint32("version").uint32("record_count")
            for i in range(header["record_count"] - 1):
                with io as record:
                    self.records.append(
                        Record(
                            **record.bytes("type_", 4)
                            .uint32("size")
                            .bytes("data", record["size"])
                            .data
                        )
                    )

    def save(self, destination: BinaryIO, *, version: int = 4):
        io = BinaryWriter(destination)
        io.write(b"BETH").uint32(8).uint32(version).uint32(
            len(self.records) + 1
        )
        for record in self.records:
            io.write(record.type_).uint32(len(record.data)).write(record.data)
