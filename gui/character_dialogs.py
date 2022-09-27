from PyQt6.QtWidgets import QDialog, QLineEdit, QPushButton, QFormLayout, QComboBox


class CharacterSelectDialog(QDialog):
    def __init__(self, engine):
        super().__init__()
        self.engine = engine

        # Form Content
        self.character_selector = QComboBox()
        self.character_selector.addItems(self.engine.get_characters())
        self.done_button = QPushButton("Done")
        self.done_button.clicked.connect(self.handle_done)

        # Form Layout
        self.form_layout = QFormLayout()
        self.form_layout.addRow("Character:", self.character_selector)
        self.form_layout.addRow("", self.done_button)
        self.setLayout(self.form_layout)
        self.setMinimumWidth(640)

        self.viable = False

    def handle_done(self, *args):
        self.viable = True
        self.close()


class CharacterDialog(QDialog):
    def __init__(self, engine):
        super().__init__()
        self.engine = engine
        self.viable = False

        # Form content
        self.character_name = QLineEdit()
        self.done_button = QPushButton("Done")
        self.done_button.clicked.connect(self.handle_done)

        # Layout
        self.layout = QFormLayout()
        self.layout.addRow("Character Name: ", self.character_name)
        self.layout.addRow("", self.done_button)
        self.setLayout(self.layout)

    def handle_done(self):
        self.viable = True
        self.close()
