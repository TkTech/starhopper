import contextlib
import zlib
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import BinaryIO, Iterator

import lz4.frame
import lz4.block

from starhopper.formats.archive import ArchiveContainer, AbstractFile
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
    reader: BinaryReader | None = None


class BA2Container(ArchiveContainer):
    """
    Parser for Bethesda .ba2 files.

    .. note::

        Currently, this only supports BTDX-versioned .ba2 files, such as those
        used in Starfield.
    """

    def __init__(self, file: BinaryIO | None = None):
        self._files: list[AbstractFile] = []

        if file is not None:
            self.read_from_file(file)

    def read_from_file(self, file: BinaryIO):
        """
        Reads a .ba2 file from a file-like object.

        :param file: Any file-like object supporting read().
        """
        io = BinaryReader(file)

        header = self.parse_header(io)
        name_table = self.parse_name_table(io, header)
        for file in self.parse_file_index(io, header, name_table):
            self._files.append(
                AbstractFile(
                    path=file.path.decode("ascii"),
                    container=self,
                    size=file.unpacked_size,
                    meta={
                        "_original": file,
                    },
                )
            )

    def files(self) -> Iterator[AbstractFile]:
        yield from self._files

    @contextlib.contextmanager
    def open(self, file: AbstractFile):
        """
        Opens a file in the archive.

        :param file: The file to open.
        :return: A file-like object.
        """
        # If there's no original metadata, then this file was added after
        # the archive was loaded and hasn't actually been written anywhere.
        with BytesIO() as destination:
            self._write_to_io(file, destination)
            destination.seek(0)
            yield destination

    def extract_into(
        self, file: AbstractFile, directory: Path, *, overwrite: bool = False
    ):
        if not directory.is_dir():
            raise ValueError(f"{directory} is not a directory")

        final_path = directory / Path(file.path)
        if final_path.exists() and not overwrite:
            raise FileExistsError(f"{final_path} already exists")

        final_path.parent.mkdir(parents=True, exist_ok=True)
        with open(final_path, "wb") as destination:
            self._write_to_io(file, destination)

    @staticmethod
    def _write_to_io(file: AbstractFile, destination: BinaryIO):
        original: GeneralFile | None = file.meta.get("_original")
        if original is None:
            destination.write(file.meta["_content"])
        else:
            reader = original.reader
            reader.seek(original.offset)
            if original.packed_size > 0:
                # This file is compressed.
                # TODO: We should see if these support chunked decoding to
                #       minimize memory usage.
                zlib_check = reader.read(2)
                reader.seek(original.offset)

                if zlib_check == b"\x78\xDA":
                    # Zlib-compressed.
                    unpacked = zlib.decompress(
                        reader.read(original.packed_size),
                        bufsize=original.unpacked_size,
                    )
                else:
                    unpacked = lz4.frame.decompress(
                        reader.read(original.packed_size)
                    )

                if len(unpacked) != original.unpacked_size:
                    raise ValueError(
                        f"Unpacked size mismatch: expected "
                        f"{original.unpacked_size}, got {len(unpacked)}"
                    )

                destination.write(unpacked)
            else:
                end = original.offset + original.unpacked_size
                for chunk in range(original.offset, end, 4096):
                    chunk = reader.read(4096)
                    if not chunk:
                        break
                    destination.write(chunk)

    @staticmethod
    def parse_header(reader: BinaryReader):
        """
        Parses the header of a .ba2 file.
        """
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
                Location(header.start_pos, header.pos),
            )

            return header.data

    @staticmethod
    def parse_name_table(reader: BinaryReader, header: dict):
        reader.seek(header["names_offset"])
        result = [
            reader.read(reader.uint16()) for _ in range(header["file_count"])
        ]
        reader.seek(header["loc"].end)
        return result

    @staticmethod
    def parse_file_index(
        reader: BinaryReader, header: dict, name_table: list[bytes]
    ) -> list[GeneralFile]:
        if header["type"] == "GNRL":
            for index in range(header["file_count"]):
                with reader as file:
                    yield (
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
                                ),
                            )
                            .data,
                            reader=reader,
                            path=name_table[index],
                        )
                    )
