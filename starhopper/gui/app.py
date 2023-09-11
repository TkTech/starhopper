import sys
from pathlib import Path

from PySide6 import QtCore
from PySide6.QtCore import (
    QTranslator,
    QCoreApplication,
    QThread,
)
from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QMainWindow,
    QSplitter,
    QFileDialog,
    QScrollArea,
    QHBoxLayout,
    QLayout,
    QSizePolicy,
    QLineEdit,
    QProgressBar,
    QMessageBox,
)

from starhopper.formats.esm.file import ESMContainer
from starhopper.gui.common import tr
from starhopper.gui.navigation import Navigation, ESMFileNode, BTDXFileNode
from starhopper.gui.settings import HasSettings


class SearchBox(QWidget):
    def __init__(self):
        super().__init__()

        self.query = QLineEdit()
        self.query.setMinimumWidth(300)
        self.query.setPlaceholderText(tr("Search", "Search...", None))

        self.progress = QProgressBar()
        self.progress.setTextVisible(True)
        self.progress.setMinimumWidth(300)
        self.progress.setFormat(tr("Search", "Indexing...", None))
        self.progress.setAlignment(QtCore.Qt.AlignCenter)
        self.progress.setMaximum(100)
        self.progress.setValue(50)

        self.layout = QVBoxLayout(self)
        # self.layout.addWidget(self.query)
        self.layout.setContentsMargins(0, 0, 0, 0)


class SearchIndexThread(QThread):
    def __init__(self, file: str):
        super().__init__()
        self.file = file

    def run(self):
        with open(self.file, "rb") as src:
            esm = ESMContainer(src)
            for group in esm.groups:
                pass


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
        self.global_search = SearchBox()
        self.menu.setCornerWidget(
            self.global_search, QtCore.Qt.TopRightCorner  # noqa
        )
        self.menu_file = self.menu.addMenu(tr("MainWindow", "File", None))

        open_action = self.menu_file.addAction(tr("MainWindow", "Open", None))
        open_action.setShortcut(QKeySequence.Open)
        open_action.triggered.connect(self.on_open_file)

        self.menu_file.addSeparator()

        file_exit = self.menu_file.addAction(tr("MainWindow", "Exit", None))
        file_exit.setShortcut(QKeySequence.Quit)
        file_exit.triggered.connect(self.on_close)

        self.panel_scroll_container = QScrollArea()
        self.panel_scroll_container.setWidgetResizable(True)
        self.panel_scroll_container.setSizePolicy(
            QSizePolicy.MinimumExpanding, QSizePolicy.Expanding
        )

        self.panel_container = QWidget()
        self.panel_container.setSizePolicy(
            QSizePolicy.Minimum, QSizePolicy.Minimum
        )
        self.panel_container.setMinimumWidth(800)
        self.panel_container_layout = QHBoxLayout(self.panel_container)
        self.panel_container_layout.setContentsMargins(0, 0, 0, 0)
        self.panel_container_layout.setSizeConstraint(QLayout.SetMinimumSize)
        self.panel_scroll_container.setWidget(self.panel_container)

        self.navigation = Navigation(working_area=self.panel_container_layout)
        self.navigation.setMinimumWidth(300)
        self.navigation.setSizePolicy(
            QSizePolicy.Minimum, QSizePolicy.Expanding
        )
        self.navigation.addedNewPanel.connect(
            self.on_added_new_panel, QtCore.Qt.QueuedConnection  # noqa
        )

        splitter = QSplitter()
        splitter.addWidget(self.navigation)
        splitter.addWidget(self.panel_scroll_container)
        splitter.setSizes([300, 800])

        self.setCentralWidget(splitter)

    def settings_group_name(self) -> str:
        return "main"

    def on_close(self):
        QCoreApplication.quit()

    def on_open_file(self):
        fnames, _ = QFileDialog.getOpenFileNames(
            self,
            tr("MainWindow", "Open File", None),
            self.settings.value("last_open_dir", "."),
            tr("MainWindow", "Bethesda Files (*.esm *.ba2)", None),
        )
        if not fnames:
            return

        for fname in fnames:
            path = Path(fname)
            self.settings.setValue("last_open_dir", str(path.parent))
            match path.suffix:
                case ".esm":
                    self.navigation.tree.addTopLevelItem(ESMFileNode(fname))
                case ".ba2":
                    self.navigation.tree.addTopLevelItem(BTDXFileNode(fname))
                case _:
                    QMessageBox.warning(
                        None,  # noqa
                        "StarHopper",
                        tr(
                            "MainWindow",
                            "Tried to open an unknown filetype :(",
                            None,
                        ),
                    )

        # sit = SearchIndexThread(fname)
        # self.search_index_threads.append(sit)
        # sit.start()

    def on_added_new_panel(self, panel: QWidget):
        self.panel_scroll_container.ensureWidgetVisible(panel)

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
