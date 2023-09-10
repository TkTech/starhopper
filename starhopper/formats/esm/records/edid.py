from starhopper.formats.esm.file import Field
from starhopper.formats.esm.records.base import RecordField, HighLevelRecord
from starhopper.formats.esm.records.types import String
from starhopper.io import BinaryReader


class EDID(RecordField):
    @staticmethod
    def label():
        return "Editor ID"

    def read(self, record: HighLevelRecord, field: Field, io: BinaryReader):
        with io as edid:
            return edid.cstring("name").change(String).data
