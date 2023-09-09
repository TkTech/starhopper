import dataclasses
import os
import sys
from functools import cache
from pathlib import Path

from PySide6 import QtCore, QtGui
from PySide6.QtCore import (
    QTranslator,
    QCoreApplication,
    QThread,
    Signal,
)
from PySide6.QtGui import QKeySequence, QFont, QPixmap, QIcon
from PySide6.QtWidgets import (
    QApplication,
    QTreeWidget,
    QWidget,
    QVBoxLayout,
    QMainWindow,
    QMdiArea,
    QSplitter,
    QFileDialog,
    QTreeWidgetItem,
    QProgressBar,
)

from starhopper.formats.esm.file import Group, ESMFile
from starhopper.gui.settings import HasSettings

tr = QCoreApplication.translate


@cache
def monospace():
    font = QFont("Monospace")
    font.setStyleHint(QFont.Monospace)
    return font


class SearchIndexThread(QThread):
    def __init__(self, file: str):
        super().__init__()
        self.file = file

    def run(self):
        with open(self.file, "rb") as src:
            esm = ESMFile(src)
            for group in esm.groups:
                pass


class GroupLoaderThread(QThread):
    """
    Loads a group in the background and populates the details view.
    """

    progressUpdate = Signal(int)
    progressSetMaximum = Signal(int)
    progressDone = Signal()

    def __init__(self, viewer: "GroupViewer", group: Group):
        super().__init__()
        self.viewer = viewer
        self.group = group

    def run(self):
        self.progressSetMaximum.emit(self.group.loc.size)

        item = QTreeWidgetItem(self.viewer.details)
        item.setText(0, tr("GroupViewer", "Details", None))
        item.addChildren(
            [
                QTreeWidgetItem(["Type", self.group.type.decode("ascii")]),
                QTreeWidgetItem(["Size", f"{self.group.size} bytes"]),
                QTreeWidgetItem(["Label", repr(self.group.label)]),
                QTreeWidgetItem(["Group Type", str(self.group.group_type)]),
                QTreeWidgetItem(["Version", str(self.group.version)]),
                QTreeWidgetItem(["Start", f"{self.group.loc.start:08x}"]),
                QTreeWidgetItem(["End", f"0x{self.group.loc.end:08x}"]),
                QTreeWidgetItem(["Size", f"0x{self.group.loc.size:08x}"]),
            ]
        )
        item.setExpanded(True)

        last_update_at = 0
        for child in self.group.children():
            item = QTreeWidgetItem(self.viewer.details)
            item.setText(0, child.type.decode("ascii"))
            item.setText(1, f"{child.form_id:08x}")
            item.setToolTip(1, tr("GroupViewer", "Form ID", None))
            item.setFont(1, monospace())
            item.setForeground(1, QtGui.QBrush(QtGui.QColor(122, 122, 122)))

            for field in child.fields():
                field_item = QTreeWidgetItem(item)
                field_item.setText(0, field.type.decode("ascii"))

                if field.type == b"EDID":
                    data = field.decompose()
                    item.setText(
                        2,
                        data.get("name", "Unknown"),
                    )
                    item.setToolTip(2, tr("GroupViewer", "Editor ID", None))
                    item.setForeground(
                        2,
                        QtGui.QBrush(QtGui.QColor(122, 122, 122)),
                    )

                data = field.decompose()

                def _make_children(top: QTreeWidgetItem, data: dict):
                    for k, v in data.items():
                        it = QTreeWidgetItem(top)
                        it.setText(0, k)
                        if isinstance(v, dict):
                            _make_children(it, v)
                        elif isinstance(v, (list, tuple)):
                            it.setText(1, repr(v[0]))
                            it.setText(2, v[1])
                            f = it.font(0)
                            f.setItalic(True)
                            it.setFont(2, f)
                        else:
                            it.setText(1, str(v))

                if data:
                    _make_children(field_item, data)

            # Only emit updates every 1MB to avoid slowing down the UI.
            if child.loc.end - last_update_at > 1024 * 1024:
                last_update_at = child.loc.end
                self.progressUpdate.emit(child.loc.end)

        self.progressDone.emit()


