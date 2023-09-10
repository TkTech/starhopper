from typing import Callable

from starhopper.formats.esm.file import Field
from starhopper.formats.esm.records.base import (
    RecordField,
    HighLevelRecord,
    BasicType,
)
from starhopper.formats.esm.records.types import String, UInt32, Float, Bool, \
    Bytes
from starhopper.io import BinaryReader


class DATA(RecordField):
    def __init__(
        self, name: str, type_: Callable[[HighLevelRecord], BasicType]
    ):
        super().__init__(name)
        self.type_ = type_

    @staticmethod
    def label():
        return "Arbitrary Data"

    def read(self, record: HighLevelRecord, field: Field, io: BinaryReader):
        with io as data:
            type_ = self.type_(record)
            match type_:
                case BasicType.String:
                    data.cstring("value").change(String)
                case BasicType.Int:
                    data.int32("value").change(UInt32)
                case BasicType.Float:
                    data.float_("value").change(Float)
                case BasicType.Bool:
                    data.uint8("value").change(Bool)
                case BasicType.Unknown:
                    data.bytes("value", field.size).change(Bytes)
                case _:
                    raise ValueError(f"Unknown type {self.type_}")

            return data.data
