from struct import unpack
from typing import BinaryIO, Callable


class BinaryReader:
    def __init__(self, file: BinaryIO, *, offset: int = 0):
        self.file = file
        self.offset = offset

    def read(self, size: int) -> bytes:
        self.offset += size
        result = self.file.read(size)
        if not result:
            raise EOFError("End of file")
        return result

    @property
    def pos(self) -> int:
        return self.offset

    def seek(self, offset: int):
        self.offset = offset
        self.file.seek(offset, 0)

    def skip(self, count: int):
        self.offset += count
        self.file.seek(count, 1)

    def uint8(self) -> int:
        return int.from_bytes(self.read(1), byteorder="little", signed=False)

    def uint16(self) -> int:
        return int.from_bytes(self.read(2), byteorder="little", signed=False)

    def uint32(self) -> int:
        return int.from_bytes(self.read(4), byteorder="little", signed=False)

    def uint64(self) -> int:
        return int.from_bytes(self.read(8), byteorder="little", signed=False)

    def int8(self) -> int:
        return int.from_bytes(self.read(1), byteorder="little", signed=True)

    def int16(self) -> int:
        return int.from_bytes(self.read(2), byteorder="little", signed=True)

    def int32(self) -> int:
        return int.from_bytes(self.read(4), byteorder="little", signed=True)

    def int64(self) -> int:
        return int.from_bytes(self.read(8), byteorder="little", signed=True)

    def float_(self) -> float:
        return unpack("<f", self.read(4))[0]

    def double(self) -> float:
        return unpack("<d", self.read(8))[0]

    def __enter__(self) -> "Capture":
        return Capture(self)

    def __exit__(self, exc_type, exc_value, traceback):
        pass


class Capture:
    def __init__(self, file: BinaryReader):
        self.file = file
        self.start_pos: int = file.pos
        self.data = {}
        self._last_field_set: str | None = None

    def __getitem__(self, item: str):
        return self.data[item]

    def __setitem__(self, item: str, value):
        self._last_field_set = item
        self.data[item] = value

    def __repr__(self):
        return repr(self.data)

    @property
    def pos(self):
        """
        The current position as an offset from the start of the IO stream.
        """
        return self.file.pos

    def uint8(self, name: str) -> "Capture":
        self[name] = self.file.uint8()
        return self

    def uint16(self, name: str) -> "Capture":
        self[name] = self.file.uint16()
        return self

    def uint32(self, name: str) -> "Capture":
        self[name] = self.file.uint32()
        return self

    def uint64(self, name: str) -> "Capture":
        self[name] = self.file.uint64()
        return self

    def int8(self, name: str) -> "Capture":
        self[name] = self.file.int8()
        return self

    def int16(self, name: str) -> "Capture":
        self[name] = self.file.int16()
        return self

    def int32(self, name: str) -> "Capture":
        self[name] = self.file.int32()
        return self

    def int64(self, name: str) -> "Capture":
        self[name] = self.file.int64()
        return self

    def float_(self, name: str) -> "Capture":
        self[name] = self.file.float_()
        return self

    def double(self, name: str) -> "Capture":
        self[name] = self.file.double()
        return self

    def string(
        self, name: str, size: int, encoding: str = "utf-8"
    ) -> "Capture":
        """
        Read the given number of bytes into the given field, and decode it as
        the given encoding.

        :param name: The destination field.
        :param size: The number of bytes to read.
        :param encoding: The encoding to use.
        """
        self[name] = self.file.read(size).decode(encoding)
        return self

    def cstring(self, name: str, encoding: str = "utf-8") -> "Capture":
        """
        Read bytes until a null byte is encountered, and decode them as the
        given encoding.

        :param name: The destination field.
        :param encoding: The encoding to use.
        """
        b = []
        while True:
            c = self.file.uint8()
            if c == 0:
                break
            b.append(c)
        self[name] = bytes(b).decode(encoding)
        return self

    def bytes(self, name: str, size: int) -> "Capture":
        """
        Read the given number of bytes into the given field.

        :param name: The destination field.
        :param size: The number of bytes to read.
        """
        self[name] = self.file.read(size)
        return self

    def skip(self, count: int) -> "Capture":
        """
        Skip the given number of bytes.

        :param count: The number of bytes to skip.
        """
        self.file.seek(self.file.pos + count)
        return self

    def seek(self, offset: int) -> "Capture":
        """
        Seek to the given offset relative to the start of the record.

        .. note::

            This is offset from the _start of the capture_, not the entire
            IO stream.

        :param offset: The offset to seek to.
        """
        self.file.seek(self.start_pos + offset)
        return self

    def ensure(
        self, name: str, value_or_callable: object | Callable[[object], bool]
    ) -> "Capture":
        """
        Ensure that the value of the given field is equal to the given value.

        :param name: The field to validate.
        :param value_or_callable: A value to compare against, or a callable
                                    that takes the current value and returns
                                    True if it's valid.
        :return:
        """
        if callable(value_or_callable):
            valid = value_or_callable(self.data[name])
        else:
            valid = self.data[name] == value_or_callable

        if not valid:
            raise ValueError(f"Invalid value for {name}: {self.data[name]}")

        return self

    def change(self, callback: Callable) -> "Capture":
        """
        Change the value of the last field set.

        :param callback: Callable that takes the current value and returns
                         the new value.
        """
        self.data[self._last_field_set] = callback(
            self.data[self._last_field_set]
        )
        return self

    def stride(self, name: str) -> "Capture":
        self[name] = {
            "start": self.start_pos,
            "end": self.file.pos,
            "size": self.file.pos - self.start_pos,
        }
        return self

    def set(self, name: str, value: object) -> "Capture":
        self[name] = value
        return self
