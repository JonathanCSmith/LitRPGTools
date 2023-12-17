from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, List

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPainter, QBrush, QColor, QPen, QResizeEvent, QMoveEvent, QWheelEvent
from PyQt6.QtWidgets import QSplitter, QWidget, QHBoxLayout, QCheckBox, QDialog, QComboBox

if TYPE_CHECKING:
    from desktop.guis import DesktopGUI


class Content:
    __metaclass__ = ABC

    @abstractmethod
    def fill_content(self):
        pass

    @abstractmethod
    def clear_content(self):
        pass


class MemoryModalDialog(QDialog):
    def __init__(self, gui: 'DesktopGUI', *args, **kwargs):
        super(MemoryModalDialog, self).__init__(*args, **kwargs)
        self.desktop_gui = gui
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowMinMaxButtonsHint)
        if self.desktop_gui.runtime.session.modal_geometry is not None:
            self.restoreGeometry(self.desktop_gui.runtime.session.modal_geometry)
        if self.desktop_gui.runtime.session.modal_state:
            self.showMaximized()

    def moveEvent(self, event: QMoveEvent) -> None:
        self.desktop_gui.runtime.set_modal_window_properties(self.saveGeometry(), self.windowState().value == 2)

    def resizeEvent(self, event: QResizeEvent) -> None:
        self.desktop_gui.runtime.set_modal_window_properties(self.saveGeometry(), self.windowState().value == 2)


class ShadedWidget(QWidget):
    def paintEvent(self, event):
        painter = QPainter()
        painter.begin(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(event.rect(), QBrush(QColor(35, 35, 35, 127)))
        painter.setPen(QPen(Qt.PenStyle.NoPen))


class SplitterHandle(QWidget):
    def paintEvent(self, e=None):
        painter = QPainter(self)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(Qt.BrushStyle.Dense6Pattern)
        painter.drawRect(self.rect())


class VisibleDynamicSplitPanel(QSplitter):
    def addWidget(self, widget: QWidget):
        super().addWidget(widget)
        self.width = self.handleWidth()
        hand = SplitterHandle()
        hand.setMaximumSize(self.width * 2, self.width * 10)
        layout = QHBoxLayout(self.handle(self.count() - 1))
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(hand)


def add_checkbox_in_table_at(table, row_index, column_index=1, state=False, callback=None):
    check_box = QCheckBox()

    # Handle the initial state
    if state:
        check_box.setCheckState(Qt.CheckState.Checked)
    else:
        check_box.setCheckState(Qt.CheckState.Unchecked)

    # Handle a callback
    if callback is not None:
        check_box.stateChanged.connect(callback)

    table.setCellWidget(row_index, column_index, check_box)


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
