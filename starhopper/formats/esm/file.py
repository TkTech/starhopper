import dataclasses
import enum
import zlib
from io import BytesIO
from typing import BinaryIO, Iterator, Any

from starhopper.formats.common import Location
from starhopper.io import BinaryReader


class RecordFlag(enum.IntFlag):
    Master = 0x01
    Deleted = 0x20
    Localized = 0x80
    Shadows = 0x200
    Persistent = 0x400
    Ignored = 0x1000
    VisibleWhenDistant = 0x8000
    Dangerous = 0x20000
    Compressed = 0x40000
    CantWait = 0x80000


class GroupType(enum.IntEnum):
    # GitHub Copilot crapped out this enum practically verbatim from the
    # ESMSharp project...
    Top = 0x00
    WorldChildren = 0x01
    InteriorCellBlock = 0x02
    InteriorCellSubBlock = 0x03
    ExteriorCellBlock = 0x04
    ExteriorCellSubBlock = 0x05
    CellChildren = 0x06
    TopicChildren = 0x07
    CellPersistentChildren = 0x08
    CellTemporaryChildren = 0x09
    CellVisibleDistantChildren = 0x0A


@dataclasses.dataclass
class Group:
    type: bytes
    size: int
    label: bytes
    group_type: int
    version: int
    loc: Location
    file: "ESMContainer"

    def get_friendly_label(self) -> str:
        """
        Get a human-friendly name for display.

        Only top-level GRUPs have a readable label. The rest must be resolved.
        """
        io = BinaryReader(BytesIO(self.label))
        match self.group_type:
            case GroupType.Top:
                return self.label.decode("ascii")
            case GroupType.WorldChildren:
                return f"World Children [{io.uint32():08X}]"
            case GroupType.InteriorCellBlock:
                return f"Interior Cell Block [{io.uint32():08X}]"
            case GroupType.InteriorCellSubBlock:
                return f"Interior Cell Sub-Block [{io.uint32():08X}]"
            case GroupType.ExteriorCellBlock:
                return f"Exterior Cell Block {io.uint16()}, {io.uint16()}"
            case GroupType.ExteriorCellSubBlock:
                return f"Exterior Cell Sub-Block {io.uint16()}, {io.uint16()}"
            case GroupType.CellChildren:
                return f"Cell Children [{io.uint32():08X}]"
            case GroupType.TopicChildren:
                return f"Topic Children [{io.uint32():08X}]"
            case GroupType.CellPersistentChildren:
                return f"Cell Persistent Children [{io.uint32():08X}]"
            case GroupType.CellTemporaryChildren:
                return f"Cell Temporary Children [{io.uint32():08X}]"
            case GroupType.CellVisibleDistantChildren:
                return f"Cell Visible Distant Children [{io.uint32():08X}]"
            case _:
                return f"Unknown (T:{self.group_type}, V:{self.label.hex()})"

    @property
    def metadata(self) -> dict[str, Any]:
        return {}

    def children(self):
        self.file.io.seek(self.loc.start + 24)
        while self.file.io.pos < self.loc.end:
            peek = self.file.io.read(4)
            self.file.io.seek(self.file.io.pos - 4)

            if peek == b"GRUP":
                group = self.file.parse_group(self.file.io)
                self.file.io.seek(group.loc.end)
                yield group
            else:
                record = self.file.parse_record()
                self.file.io.seek(record.loc.end)
                yield record


@dataclasses.dataclass
class Record:
    type: bytes
    size: int
    flags: RecordFlag
    form_id: int
    revision: int
    version: int
    loc: Location
    file: "ESMContainer"

    def fields(self):
        self.file.io.seek(self.loc.start + 24)
        if self.flags & RecordFlag.Compressed:
            decompressed_size = self.file.io.uint32()
            with BytesIO(
                zlib.decompress(
                    self.file.io.read(self.size - 4),
                    bufsize=decompressed_size,
                )
            ) as data:
                compressed_io = BinaryReader(data)
                while compressed_io.pos < decompressed_size:
                    field = self.file.parse_field(compressed_io)
                    yield field
        else:
            while self.file.io.pos < self.loc.end:
                field = self.file.parse_field()
                yield field


@dataclasses.dataclass
class Field:
    type: bytes
    size: int
    file: "ESMContainer"
    data: bytes


class ESMContainer:
    """
    Parser for a Bethesda ESM file.
    """

    def __init__(self, file: BinaryIO):
        self.file = file
        self.io = BinaryReader(file)
        self.header = self.parse_header(self.io)
        self.io.seek(self.header["loc"].end)
        self._groups = list(self.parse_groups(self.io))

    @staticmethod
    def parse_header(reader: BinaryReader):
        with reader as header:
            return (
                header.bytes("type", 4)
                .ensure("type", b"TES4")
                .uint32("size")
                .uint32("flags")
                .change(lambda f: RecordFlag(f))
                .uint32("form_id")
                .ensure("form_id", 0)
                .uint32("revision")
                .uint16("version")
                .skip(2)
                .set(
                    "loc",
                    Location(
                        header.start_pos,
                        header.start_pos + header["size"] + 24,
                    ),
                )
                .data
            )

    def parse_group(self, stream: BinaryReader):
        with stream as group:
            return Group(
                **group.bytes("type", 4)
                .uint32("size")
                .bytes("label", 4)
                .uint32("group_type")
                .skip(2)
                .skip(2)
                .uint16("version")
                .skip(2)
                .set(
                    "loc",
                    Location(
                        group.start_pos,
                        group.start_pos + group["size"],
                    ),
                )
                .data,
                file=self,
            )

    def parse_groups(self, reader: BinaryReader) -> Iterator[Group]:
        while True:
            try:
                group = self.parse_group(reader)
                reader.seek(group.loc.end)
                yield group
            except EOFError:
                break

    def parse_record(self) -> Record:
        with self.io as record:
            return Record(
                **record.bytes("type", 4)
                .uint32("size")
                .uint32("flags")
                .change(lambda f: RecordFlag(f))
                .uint32("form_id")
                .uint32("revision")
                .uint16("version")
                .skip(2)
                .set(
                    "loc",
                    Location(
                        record.start_pos,
                        record.start_pos + record["size"] + 24,
                    ),
                )
                .data,
                file=self,
            )

    def parse_field(self, using: BinaryReader | None = None) -> Field:
        with using or self.io as field:
            field.bytes("type", 4).uint16("size")

            if field["type"] == b"XXXX":
                # This took a really long time to figure out. The XXXX field
                # would parse fine, but a couple fields later parsing would
                # break. XXXX is used to indicate that the next field uses a
                # 32bit size instead of the usual 16bit size. The XXXX field
                # itself is not included in the size.
                field.uint32("size").bytes("type", 4).skip(2)
                if field["size"] == 0:
                    field.set("data", b"")
                else:
                    field.bytes("data", field["size"])
            else:
                if field["size"] == 0:
                    field.set("data", b"")
                else:
                    field.bytes("data", field["size"])

            return Field(
                **field.data,
                file=self,
            )

    @property
    def groups(self):
        return self._groups
