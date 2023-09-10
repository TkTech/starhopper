from starhopper.formats.esm.file import Record
from starhopper.formats.esm.records.base import (
    BasicType,
    BaseRecord,
)
from starhopper.formats.esm.records.data import DATA
from starhopper.formats.esm.records.edid import EDID


class GMST(BaseRecord):
    @staticmethod
    def label():
        return b"Game Setting"

    @staticmethod
    def structure(record: Record):
        return [
            EDID("Editor ID"),
            DATA(
                "value",
                type_=lambda r: {
                    "s": BasicType.String,
                    "i": BasicType.Int,
                    "f": BasicType.Float,
                    "b": BasicType.Bool,
                }.get(r.first(EDID)["name"].value[0]),
            ),
        ]
