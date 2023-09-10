import dataclasses
import os

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (
    QTreeWidget,
    QTreeWidgetItem,
    QMdiArea,
    QLayout,
)

from starhopper.formats.esm.file import Record, ESMFile, RecordFlag
from starhopper.formats.esm.records.base import HighLevelRecord
from starhopper.gui.common import tr, ColorPurple, ColorGray
from starhopper.gui.viewer import Viewer


class FieldChild(QTreeWidgetItem):
    def __init__(self, record, field):
        super().__init__()
        self.record = record
        self.field = field


class RecordLoaderThread(QThread):
    progressUpdate = Signal(int)
    progressSetMaximum = Signal(int)
    progressDone = Signal()

    def __init__(self, viewer: "RecordViewer", record: Record):
        super().__init__()
        self.record = record
        self.viewer = viewer

    def run(self):
        self.progressSetMaximum.emit(self.record.loc.size)

        item = QTreeWidgetItem(self.viewer.details)
        item.setText(0, "Details")

        item_flags = QTreeWidgetItem(["Flags", str(self.record.flags)])
        item_flags.addChildren(
            [
                QTreeWidgetItem([str(flag.name), str(True)])
                for flag in RecordFlag
                if flag in self.record.flags
            ]
        )

        item.addChildren(
            [
                QTreeWidgetItem(["Type", self.record.type.decode("ascii")]),
                QTreeWidgetItem(["Size", str(self.record.size)]),
                item_flags,
                QTreeWidgetItem(["Form ID", f"0x{self.record.form_id:08X}"]),
                QTreeWidgetItem(["Revision", str(self.record.revision)]),
                QTreeWidgetItem(["Version", str(self.record.version)]),
                QTreeWidgetItem(["Start", f"{self.record.loc.start:08x}"]),
                QTreeWidgetItem(["End", f"0x{self.record.loc.end:08x}"]),
                QTreeWidgetItem(["Size", f"0x{self.record.loc.size:08x}"]),
            ]
        )
        item.setExpanded(True)

        if HighLevelRecord.can_be_handled(self.record):
            hlr = HighLevelRecord(self.record)
            hlr.read()

            for field, values in hlr.results:
                field_item = FieldChild(self.record, field)
                field_item.setText(0, field.label())
                if len(values) == 1:
                    # If there's only a single value, we'll just display it
                    # inline.
                    value = next(iter(values.values()))
                    field_item.setText(1, str(value.value))
                    field_item.setForeground(1, ColorPurple)
                    field_item.setText(2, value.__class__.__name__)
                    field_item.setForeground(2, ColorGray)
                else:
                    field_item.addChildren(
                        [
                            QTreeWidgetItem([str(k), str(v)])
                            for k, v in values.items()
                        ]
                    )

                self.viewer.details.addTopLevelItem(field_item)

            # TODO: Actually track progress
            self.progressDone.emit()
            return

        # Fallback for unknown types of records.
        bytes_read = 0
        last_updated_at = 0
        for field in self.record.fields():
            field_item = FieldChild(self.record, field)
            field_item.setText(0, field.type.decode("ascii"))
            field_item.addChildren(
                [
                    QTreeWidgetItem(["Size", str(field.size)]),
                    QTreeWidgetItem(["Data", repr(field.data)]),
                ]
            )
            field_item.setExpanded(True)

            self.viewer.details.addTopLevelItem(field_item)

            bytes_read += field.size + 6
            if bytes_read - last_updated_at > 1024:
                last_updated_at = bytes_read
                self.progressUpdate.emit(bytes_read)

        self.progressDone.emit()


class RecordViewer(Viewer):
    """
    Generic record viewer.
    """

    def __init__(self, record: Record, working_area: QLayout):
        super().__init__(working_area=working_area)
        self.file = os.fdopen(os.dup(record.file.file.fileno()), "rb")
        self.file.seek(0)
        self.record = dataclasses.replace(record, file=ESMFile(self.file))

        self.details = QTreeWidget()
        self.details.setColumnCount(3)
        self.details.setHeaderLabels(
            (
                tr("RecordViewer", "Field Type", None),
                tr("RecordViewer", "Value", None),
                tr("RecordViewer", "Data Type", None),
            )
        )

        self.loader = RecordLoaderThread(self, record)
        self.loader.progressSetMaximum.connect(self.on_progress_set_maximum)
        self.loader.progressUpdate.connect(self.on_progress_update)
        self.loader.progressDone.connect(self.on_progress_complete)
        self.loader.start()

        self.layout.insertWidget(0, self.details)
