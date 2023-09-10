import dataclasses
import os
from io import BytesIO

from PySide6 import QtGui, QtCore
from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (
    QTreeWidgetItem,
    QTreeWidget,
    QMdiArea,
    QSizePolicy,
    QLayout,
    QScrollArea,
)

from starhopper.formats.esm.file import Group, ESMFile, Record, RecordFlag
from starhopper.gui.common import (
    tr,
    ColorGray,
    ColorPurple,
    monospace,
    ColorRed,
)
from starhopper.gui.record_viewer import RecordViewer
from starhopper.gui.viewer import Viewer
from starhopper.io import BinaryReader


class RecordChild(QTreeWidgetItem):
    def __init__(self, record: Record):
        super().__init__()
        self.record = record


class GroupChild(QTreeWidgetItem):
    def __init__(self, group: Group):
        super().__init__()
        self.group = group


class GroupLoaderThread(QThread):
    """
    Loads a group in the background and populates the details view.
    """

    progressUpdate = Signal(int)
    progressSetMaximum = Signal(int)
    progressDone = Signal()

    def __init__(self, viewer: "GroupViewer", group: Group):
        super().__init__()
        self.viewer = viewer
        self.group = group

    def run(self):
        self.progressSetMaximum.emit(self.group.loc.size)

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

        bytes_read = 0
        last_updated_at = 0
        for child in self.group.children():
            if isinstance(child, Group):
                item = GroupChild(group=child)
                item.setText(0, child.type.decode("ascii"))
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

            bytes_read += child.loc.size
            if bytes_read - last_updated_at > 1024:
                last_updated_at = bytes_read
                self.progressUpdate.emit(bytes_read)

        self.progressDone.emit()


class GroupViewer(Viewer):
    """
    Displays a single group in a tree view.

    Uses a background thread to load the group and populate the tree without
    blocking the UI thread.
    """

    def __init__(self, group: Group, working_area: QLayout):
        super().__init__(working_area=working_area)

        if group.label.isascii():
            self.setWindowTitle(f"Group Viewer: {group.label.decode('ascii')}")
        else:
            self.setWindowTitle(f"Group Viewer")

        # We're going to be creating a new file handle for this group, so we
        # can seek around in it without affecting any other views.
        self.group = group
        self.file = os.fdopen(os.dup(group.file.file.fileno()), "rb")
        self.file.seek(0)
        self.group = dataclasses.replace(self.group, file=ESMFile(self.file))

        self.details = QTreeWidget(self)
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

        self.loader = GroupLoaderThread(self, group)
        self.loader.progressUpdate.connect(
            self.on_progress_update, QtCore.Qt.QueuedConnection  # noqa
        )
        self.loader.progressSetMaximum.connect(
            self.on_progress_set_maximum, QtCore.Qt.QueuedConnection  # noqa
        )
        self.loader.progressDone.connect(
            self.on_progress_complete, QtCore.Qt.QueuedConnection  # noqa
        )
        self.loader.start()

        self.layout.insertWidget(0, self.details)

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        self.file.close()
        super().closeEvent(event)

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
