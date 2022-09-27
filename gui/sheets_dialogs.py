from PyQt6.QtWidgets import QDialog, QFormLayout, QLineEdit, QPushButton, QComboBox


class TagDialog(QDialog):
    def __init__(self, main):
        super().__init__()
        self.viable = False
        self.__main = main

        # Form content
        self.tag_name = QLineEdit()
        self.tag_target = QComboBox()
        self.tag_target.addItem('NONE')
        self.done_button = QPushButton("Done")
        self.done_button.clicked.connect(self.handle_done)

        # Add the sheets
        sheets = self.__main.get_available_sheets()
        self.tag_target.addItems(sheets)

        # layout
        self.layout = QFormLayout()
        self.layout.addRow("Tag Name:", self.tag_name)
        self.layout.addRow("Tag URL (gsheet):", self.tag_target)
        self.layout.addRow("", self.done_button)
        self.setLayout(self.layout)

    def handle_done(self):
        self.viable = True
        self.close()
