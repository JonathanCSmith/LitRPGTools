import abc
from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPainter
from PyQt6.QtWidgets import QSplitter, QWidget, QHBoxLayout, QCheckBox

if TYPE_CHECKING:
    from new.main import LitRPGToolsEngine
    from new.ui.desktop.gui import LitRPGToolsDesktopGUI


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


class Tab(QWidget):
    __metaclass__ = abc.ABCMeta

    def __init__(self, parent: 'LitRPGToolsDesktopGUI', engine: 'LitRPGToolsEngine'):
        super(Tab, self).__init__()
        self._parent = parent
        self._engine = engine

        # All tab props
        self.setContentsMargins(0, 0, 0, 0)

    @abc.abstractmethod
    def handle_update(self):
        pass
