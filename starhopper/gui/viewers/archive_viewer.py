from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QLayout,
    QTreeWidget,
    QTreeWidgetItem,
    QPushButton,
    QHeaderView,
    QFileDialog,
)

from starhopper.formats.archive import ArchiveContainer, AbstractFile
from starhopper.gui.common import tr, monospace
from starhopper.gui.settings import HasSettings
from starhopper.gui.viewers.model_viewer import ModelViewer
from starhopper.gui.viewers.string_viewer import StringViewer
from starhopper.gui.viewers.viewer import Viewer


class ArchiveViewerNode(QTreeWidgetItem):
    def __init__(self, container: ArchiveContainer, file: AbstractFile):
        super().__init__()
        self.container = container
        self.file = file

        self.setText(0, file.path)
        self.setText(1, f"{file.size} bytes")
        self.setFont(1, monospace())
        self.setTextAlignment(1, Qt.AlignRight)
        self.setFlags(self.flags() | Qt.ItemIsUserCheckable)
        self.setCheckState(0, Qt.Unchecked)


class ArchiveViewer(HasSettings, Viewer):
    def __init__(self, container: ArchiveContainer, working_area: QLayout):
        super().__init__(working_area=working_area)
        self.container = container

        self.browser = QTreeWidget()
        self.browser.setColumnCount(2)
        self.browser.setUniformRowHeights(True)
        self.browser.setAlternatingRowColors(True)
        header = self.browser.header()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.browser.setHeaderLabels(
            (
                tr("ArchiveViewer", "Path", None),
                tr("ArchiveViewer", "Size", None),
            )
        )
        self.browser.itemDoubleClicked.connect(self.on_item_double_clicked)

        # TODO: Build up a directory tree here instead of lumping it all into
        #       the root.
        for file in container.files():
            item = ArchiveViewerNode(self.container, file)
            self.browser.addTopLevelItem(item)

        self.export_button = QPushButton(tr("ArchiveViewer", "&Export", None))
        self.export_button.clicked.connect(self.on_export_button_clicked)

        self.layout.insertWidget(0, self.browser)
        self.layout.insertWidget(1, self.export_button)

    def on_item_double_clicked(self, item: QTreeWidgetItem, column: int):
        if not isinstance(item, ArchiveViewerNode):
            return

        p = Path(item.file.path)
        match p.suffix:
            case ".strings" | ".dlstrings" | ".ilstrings":
                self.add_panel(
                    "child", StringViewer(item.file, self.working_area)
                )
            case ".mesh":
                self.add_panel(
                    "child", ModelViewer(item.file, self.working_area)
                )

    def on_export_button_clicked(self):
        items_to_extract = [
            item
            for item in self.browser.findItems(
                "", Qt.MatchContains | Qt.MatchRecursive
            )
            if isinstance(item, ArchiveViewerNode)
            and item.checkState(0) == Qt.Checked
        ]

        if not items_to_extract:
            return

        directory = QFileDialog.getExistingDirectory(
            self,
            tr("ArchiveViewer", "Export to", None),
            self.settings.value("last_open_dir", "."),
            QFileDialog.ShowDirsOnly,
        )

        # Should probably be moved into a thread.
        for item in items_to_extract:
            item.file.extract_into(Path(directory), overwrite=True)

    def settings_group_name(self) -> str:
        return "archive_viewer"
