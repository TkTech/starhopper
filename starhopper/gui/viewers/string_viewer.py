from io import BytesIO
from pathlib import Path

from PySide6.QtWidgets import QLayout, QTreeWidget, QTreeWidgetItem

from starhopper.formats.btdx.file import GeneralFile
from starhopper.formats.strings import StringContainer, StringContainerType
from starhopper.gui.common import tr
from starhopper.gui.viewers.viewer import Viewer


class StringViewer(Viewer):
    def __init__(self, file: GeneralFile, working_area: QLayout):
        super().__init__(working_area)

        self.file = file

        match Path(self.file.path.decode("utf-8")).suffix.lower():
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

        with BytesIO(file.view_content()) as data:
            self.strings = StringContainer(data, self._type)
            for string_id, string in self.strings.strings.items():
                item = QTreeWidgetItem()
                item.setText(0, str(string_id))
                item.setText(1, string)
                self.details.addTopLevelItem(item)

        self.layout.insertWidget(0, self.details)
