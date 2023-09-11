import enum
from typing import BinaryIO

from starhopper.formats.common import Location
from starhopper.io import BinaryReader


class StringContainerType(enum.IntEnum):
    Strings = 0
    DLStrings = 1
    ILStrings = 2


class StringContainer:
    """
    Parser for a Bethesda .strings, .dlstrings, and ilstring files.
    """

    def __init__(self, file: BinaryIO, type_: StringContainerType):
        self.file = file
        self.io = BinaryReader(file)
        self.type_ = type_
        self.header = self.parse_header(self.io)
        self._strings = {}

    @staticmethod
    def parse_header(reader: BinaryReader):
        with reader as header:
            header.uint32("count").uint32("size").set(
                "directory",
                [
                    (reader.uint32(), reader.uint32())
                    for _ in range(header["count"])
                ],
            )
            header.set(
                "loc",
                Location(
                    header.start_pos, header.pos, header.pos - header.start_pos
                ),
            )
            return header.data

    @property
    def strings(self):
        if self._strings:
            return self._strings

        self._strings = strings = {}

        for string_id, offset in self.header["directory"]:
            self.io.seek(self.header["loc"].end + offset)
            match self.type_:
                case StringContainerType.Strings:
                    strings[string_id] = self.io.cstring()
                case StringContainerType.DLStrings | StringContainerType.ILStrings:
                    size = self.io.uint32()
                    # TODO: This is absolutely not correct. We need to handle
                    #       encoding with Windows-1252 and their wacky custom
                    #       encoding for Polish & Czech.
                    strings[string_id] = self.io.read(size).decode("utf-8")
                case _:
                    raise ValueError(
                        f"Unknown string container type: {self.type_}"
                    )

        return self._strings
