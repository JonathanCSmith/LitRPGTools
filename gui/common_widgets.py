from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPainter
from PyQt6.QtWidgets import QSplitter, QWidget, QHBoxLayout


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
