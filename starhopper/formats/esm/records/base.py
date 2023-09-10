import abc
import enum
import importlib
import inspect
import pkgutil
from functools import cache
from io import BytesIO
from typing import Any

from starhopper.formats.esm.file import Record, Field
from starhopper.io import BinaryReader


class Missing:
    pass


class BasicType(enum.IntEnum):
    String: int = 0
    Int: int = 1
    Float: int = 2
    Bool: int = 3
    Unknown: int = 4


class RecordField(abc.ABC):
    """
    Base class for an ESM field contained in a record.
    """

    def __init__(self, name: str):
        self.name = name

    def __repr__(self):
        return f"<{self.__class__.__name__}({self.name!r})>"

    @staticmethod
    @abc.abstractmethod
    def label() -> str:
        pass

    def read_from_field(self, record: Record, field: Field):
        with BytesIO(field.data) as src:
            io = BinaryReader(src)
            return self.read(record, field, io)

    @abc.abstractmethod
    def read(
        self, record: Record, field: Field, io: BinaryReader
    ) -> dict[str, Any]:
        pass


class UnknownField(RecordField):
    @staticmethod
    def label():
        return "Unknown"

    def read(self, record: "HighLevelRecord", field: Field, io: BinaryReader):
        with io as unknown:
            return (
                unknown.set("size", field.size).bytes("data", field.size).data
            )


class BaseRecord(abc.ABC):
    @staticmethod
    @abc.abstractmethod
    def label():
        pass

    @staticmethod
    @abc.abstractmethod
    def structure(record: Record):
        pass


class UnknownRecord(BaseRecord):
    @staticmethod
    def label():
        return "An Unknown Record"

    @staticmethod
    def structure(record: Record):
        return [UnknownField("Unknown")]


@cache
def get_all_records() -> dict[bytes, type[BaseRecord]]:
    """
    Returns a dictionary of all implemented record fields.
    """
    import starhopper.formats.esm.records

    scan_path = starhopper.formats.esm.records.__path__

    result = {}
    for item in pkgutil.iter_modules(scan_path):
        module = importlib.import_module(
            f"starhopper.formats.esm.records.{item.name}"
        )

        for _, class_ in inspect.getmembers(module, inspect.isclass):
            if issubclass(class_, BaseRecord) and class_ is not BaseRecord:
                result[class_.__name__.encode("ascii")] = class_

    return result


class HighLevelRecord:
    """
    A high-level representation of a record.

    When the complete structure of a Record is known, this class can be used to
    parse the record into a high-level representation with individual fields
    parsed.
    """

    def __init__(self, record: Record):
        self.results: list[RecordField, dict[str, Any]] = []
        self.record = record

    def first(self, type_: type[RecordField], default=Missing):
        """
        Returns the first result of the given type.

        :param type_: A subclass of RecordField.
        :param default: A default value to return if the type is not found.
        :return: The first result of the given type.
        """
        for result, data in self.results:
            if isinstance(result, type_):
                return data

        if default is not Missing:
            return default

        raise ValueError(f"Could not find {type_}")

    @staticmethod
    def can_be_handled(record: Record):
        """
        Returns True if this record can be handled by a handler.
        """
        return record.type in get_all_records()

    @staticmethod
    def handler(record: Record) -> type[BaseRecord]:
        return get_all_records().get(record.type, UnknownRecord)

    def read(self):
        for structure, field in zip(
            self.handler(self.record).structure(self.record),
            self.record.fields(),
        ):
            self.results.append(
                (structure, structure.read_from_field(self, field))
            )
