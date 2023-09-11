import dataclasses

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (
    QTreeWidget,
    QTreeWidgetItem,
    QLayout,
    QHeaderView,
)

from starhopper.formats.esm.file import Record, ESMContainer, RecordFlag, Field
from starhopper.formats.esm.records.base import HighLevelRecord
from starhopper.gui.common import tr, ColorPurple, ColorGray
from starhopper.gui.viewers.binary_viewer import BinaryViewer
from starhopper.gui.viewers.viewer import Viewer


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
        self.file = record.file.file
        self.file.seek(0)
        self.record = dataclasses.replace(record, file=ESMContainer(self.file))

        self.details = QTreeWidget()
        self.details.setColumnCount(3)
        self.details.setHeaderLabels(
            (
                tr("RecordViewer", "Field Type", None),
                tr("RecordViewer", "Value", None),
                tr("RecordViewer", "Data Type", None),
            )
        )
        header = self.details.header()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(1, QHeaderView.Stretch)

        self.details.itemDoubleClicked.connect(self.on_item_double_clicked)
        self.details.currentItemChanged.connect(self.on_item_changed)

        self.loader = RecordLoaderThread(self, record)
        self.loader.progressSetMaximum.connect(self.on_progress_set_maximum)
        self.loader.progressUpdate.connect(self.on_progress_update)
        self.loader.progressDone.connect(self.on_progress_complete)
        self.loader.start()

        self.layout.insertWidget(0, self.details)

    def on_progress_complete(self):
        self.details.expandAll()
        super().on_progress_complete()

    def on_item_double_clicked(self, item: QTreeWidgetItem, column: int):
        if not isinstance(item, FieldChild):
            return

        self.add_panel(
            "child",
            BinaryViewer(
                item.field.data,
                working_area=self.working_area,
            ),
        )

    def on_item_changed(
        self, current: QTreeWidgetItem, previous: QTreeWidgetItem
    ):
        if not isinstance(current, FieldChild):
            return

        if not isinstance(current.field, Field):
            # If we have a high-level field, we already know what the contents
            # are.
            return

        self.add_panel(
            "child",
            BinaryViewer(
                current.field.data,
                working_area=self.working_area,
            ),
        )
