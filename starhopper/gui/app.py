import sys
from pathlib import Path

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
    QMdiArea,
    QSplitter,
    QFileDialog,
    QTreeWidgetItem,
)

from starhopper.formats.esm.file import ESMFile
from starhopper.gui.common import tr
from starhopper.gui.navigation import Navigation, ChildNode
from starhopper.gui.settings import HasSettings


class SearchIndexThread(QThread):
    def __init__(self, file: str):
        super().__init__()
        self.file = file

    def run(self):
        with open(self.file, "rb") as src:
            esm = ESMFile(src)
            for group in esm.groups:
                pass


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

        cascade_all_action = self.menu_viewers.addAction(
            tr("MainWindow", "Cascade All", None)
        )
        cascade_all_action.triggered.connect(self.mdi.cascadeSubWindows)
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
