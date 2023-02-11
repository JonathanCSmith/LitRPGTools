from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPainter, QBrush, QColor, QPen
from PyQt6.QtWidgets import QSplitter, QWidget, QHBoxLayout, QCheckBox


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
