import dataclasses

from PySide6.QtCore import Signal, QObject, QRunnable, QThreadPool
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


class RecordLoaderSignals(QObject):
    progressStart = Signal(int)
    progressDone = Signal()


class RecordLoaderThread(QRunnable):
    def __init__(self, viewer: "RecordViewer", record: Record):
        super().__init__()
        self.record = record
        self.viewer = viewer
        self.s = RecordLoaderSignals()

    def run(self):
        self.s.progressStart.emit(self.record.loc.size)

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
            self.s.progressDone.emit()
            return

        # Fallback for unknown types of records.
        for field in self.record.fields():
            field_item = FieldChild(self.record, field)
            field_item.setText(0, field.type.decode("ascii"))
            field_item.setText(1, f"{field.size} bytes")
            field_item.setForeground(1, ColorGray)

            self.viewer.details.addTopLevelItem(field_item)

        self.s.progressDone.emit()


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

        self.details.currentItemChanged.connect(self.on_item_changed)

        loader = RecordLoaderThread(self, record)
        loader.s.progressStart.connect(self.on_loading_start)
        loader.s.progressDone.connect(self.on_loading_complete)
        QThreadPool.globalInstance().start(loader)

        self.layout.insertWidget(0, self.details)

    def on_loading_complete(self):
        self.details.expandAll()
        super().on_loading_complete()

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
