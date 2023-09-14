import itertools
from io import BytesIO
from pathlib import Path

from PySide6.QtCore import QRunnable, Signal
from PySide6.QtWidgets import (
    QLayout,
    QTreeWidget,
    QTreeWidgetItem,
    QHeaderView,
    QSizePolicy,
    QWidget,
)

from starhopper.formats.btdx.file import BA2Container
from starhopper.formats.esm.file import ESMContainer, Group
from starhopper.gui import search
from starhopper.gui.common import (
    ColorPurple,
    tr,
    ColorGray,
    ColorOrange,
    ColorGreen,
    monospace,
)
from starhopper.gui.search import SearchResult

from starhopper.gui.viewers.viewer import Viewer
from starhopper.io import BinaryReader


class SearchResultNode(QTreeWidgetItem):
    def __init__(self, result: SearchResult):
        super().__init__()

        self.result = result
        self.setText(0, Path(result.file_path).name)
        self.setText(1, result.stored_text)
        self.setText(2, result.item_type.name)
        self.setForeground(0, ColorGray)

        match result.item_type:
            case search.ItemType.EDID:
                self.setForeground(1, ColorPurple)
            case search.ItemType.FORM_ID:
                self.setText(1, f"0x{result.stored_text}")
                self.setFont(1, monospace())
                self.setForeground(1, ColorOrange)
            case search.ItemType.FILE:
                self.setForeground(1, ColorGreen)


class SearchViewer(Viewer):
    """
    A viewer for search results.
    """

    onSearchSelected = Signal(list)

    def __init__(self, working_area: QLayout):
        super().__init__(working_area=working_area)

        self.tree = QTreeWidget()
        self.tree.setAlternatingRowColors(True)
        self.tree.setUniformRowHeights(True)
        self.tree.setColumnCount(3)
        self.tree.setHeaderLabels(
            (
                tr("Search", "File", None),
                tr("Search", "Text", None),
                tr("Search", "Type", None),
            )
        )
        self.tree.itemDoubleClicked.connect(self.on_item_double_clicked)

        header = self.tree.header()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setStretchLastSection(False)

        self.layout.insertWidget(0, self.tree)
        self.setSizePolicy(
            QSizePolicy.MinimumExpanding,
            QSizePolicy.MinimumExpanding,
        )

    def update_search_results(self, text: str):
        self.tree.clear()

        items = []
        for result in search.search_index(f"%{text}%"):
            item = SearchResultNode(result)
            items.append(item)

        self.tree.addTopLevelItems(items)

    def on_item_double_clicked(self, item: QTreeWidgetItem, column: int):
        if not isinstance(item, SearchResultNode):
            return

        self.onSearchSelected.emit(item.result.navigation_path)


class SearchIndexThread(QRunnable):
    """
    Loads a file in the background, scanning it to populate a search index.
    """

    def __init__(self, file: str):
        super().__init__()
        self.file = Path(file)

    def run(self):
        match self.file.suffix:
            case ".esm":
                with open(self.file, "rb") as handle:
                    item = ESMContainer(handle)
                    for top_level_group in item.groups:
                        path = [top_level_group]
                        while path:
                            parent = path.pop()
                            for record in parent.children():
                                if isinstance(record, Group):
                                    path.append(record)
                                    continue

                                search.add_to_index(
                                    str(self.file),
                                    [
                                        str(self.file),
                                        top_level_group.label.decode("ascii"),
                                        f"{record.form_id:08X}",
                                    ],
                                    f"{record.form_id:08X}",
                                    search.ItemType.FORM_ID,
                                )

                                for field in record.fields():
                                    if field.type != b"EDID":
                                        continue

                                    with BytesIO(field.data) as data:
                                        io = BinaryReader(data)
                                        label = io.cstring()
                                        search.add_to_index(
                                            str(self.file),
                                            [
                                                str(self.file),
                                                top_level_group.label.decode(
                                                    "ascii"
                                                ),
                                                label,
                                            ],
                                            label,
                                            search.ItemType.EDID,
                                        )

            case ".ba2":
                with open(self.file, "rb") as handle:
                    item = BA2Container()
                    item.read_from_file(handle)
                    for file in item.files():
                        search.add_to_index(
                            str(self.file),
                            [str(self.file), file.path],
                            file.path,
                            search.ItemType.FILE,
                        )
            case _:
                return
