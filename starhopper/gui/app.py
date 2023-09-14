import sys
from pathlib import Path

from PySide6 import QtCore
from PySide6.QtCore import (
    QTranslator,
    QCoreApplication,
    Signal,
    QThreadPool,
)
from PySide6.QtGui import QKeySequence, Qt
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
    QLabel,
    QPushButton,
)

from starhopper.gui.common import tr
from starhopper.gui.navigation import Navigation, ESMFileNode, ArchiveFileNode
from starhopper.gui.settings import HasSettings
from starhopper.gui.viewers.search_viewer import SearchViewer, SearchIndexThread


class SearchBox(QWidget):
    onTyping = Signal(str)

    def __init__(self):
        super().__init__()

        self.query = QLineEdit()
        self.query.setMinimumWidth(300)
        self.query.setPlaceholderText(tr("Search", "Search...", None))
        self.query.textChanged.connect(self.onTyping)

        self.progress = QProgressBar()
        self.progress.setTextVisible(True)
        self.progress.setMinimumWidth(300)
        self.progress.setFormat(tr("Search", "Indexing...", None))
        self.progress.setAlignment(QtCore.Qt.AlignCenter)
        self.progress.setMaximum(100)
        self.progress.setValue(50)

        self.layout = QVBoxLayout(self)
        self.layout.addWidget(self.query)
        self.layout.setContentsMargins(0, 0, 0, 0)


class Details(QWidget):
    def __init__(self):
        super().__init__()

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.setLayout(self.layout)


class StarterWidget(QWidget):
    """
    Shown in the main window when no other content has been loaded yet to
    provide an easy way to get started.
    """

    openFile = Signal()

    def __init__(self):
        super().__init__()

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.layout.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(
            QLabel(tr("MainWindow", "Welcome to StarHopper!", None))
        )
        self.layout.addWidget(
            QLabel(
                tr(
                    "MainWindow",
                    "To get started, open a file using the button below.",
                    None,
                )
            )
        )
        btn = QPushButton(
            tr("MainWindow", "Open File", None),
        )
        btn.clicked.connect(self.openFile.emit)
        self.layout.addWidget(btn)

        self.setLayout(self.layout)


class MainWindow(HasSettings, QMainWindow):
    fileAdded = Signal(str)

    def __init__(self):
        super().__init__()
        self.search_index_threads = []
        self.setWindowTitle("StarHopper")

        self.search_box = SearchBox()

        self.menu = self.menuBar()
        self.menu.setCornerWidget(
            self.search_box, QtCore.Qt.TopRightCorner  # noqa
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

        self.search_box.onTyping.connect(self.on_search)

        self.navigation = Navigation(working_area=self.panel_container_layout)
        self.navigation.setMinimumWidth(300)
        self.navigation.setSizePolicy(
            QSizePolicy.Minimum, QSizePolicy.Expanding
        )
        self.navigation.addedNewPanel.connect(
            self.on_added_new_panel, QtCore.Qt.QueuedConnection  # noqa
        )
        self.navigation.hide()

        self.search_view = SearchViewer(self.panel_container_layout)
        self.search_view.hide()
        self.search_view.onSearchSelected.connect(self.navigation.navigate)
        self.search_view.onSearchSelected.connect(self.close_search)

        starter = StarterWidget()
        starter.openFile.connect(self.on_open_file)
        self.fileAdded.connect(starter.close)
        self.panel_container_layout.addWidget(starter)

        splitter = QSplitter()
        splitter.addWidget(self.navigation)
        splitter.addWidget(self.panel_scroll_container)
        splitter.addWidget(self.search_view)
        splitter.setSizes([300, 800, 800])

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
                    item = ESMFileNode(fname)
                case ".ba2":
                    item = ArchiveFileNode(fname)
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
                    continue

            self.navigation.tree.addTopLevelItem(item)
            if self.navigation.tree.topLevelItemCount() > 1:
                self.navigation.show()
            else:
                self.navigation.on_item_double_clicked(item, 0)

            self.fileAdded.emit(fname)

            loader = SearchIndexThread(fname)
            QThreadPool.globalInstance().start(loader)

    def close_search(self):
        self.search_box.query.clear()
        self.search_view.hide()
        self.panel_scroll_container.show()

    def on_search(self, query: str):
        if not query:
            self.close_search()
            return

        self.panel_scroll_container.hide()
        self.search_view.show()
        self.search_view.update_search_results(query)

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
