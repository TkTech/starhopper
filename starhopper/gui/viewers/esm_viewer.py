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

        self.top_level_groups = QTreeWidget()
        self.top_level_groups.setColumnCount(1)
        self.top_level_groups.setHeaderHidden(True)
        self.top_level_groups.setAlternatingRowColors(True)
        self.top_level_groups.itemDoubleClicked.connect(
            self.on_item_double_clicked
        )
        self.top_level_groups.setSizePolicy(
            QSizePolicy.Minimum, QSizePolicy.MinimumExpanding
        )

        for group in self.esm.groups:
            item = ESMViewerNode(self.esm, group)
            self.top_level_groups.addTopLevelItem(item)

        self.layout.insertWidget(0, self.top_level_groups)
        self.setMinimumWidth(0)

    def on_item_double_clicked(self, item: QTreeWidgetItem, column: int):
        if isinstance(item, ESMViewerNode):
            self.add_panel(
                "child",
                GroupViewer(item.group, working_area=self.working_area),
            )
