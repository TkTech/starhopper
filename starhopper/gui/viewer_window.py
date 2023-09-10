from PySide6 import QtCore, QtGui
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import QVBoxLayout, QProgressBar, QWidget


class ViewerWindow(QWidget):
    def __init__(self):
        super().__init__()
        # Get rid of an ugly Qt icon on each subwindow.
        self.setWindowIcon(QIcon(QPixmap(1, 1)))
        # Doesn't seem to be strictly necessary since PySide is using object
        # lifecycle rules for this, but just in case...
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)  # noqa

        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.progress = QProgressBar()
        self.progress.setMaximumHeight(12)
        self.progress.hide()
        self.layout.addWidget(self.progress)

        self.setLayout(self.layout)

    def on_progress_update(self, value):
        self.progress.setValue(value)

    def on_progress_set_maximum(self, value):
        self.progress.show()
        self.progress.setMaximum(value)

    def on_progress_complete(self):
        self.progress.hide()
