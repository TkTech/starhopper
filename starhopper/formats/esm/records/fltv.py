from starhopper.formats.esm.file import Field
from starhopper.formats.esm.records.base import RecordField, HighLevelRecord
from starhopper.formats.esm.records.types import Float
from starhopper.io import BinaryReader


class FLTV(RecordField):
    @staticmethod
    def label():
        return "Float Value"

    def read(self, record: HighLevelRecord, field: Field, io: BinaryReader):
        with io as fltv:
            return fltv.float_("value").change(Float).data
