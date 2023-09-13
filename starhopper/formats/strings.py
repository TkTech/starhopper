import enum
from typing import BinaryIO

from starhopper.formats.common import Location
from starhopper.io import BinaryReader, BinaryWriter


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
                Location(header.start_pos, header.pos),
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

    def save(self, file: BinaryIO):
        """
        Saves the string container to a file.

        :param file: Any file-like object supporting write() and seek().
        """
        writer = BinaryWriter(file)
        writer.uint32(len(self.strings))
        # This is the size of the string data, we'll have to come back to write
        # this.
        writer.uint32(0)

        # Where to skip backwards to when writing offsets.
        offsets: dict[int, int] = {}

        for string_id in self.strings.values():
            writer.uint32(string_id)
            offsets[string_id] = writer.pos
            writer.uint32(0)

        # Write the string data.
        for string_id, string in self.strings.items():
            start = writer.pos
            match self.type_:
                case StringContainerType.Strings:
                    writer.cstring(string)
                case StringContainerType.DLStrings | StringContainerType.ILStrings:
                    encoded = string.encode("utf-8")
                    writer.uint32(len(encoded))
                    writer.write(string)
                    writer.write(b"\x00")

            return_pos = writer.pos
            writer.seek(offsets[string_id])
            writer.uint32(start)
            writer.seek(return_pos)

        # Write the size of the string data.
        writer.seek(4)
        writer.uint32(writer.pos - 8)
