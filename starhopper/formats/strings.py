import enum
from typing import BinaryIO

from starhopper.formats.common import Location
from starhopper.io import BinaryReader


class StringContainerType(enum.IntEnum):
    Strings = 0
    DLStrings = 1
    ILStrings = 2


class StringContainer:
    def __init__(self, file: BinaryIO, type_: StringContainerType):
        """
        Parser for a Bethesda .strings, .dlstrings, and ilstring files.

        The type of string container is typically determined by the file
        extension and must be passed into the parser. The structure of the
        header is the same for all three types, but the strings themselves
        are encoded differently.

        :param file: The file to parse.
        :param type_: The type of string container.
        """
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
        """
        Returns a dictionary of string IDs to strings.

        :return:
        """
        if self._strings:
            return self._strings

        self._strings = strings = {}

        for string_id, offset in self.header["directory"]:
            self.io.seek(self.header["loc"].end + offset)
            match self.type_:
                case StringContainerType.Strings:
                    strings[string_id] = self.io.cstring(None)
                    try:
                        strings[string_id] = strings[string_id].decode("utf-8")
                    except UnicodeDecodeError:
                        strings[string_id] = strings[string_id].decode("cp1252")
                case StringContainerType.DLStrings | StringContainerType.ILStrings:
                    size = self.io.uint32()
                    strings[string_id] = self.io.read(size)
                    try:
                        strings[string_id] = strings[string_id].decode("utf-8")
                    except UnicodeDecodeError:
                        strings[string_id] = strings[string_id].decode("cp1252")
                case _:
                    raise ValueError(
                        f"Unknown string container type: {self.type_}"
                    )

        return self._strings
