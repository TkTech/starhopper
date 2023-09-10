from PySide6 import QtGui, QtCore
from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QWidget,
    QTreeWidget,
    QVBoxLayout,
    QTreeWidgetItem,
    QLayout,
)

from starhopper.formats.esm.file import Group
from starhopper.formats.esm.records.base import get_all_records

from starhopper.gui.common import tr, monospace
from starhopper.gui.group_viewer import GroupViewer


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
        if isinstance(item, ChildNode):
            if self.viewer is not None:
                self.viewer.close()

            self.viewer = GroupViewer(item.group, self.working_area)
            self.viewer.addedNewPanel.connect(
                self.addedNewPanel.emit, QtCore.Qt.QueuedConnection  # noqa
            )
            self.working_area.addWidget(self.viewer)
            self.addedNewPanel.emit(self.viewer)


class ChildNode(QTreeWidgetItem):
    def __init__(self, group: Group):
        super().__init__()

        self.group = group
        self.setFont(0, monospace())
        self.setText(0, group.label.decode("ascii"))

        handler = get_all_records().get(group.label, None)
        if handler:
            self.setText(1, handler.label().decode("ascii"))
            self.setForeground(1, QtGui.QBrush(QtGui.QColor(122, 122, 122)))
