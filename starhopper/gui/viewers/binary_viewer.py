import struct
from io import BytesIO

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QLayout,
    QWidget,
    QVBoxLayout,
    QTreeWidget,
    QTreeWidgetItem,
    QHeaderView,
    QSizePolicy,
)

from starhopper.gui.common import tr, ColorGray
from starhopper.gui.viewers.viewer import Viewer
from starhopper.io import BinaryReader


class TypeGuesser(QWidget):
    def __init__(self, data: bytes):
        super().__init__()
        self.data = data

        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.tree = QTreeWidget()

        self.tree.setColumnCount(2)
        self.tree.setHeaderLabels(
            (
                tr("BinaryViewer", "Type", None),
                tr("BinaryViewer", "Value", None),
            )
        )
        header = self.tree.header()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        self.tree.setAlternatingRowColors(True)
        self.tree.setSizePolicy(
            QSizePolicy.Minimum, QSizePolicy.MinimumExpanding
        )

        with BytesIO(self.data) as stream:
            io = BinaryReader(stream)
            for offset in range(0, 3):
                item = QTreeWidgetItem((f"{offset} byte offset",))
                item.setFirstColumnSpanned(2)
                item.setForeground(0, ColorGray)
                f = self.tree.font()
                f.setItalic(True)
                item.setFont(0, f)
                self.tree.addTopLevelItem(item)

                to_try = (
                    ("uint8", io.uint8, 1),
                    ("uint16", io.uint16, 2),
                    ("uint32", io.uint32, 4),
                    ("uint64", io.uint64, 8),
                    ("int8", io.int8, 1),
                    ("int16", io.int16, 2),
                    ("int32", io.int32, 4),
                    ("int64", io.int64, 8),
                    ("float", io.float_, 4),
                    ("double", io.double, 8),
                    ("string", lambda: io.read(16), None),
                )

                stream.seek(offset)
                for label, reader, size in to_try:
                    try:
                        value = reader()
                    except (EOFError, struct.error):
                        value = None
                    finally:
                        stream.seek(offset)

                    item = QTreeWidgetItem((label, repr(value)))
                    item.setTextAlignment(0, Qt.AlignLeft)
                    item.setTextAlignment(1, Qt.AlignRight)
                    if value is None:
                        item.setForeground(1, ColorGray)
                    self.tree.addTopLevelItem(item)

        self.layout.addWidget(self.tree)
        self.setLayout(self.layout)


class BinaryViewer(Viewer):
    """
    Simplistic binary viewer.

    Not optimized at all for large files. Should be replaced with a better
    implementation that can use memoryviews() or IO.
    """

    def __init__(self, data: bytes, working_area: QLayout):
        super().__init__(working_area=working_area)

        self.data = data

        # If the data is small enough, it's _probably_ a simple type, so lets
        # just try showing it as _everything_.
        self.type_guesser = TypeGuesser(data)
        self.layout.insertWidget(0, self.type_guesser)
        self.setMinimumWidth(0)
