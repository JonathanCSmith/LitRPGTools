import os
import sys

from PyQt6.QtWidgets import QApplication

from main import LitRPGToolsInstance
from session import LitRPGToolsSession
from desktop.gui import LitRPGToolsDesktopGUI


class LitRPGToolsDesktop(LitRPGToolsInstance):
    def __init__(self):
        super().__init__()
        self.application = QApplication(sys.argv)
        self.session = LitRPGToolsSession(self)
        self.gui = None
        self.data_directory = None

    def start(self):
        self.gui = LitRPGToolsDesktopGUI(self, self.session, self.application)
        super().start()

    def run(self):
        if not self.started:
            print("Application has not been started")
            return

        self.gui.show()
        sys.exit(self.application.exec())

    def get_data_directory(self):
        return self.data_directory

    def set_data_directory(self, data_directory: str):
        if os.path.exists(data_directory):
            self.data_directory = data_directory

    def get_autosave_directory(self):
        return os.getcwd()
