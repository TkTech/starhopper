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

from starhopper.formats.btdx.file import BA2Container
from starhopper.formats.esm.file import ESMContainer

from starhopper.gui.common import (
    ColorTeal,
    ColorOrange,
)
from starhopper.gui.viewers.archive_viewer import ArchiveViewer
from starhopper.gui.viewers.esm_viewer import ESMViewer
from starhopper.gui.viewers.viewer import Viewer


class Navigation(QWidget):
    addedNewPanel = Signal(QWidget)

    def __init__(self, working_area: QLayout):
        super().__init__()

        self.working_area = working_area

        self.tree = QTreeWidget()
        self.tree.setColumnCount(1)
        self.tree.setHeaderHidden(True)
        self.tree.itemDoubleClicked.connect(self.on_item_double_clicked)

        self.layout = QVBoxLayout(self)
        self.layout.addWidget(self.tree)
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.viewer: QWidget | None = None

    def on_item_double_clicked(self, item: QTreeWidgetItem, column: int):
        if not isinstance(item, HandledChildNode):
            return

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


class ESMFileNode(HandledChildNode, QTreeWidgetItem):
    def __init__(self, file: str):
        super().__init__()
        self.file = Path(file)
        self.handle = open(file, "rb")
        self.esm = ESMContainer(self.handle)

        self.setText(0, self.file.name)
        self.setForeground(0, QtGui.QBrush(ColorOrange))

    def get_viewer(self, working_area: QLayout) -> Viewer | None:
        return ESMViewer(self.esm, working_area)


class ArchiveFileNode(HandledChildNode, QTreeWidgetItem):
    def __init__(self, file: str):
        super().__init__()
        self.file = Path(file)
        self.handle = open(file, "rb")
        self.container = BA2Container(self.handle)

        self.setText(0, self.file.name)
        self.setForeground(0, QtGui.QBrush(ColorTeal))

    def get_viewer(self, working_area: QLayout) -> Viewer | None:
        return ArchiveViewer(self.container, working_area)
