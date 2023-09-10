from functools import cache

from PySide6 import QtGui
from PySide6.QtCore import QCoreApplication
from PySide6.QtGui import QFont

tr = QCoreApplication.translate
ColorGray = QtGui.QColor(122, 122, 122)
ColorPurple = QtGui.QColor(122, 122, 255)
ColorRed = QtGui.QColor(255, 122, 122)


@cache
def monospace():
    font = QFont("Monospace")
    font.setStyleHint(QFont.Monospace)
    return font
