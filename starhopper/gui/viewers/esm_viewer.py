from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush
from PySide6.QtWidgets import QLayout, QTreeWidget, QTreeWidgetItem, QSizePolicy

from starhopper.formats.esm.file import ESMContainer, Group
from starhopper.formats.esm.records.base import get_all_records
from starhopper.gui.common import ColorGreen, monospace
from starhopper.gui.viewers.group_viewer import GroupViewer
from starhopper.gui.viewers.viewer import Viewer


class ESMViewerNode(QTreeWidgetItem):
    def __init__(self, esm: ESMContainer, group: Group):
        super().__init__()
        self.esm = esm
        self.group = group

        self.setText(0, group.label.decode("ascii"))

        handler = get_all_records().get(group.label)
        if handler:
            self.setText(0, handler.label())
            self.setForeground(0, QBrush(ColorGreen))
        else:
            self.setFont(0, monospace())


class ESMViewer(Viewer):
    def __init__(self, esm: ESMContainer, working_area: QLayout):
        super().__init__(working_area=working_area)
        self.esm = esm

        self.tree = QTreeWidget()
        self.tree.setColumnCount(1)
        self.tree.setHeaderHidden(True)
        self.tree.setAlternatingRowColors(True)
        self.tree.itemDoubleClicked.connect(self.on_item_double_clicked)
        self.tree.setSizePolicy(
            QSizePolicy.Minimum, QSizePolicy.MinimumExpanding
        )

        for group in self.esm.groups:
            item = ESMViewerNode(self.esm, group)
            self.tree.addTopLevelItem(item)

        self.layout.insertWidget(0, self.tree)
        self.setMinimumWidth(0)

    def on_item_double_clicked(self, item: QTreeWidgetItem, column: int):
        self.open_item(item)

    def open_item(self, item: QTreeWidgetItem) -> Viewer | None:
        if not isinstance(item, ESMViewerNode):
            return

        viewer = GroupViewer(item.group, working_area=self.working_area)
        self.add_panel("child", viewer)
        return viewer

    def navigate(self, path: list[str]):
        try:
            component = path.pop(0)
        except IndexError:
            return

        items = self.tree.findItems(
            component, Qt.MatchExactly | Qt.MatchRecursive
        )

        for item in items:
            if not isinstance(item, ESMViewerNode):
                continue

            if item.group.label.decode("ascii") == component:
                self.tree.setCurrentItem(item)
                viewer = self.open_item(item)
                viewer.navigate(path)
