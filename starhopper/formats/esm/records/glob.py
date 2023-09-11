from starhopper.formats.esm.file import Record
from starhopper.formats.esm.records.base import (
    BaseRecord,
)
from starhopper.formats.esm.records.edid import EDID
from starhopper.formats.esm.records.fltv import FLTV


class GLOB(BaseRecord):
    @staticmethod
    def label():
        return "Global"

    @staticmethod
    def structure(record: Record):
        return [
            EDID("Editor ID"),
            FLTV("Value"),
        ]
