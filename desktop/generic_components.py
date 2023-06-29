from PyQt6.QtCore import Qt
from PyQt6.QtGui import QWheelEvent
from PyQt6.QtWidgets import QComboBox


class LessIntrusiveComboBox(QComboBox):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def wheelEvent(self, e: QWheelEvent) -> None:
        if self.hasFocus():
            return super(LessIntrusiveComboBox, self).wheelEvent(e)
        else:
            return self.parent.wheelEvent(e)