class GroupViewer(QWidget):
    def __init__(self, group: Group):
        super().__init__()

        # Get rid of an ugly Qt icon on each subwindow.
        self.setWindowIcon(QIcon(QPixmap(1, 1)))
        # Doesn't seem to be strictly necessary since PySide is using object
        # lifecycle rules for this, but just in case...
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)

        # We're going to be creating a new file handle for this group, so we
        # can seek around in it without affecting any other views.
        self.group = group
        self.file = os.fdopen(os.dup(group.file.file.fileno()), "rb")
        self.file.seek(0)
        self.group = dataclasses.replace(self.group, file=ESMFile(self.file))

        self.details = QTreeWidget(self)
        self.details.setUniformRowHeights(True)
        self.details.setColumnCount(3)
        self.details.setHeaderLabels(
            (
                tr("GroupViewer", "Type", None),
                tr("GroupViewer", "Form ID", None),
                tr("GroupViewer", "EDID", None),
            )
        )

        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.progress = QProgressBar()
        self.progress.setMaximumHeight(12)
        self.layout.addWidget(self.details)
        self.layout.addWidget(self.progress)

        self.setLayout(self.layout)

        self.loader = GroupLoaderThread(self, group)
        self.loader.progressUpdate.connect(
            self.on_progress_update, QtCore.Qt.QueuedConnection  # noqa
        )
        self.loader.progressSetMaximum.connect(
            self.on_progress_set_maximum, QtCore.Qt.QueuedConnection  # noqa
        )
        self.loader.progressDone.connect(
            self.on_progress_complete, QtCore.Qt.QueuedConnection  # noqa
        )
        self.loader.start()

    def on_progress_update(self, value):
        self.progress.setValue(value)

    def on_progress_set_maximum(self, value):
        self.progress.setMaximum(value)

    def on_progress_complete(self):
        self.progress.hide()
        self.loader = None

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        self.file.close()
        super().closeEvent(event)


class ChildNode(QTreeWidgetItem):
    def __init__(self, group: Group):
        super().__init__()

        self.group = group
        self.setFont(0, monospace())
        self.setText(0, group.label.decode("ascii"))


class FileNode(QTreeWidgetItem):
    def __init__(self, file: str):
        super().__init__()
        self.file = Path(file)
        self.handle = open(file, "rb")
        self.esm = ESMFile(self.handle)

        self.setText(0, self.file.name)
        self.setFirstColumnSpanned(True)

        for group in self.esm.groups:
            self.addChild(ChildNode(group))


class Navigation(QWidget):
    def __init__(self, working_area: QMdiArea):
        super().__init__()

        self.working_area = working_area

        self.tree = QTreeWidget()
        self.tree.setColumnCount(1)
        self.tree.setHeaderHidden(True)
        self.tree.setHeaderLabels((tr("Navigation", "Type", None),))
        self.tree.itemDoubleClicked.connect(self.on_item_double_clicked)

        self.layout = QVBoxLayout(self)
        self.layout.addWidget(self.tree)
        self.layout.setContentsMargins(0, 0, 0, 0)

    def on_item_double_clicked(self, item: QTreeWidgetItem, column: int):
        if isinstance(item, ChildNode):
            self.working_area.addSubWindow(GroupViewer(item.group)).show()


class Details(QWidget):
    def __init__(self):
        super().__init__()

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.setLayout(self.layout)


class MainWindow(HasSettings, QMainWindow):
    def __init__(self):
        super().__init__()
        self.search_index_threads = []
        self.setWindowTitle("StarHopper")

        self.menu = self.menuBar()
        self.menu_file = self.menu.addMenu(tr("MainWindow", "File", None))
        self.menu_viewers = self.menu.addMenu(tr("MainWindow", "Viewers", None))

        open_action = self.menu_file.addAction(tr("MainWindow", "Open", None))
        open_action.setShortcut(QKeySequence.Open)
        open_action.triggered.connect(self.on_open_file)

        self.menu_file.addSeparator()

        file_exit = self.menu_file.addAction(tr("MainWindow", "Exit", None))
        file_exit.setShortcut(QKeySequence.Quit)
        file_exit.triggered.connect(self.on_close)

        self.mdi = QMdiArea()
        self.navigation = Navigation(working_area=self.mdi)

        close_all_action = self.menu_viewers.addAction(
            tr("MainWindow", "Close All", None)
        )
        close_all_action.triggered.connect(self.mdi.closeAllSubWindows)

        splitter = QSplitter()
        splitter.addWidget(self.navigation)
        splitter.addWidget(self.mdi)
        splitter.setSizes([300, 800])

        self.setCentralWidget(splitter)

    def settings_group_name(self) -> str:
        return "main"

    def on_close(self):
        QCoreApplication.quit()

    def on_open_file(self):
        fname, _ = QFileDialog.getOpenFileName(
            self,
            tr("MainWindow", "Open File", None),
            self.settings.value("last_open_dir", "."),
            tr("MainWindow", "Bethesda Files (*.esm *.esp)", None),
        )
        if not fname:
            return

        self.settings.setValue("last_open_dir", str(Path(fname).parent))
        self.navigation.tree.addTopLevelItem(FileNode(fname))

        sit = SearchIndexThread(fname)
        self.search_index_threads.append(sit)
        sit.start()

    def settings_load(self):
        self.restoreGeometry(self.settings.value("geometry"))
        self.restoreState(self.settings.value("state"))

    def settings_save(self):
        self.settings.setValue("geometry", self.saveGeometry())
        self.settings.setValue("state", self.saveState())


def create_app():
    app = QApplication([])
    app.setApplicationName("StarHopper")
    app.setOrganizationName("tktech")
    app.setOrganizationDomain("tkte.ch")

    translator = QTranslator()
    QCoreApplication.installTranslator(translator)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    create_app()
