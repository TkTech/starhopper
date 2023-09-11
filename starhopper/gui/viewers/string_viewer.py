from pathlib import Path

from PySide6.QtWidgets import QLayout, QTreeWidget, QTreeWidgetItem

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

        self.layout.insertWidget(0, self.details)
