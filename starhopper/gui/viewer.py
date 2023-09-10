from typing import Any

from PySide6 import QtCore, QtGui
from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QVBoxLayout,
    QProgressBar,
    QWidget,
    QSizePolicy,
    QLayout,
)


class Viewer(QWidget):
    """
    Base class for all viewers.

    Viewers are widgets that are displayed in the main window and typically
    contain Record or Field information.
    """

    addedNewPanel = Signal(QWidget)

    def __init__(self, working_area: QLayout):
        super().__init__()

        self.working_area = working_area
        self.child_panels = {}

        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.progress = QProgressBar()
        self.progress.setMaximumHeight(12)
        self.progress.hide()
        self.layout.addWidget(self.progress)

        self.setSizePolicy(
            QSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)
        )
        self.setMinimumWidth(400)
        self.setLayout(self.layout)

    def on_progress_update(self, value):
        self.progress.setValue(value)

    def on_progress_set_maximum(self, value):
        self.progress.show()
        self.progress.setMaximum(value)

    def on_progress_complete(self):
        self.progress.hide()

    def add_panel(self, key: Any, panel: QWidget):
        self.remove_panel(key)

        self.working_area.addWidget(panel)
        self.addedNewPanel.emit(panel)
        self.child_panels[key] = panel

        if isinstance(panel, Viewer):
            panel.addedNewPanel.connect(
                # No type information for QueuedConnection.
                self.addedNewPanel.emit,
                QtCore.Qt.QueuedConnection,  # noqa
            )

    def remove_panel(self, key: Any):
        if key not in self.child_panels:
            return

        panel = self.child_panels[key]
        panel.close()
        self.working_area.removeWidget(panel)
        del self.child_panels[key]

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        for panel in self.child_panels.values():
            panel.close()

        super().closeEvent(event)
