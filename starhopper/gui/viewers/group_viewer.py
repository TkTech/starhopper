import dataclasses
from io import BytesIO

from PySide6 import QtGui, QtCore
from PySide6.QtCore import Signal, QRunnable, QThreadPool, QObject
from PySide6.QtWidgets import (
    QTreeWidgetItem,
    QTreeWidget,
    QLayout,
)

from starhopper.formats.esm.file import Group, ESMContainer, Record, RecordFlag
from starhopper.gui.common import (
    tr,
    ColorGray,
    ColorPurple,
    monospace,
    ColorRed,
)
from starhopper.gui.viewers.record_viewer import RecordViewer
from starhopper.gui.viewers.viewer import Viewer
from starhopper.io import BinaryReader


class RecordChild(QTreeWidgetItem):
    def __init__(self, record: Record):
        super().__init__()
        self.record = record


class GroupChild(QTreeWidgetItem):
    def __init__(self, group: Group):
        super().__init__()
        self.group = group


class GroupLoaderSignals(QObject):
    progressStart = Signal(int)
    progressDone = Signal()


class GroupLoaderThread(QRunnable):
    """
    Loads a group in the background and populates the details view.
    """

    def __init__(self, viewer: "GroupViewer", group: Group):
        super().__init__()
        self.viewer = viewer
        self.group = group
        self.s = GroupLoaderSignals()

    def run(self):
        self.s.progressStart.emit(self.group.loc.size)

        item = QTreeWidgetItem(self.viewer.details)
        item.setText(0, tr("GroupViewer", "Details", None))
        item.addChildren(
            [
                QTreeWidgetItem(["Type", self.group.type.decode("ascii")]),
                QTreeWidgetItem(["Size", f"{self.group.size} bytes"]),
                QTreeWidgetItem(["Label", repr(self.group.label)]),
                QTreeWidgetItem(["Group Type", str(self.group.group_type)]),
                QTreeWidgetItem(["Version", str(self.group.version)]),
                QTreeWidgetItem(["Start", f"{self.group.loc.start:08x}"]),
                QTreeWidgetItem(["End", f"0x{self.group.loc.end:08x}"]),
                QTreeWidgetItem(["Size", f"0x{self.group.loc.size:08x}"]),
            ]
        )
        item.setExpanded(True)

        for child in self.group.children():
            if isinstance(child, Group):
                item = GroupChild(group=child)
                item.setText(0, child.type.decode("ascii"))
                item.setText(2, child.get_friendly_label())
                item.setForeground(2, QtGui.QBrush(ColorPurple))
                self.group.file.io.seek(child.loc.end)
                self.viewer.details.addTopLevelItem(item)
                continue

            item = RecordChild(record=child)
            item.setText(0, child.type.decode("ascii"))
            item.setText(1, f"{child.form_id:08x}")
            item.setToolTip(1, tr("GroupViewer", "Form ID", None))
            item.setFont(1, monospace())
            item.setForeground(1, QtGui.QBrush(ColorGray))

            if child.flags & RecordFlag.Deleted:
                item.setForeground(0, QtGui.QBrush(ColorRed))

            for field in child.fields():
                # As a special case, we pull up any EDID fields to the top
                # level of the tree as a label for the record.
                if field.type == b"EDID":
                    with BytesIO(field.data) as data:
                        io = BinaryReader(data)
                        with io as edid:
                            edid.cstring("name")
                            item.setText(2, edid.data["name"])
                            item.setToolTip(
                                2, tr("GroupViewer", "Editor ID", None)
                            )
                            item.setForeground(
                                2,
                                QtGui.QBrush(ColorPurple),
                            )

                    break

            self.viewer.details.addTopLevelItem(item)
            self.group.file.io.seek(child.loc.end)

        self.s.progressDone.emit()


class GroupViewer(Viewer):
    """
    Displays a single group in a tree view.

    Uses a background thread to load the group and populate the tree without
    blocking the UI thread.
    """

    def __init__(self, group: Group, working_area: QLayout):
        super().__init__(working_area=working_area)

        self.group = group
        self.file = group.file.file
        self.file.seek(0)
        self.group = dataclasses.replace(
            self.group, file=ESMContainer(self.file)
        )

        self.details = QTreeWidget(self)
        self.details.hide()
        self.details.setUniformRowHeights(True)
        self.details.setColumnCount(3)
        self.details.setHeaderLabels(
            (
                tr("GroupViewer", "Type", None),
                tr("GroupViewer", "Form ID", None),
                tr("GroupViewer", "EDID", None),
            )
        )
        self.details.itemDoubleClicked.connect(self.on_item_double_clicked)

        loader = GroupLoaderThread(self, group)
        loader.s.progressStart.connect(
            self.on_loading_start, QtCore.Qt.QueuedConnection  # noqa
        )
        loader.s.progressDone.connect(
            self.on_loading_complete, QtCore.Qt.QueuedConnection  # noqa
        )
        QThreadPool.globalInstance().start(loader)

        self.layout.insertWidget(0, self.details)

    def on_loading_complete(self):
        super().on_loading_complete()
        self.details.show()

    def on_item_double_clicked(self, item: QTreeWidgetItem, column: int):
        if isinstance(item, GroupChild):
            self.add_panel(
                "child",
                GroupViewer(item.group, self.working_area),
            )
        elif isinstance(item, RecordChild):
            self.add_panel(
                "child", RecordViewer(item.record, self.working_area)
            )
