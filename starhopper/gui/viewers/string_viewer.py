import csv
from pathlib import Path

from PySide6.QtWidgets import (
    QLayout,
    QTreeWidget,
    QTreeWidgetItem,
    QFileDialog,
    QPushButton,
)

from starhopper.formats.archive import AbstractFile
from starhopper.formats.strings import StringContainer, StringContainerType
from starhopper.gui.common import tr
from starhopper.gui.viewers.viewer import Viewer


class StringViewer(Viewer):
    """
    Viewer for Bethesda .strings, .dlstrings, and .ilstrings files, typically
    containing translations.
    """

    def __init__(self, file: AbstractFile, working_area: QLayout):
        super().__init__(working_area)

        self.file = file

        match Path(self.file.path).suffix.lower():
            case ".strings":
                self._type = StringContainerType.Strings
            case ".dlstrings":
                self._type = StringContainerType.DLStrings
            case ".ilstrings":
                self._type = StringContainerType.ILStrings
            case _:
                raise ValueError("Invalid file type")

        self.details = QTreeWidget()
        self.details.setUniformRowHeights(True)
        self.details.setColumnCount(2)
        self.details.setAlternatingRowColors(True)
        self.details.setHeaderLabels(
            (
                tr("StringViewer", "ID", None),
                tr("StringViewer", "String", None),
            )
        )

        with self.file.open() as data:
            self.strings = StringContainer(data, self._type)
            for string_id, string in self.strings.strings.items():
                item = QTreeWidgetItem()
                item.setText(0, str(string_id))
                item.setText(1, string)
                self.details.addTopLevelItem(item)

        self.export_button = QPushButton(
            tr("StringViewer", "E&xport as CSV", None)
        )
        self.export_button.clicked.connect(self.on_export_button_clicked)

        self.layout.insertWidget(0, self.details)
        self.layout.insertWidget(1, self.export_button)

    def on_export_button_clicked(self):
        fname, _ = QFileDialog.getSaveFileName(
            self,
            tr("ModelViewer", "Export As", None),
            filter=tr("ModelViewer", "CSV (*.csv)", None),
        )

        if not fname:
            return

        with open(fname, "w") as f:
            writer = csv.writer(f)
            writer.writerow(("ID", "String"))
            for string_id, string in self.strings.strings.items():
                writer.writerow((str(string_id), string))
