from pathlib import Path

from PySide6 import QtGui, QtCore
from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QWidget,
    QTreeWidget,
    QVBoxLayout,
    QTreeWidgetItem,
    QLayout,
)

from starhopper.formats.btdx.file import BTDXContainer, GeneralFile
from starhopper.formats.esm.file import Group, ESMContainer
from starhopper.formats.esm.records.base import get_all_records

from starhopper.gui.common import (
    tr,
    monospace,
    ColorGray,
    ColorGreen,
    ColorTeal,
)
from starhopper.gui.viewers.group_viewer import GroupViewer
from starhopper.gui.viewers.string_viewer import StringViewer
from starhopper.gui.viewers.viewer import Viewer


class Navigation(QWidget):
    addedNewPanel = Signal(QWidget)

    def __init__(self, working_area: QLayout):
        super().__init__()

        self.working_area = working_area

        self.tree = QTreeWidget()
        self.tree.setColumnCount(2)
        self.tree.setHeaderLabels(
            (
                tr("Navigation", "Type", None),
                tr("Navigation", "Description", None),
            )
        )
        self.tree.itemDoubleClicked.connect(self.on_item_double_clicked)

        self.layout = QVBoxLayout(self)
        self.layout.addWidget(self.tree)
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.viewer: QWidget | None = None

    def on_item_double_clicked(self, item: QTreeWidgetItem, column: int):
        handled_type = (ESMChildNode, BTDXChildNode)
        if isinstance(item, handled_type):
            if self.viewer is not None:
                self.viewer.close()

            self.viewer = item.get_viewer(self.working_area)
            if self.viewer is None:
                return

            self.viewer.addedNewPanel.connect(
                self.addedNewPanel.emit, QtCore.Qt.QueuedConnection  # noqa
            )
            self.working_area.addWidget(self.viewer)
            self.addedNewPanel.emit(self.viewer)


class HandledChildNode:
    def get_viewer(self, working_area: QLayout) -> Viewer | None:
        return None


class ESMChildNode(HandledChildNode, QTreeWidgetItem):
    def __init__(self, group: Group):
        super().__init__()

        self.group = group
        self.setFont(0, monospace())
        self.setText(0, group.label.decode("ascii"))

        handler = get_all_records().get(group.label, None)
        if handler:
            self.setText(1, handler.label().decode("ascii"))
            self.setForeground(1, QtGui.QBrush(ColorGray))
            self.setForeground(0, QtGui.QBrush(ColorGreen))

    def get_viewer(self, working_area: QLayout) -> Viewer | None:
        return GroupViewer(self.group, working_area)


class ESMFileNode(QTreeWidgetItem):
    def __init__(self, file: str):
        super().__init__()
        self.file = Path(file)
        self.handle = open(file, "rb")
        self.esm = ESMContainer(self.handle)

        self.setText(0, self.file.name)

        for group in self.esm.groups:
            # Should probably be in a thread, but realistically this is
            # fast enough to be near-instantaneous.
            self.addChild(ESMChildNode(group))


class BTDXChildNode(HandledChildNode, QTreeWidgetItem):
    def __init__(self, file: GeneralFile):
        super().__init__()

        self.file = file
        self.setText(0, file.path.decode("utf-8"))

    def get_viewer(self, working_area: QLayout) -> Viewer | None:
        if self.file.path.endswith((b".strings", b".dlstrings", b".ilstrings")):
            return StringViewer(self.file, working_area)


class BTDXFileNode(QTreeWidgetItem):
    def __init__(self, file: str):
        super().__init__()
        self.file = Path(file)
        self.handle = open(file, "rb")
        self.container = BTDXContainer(self.handle)

        self.setText(0, self.file.name)
        self.setForeground(0, QtGui.QBrush(ColorTeal))

        for file in self.container.files:
            self.addChild(BTDXChildNode(file))
