from dataclasses import dataclass
from typing import BinaryIO

from starhopper.formats.common import Location
from starhopper.io import BinaryReader


@dataclass
class GeneralFile:
    hash_: int
    ext: str
    directory_hash: int
    unknown_0: int
    offset: int
    packed_size: int
    unpacked_size: int
    unknown_1: int
    path: bytes
    loc: Location
    container: "BTDXContainer"

    def view_content(self) -> bytes:
        if self.packed_size == 0:
            self.container.io.seek(self.offset)
            return self.container.io.read(self.unpacked_size)
        else:
            return bytes()


class BTDXContainer:
    def __init__(self, file: BinaryIO):
        self.file = file
        self.io = BinaryReader(file)
        self.header = self.parse_header(self.io)
        self.name_table = self.parse_name_table(self.io)
        self._files = []

    @staticmethod
    def parse_header(reader: BinaryReader):
        with reader as header:
            header.bytes("file_id", 4).ensure("file_id", b"BTDX").uint32(
                "version"
            ).string("type", 4).change(lambda t: t.rstrip()).uint32(
                "file_count"
            ).uint64(
                "names_offset"
            )

            if header["version"] in (2, 3):
                header.uint32("unknown_1").uint32("unknown2_2")

            if header["version"] == 3:
                header.uint32("unknown_3")

            header.set(
                "loc",
                Location(
                    header.start_pos, header.pos, header.pos - header.start_pos
                ),
            )

            return header.data

    def parse_name_table(self, reader: BinaryReader):
        reader.seek(self.header["names_offset"])
        result = [
            reader.read(reader.uint16())
            for _ in range(self.header["file_count"])
        ]
        reader.seek(self.header["loc"].end)
        return result

    @property
    def files(self) -> list[GeneralFile]:
        if self._files:
            return self._files

        self._files = result = []

        if self.header["type"] == "GNRL":
            for index in range(self.header["file_count"]):
                with self.io as file:
                    result.append(
                        GeneralFile(
                            **file.uint32("hash_")
                            .string("ext", 4)
                            .change(lambda t: t.rstrip())
                            .uint32("directory_hash")
                            .uint32("unknown_0")
                            .uint64("offset")
                            .uint32("packed_size")
                            .uint32("unpacked_size")
                            .uint32("unknown_1")
                            .set(
                                "loc",
                                Location(
                                    file.start_pos,
                                    file.pos,
                                    file.pos - file.start_pos,
                                ),
                            )
                            .data,
                            path=self.name_table[index],
                            container=self
                        )
                    )

        return result
