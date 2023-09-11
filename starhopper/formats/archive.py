import abc
import dataclasses
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, BinaryIO


@dataclasses.dataclass
class AbstractFile:
    path: str
    size: int

    # Container-specific metadata.
    meta: dataclasses.field(default_factory=dict)
    # The parent container for this file.
    container: "ArchiveContainer"

    @contextmanager
    def open(self):
        with self.container.open(self) as io:
            yield io

    def extract_into(self, directory: Path, *, overwrite: bool = False):
        """
        Extracts the file into a directory.

        :param directory: The directory to extract into.
        :param overwrite: Whether to overwrite existing files.
        """
        self.container.extract_into(self, directory, overwrite=overwrite)


class ArchiveContainer(abc.ABC):
    """
    Provides a base class for working with files that contain other files in
    a virtual filesystem, such as a .bas or .ba2 archive.
    """

    @abc.abstractmethod
    def read_from_file(self, file: BinaryIO):
        """
        Reads the archive from a file.
        """

    @abc.abstractmethod
    def files(self) -> Iterator[AbstractFile]:
        """
        Returns an iterator over the files in the archive.
        """

    @abc.abstractmethod
    @contextmanager
    def open(self, file: AbstractFile):
        """
        Opens a file in the archive.
        """

    def extract_into(
        self, file: AbstractFile, directory: Path, *, overwrite: bool = False
    ):
        """
        Extracts a file into a directory.

        :param file: The file to extract.
        :param directory: The directory to extract into.
        :param overwrite: Whether to overwrite existing files.
        """
        if not directory.is_dir():
            raise ValueError(f"{directory} is not a directory")

        final_path = directory / Path(file.path)
        if final_path.exists() and not overwrite:
            raise FileExistsError(f"{final_path} already exists")

        # Naive implementation that should be replaced by optimized methods
        # in subclasses. This will result in the entire thing getting read
        # into memory.
        with file.open() as io:
            with final_path.open("wb") as out:
                out.write(io.read())

    def add(self, file: AbstractFile, content: bytes):
        """
        Adds a file to the archive. If the file already exists, it will be
        overwritten.
        """
        raise NotImplementedError()

    def remove(self, file: AbstractFile):
        """
        Removes a file from the archive.
        """
        raise NotImplementedError()

    def save(self, io: BinaryIO):
        """
        Saves the archive to a file.
        """
        raise NotImplementedError()
