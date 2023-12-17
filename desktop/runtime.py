import os
import sys

from PyQt6.QtCore import QByteArray
from PyQt6.QtWidgets import QApplication, QMessageBox, QFileDialog
from platformdirs import user_data_dir

from desktop.guis import DesktopGUI, LitRPGToolsDesktopGUIProgressUpdater
from gsheets import GSheetsHandler
from main import LitRPGToolsRuntime, LitRPGToolsRuntimeSession
from utilities.io import load_json, save_json


class DesktopSession(LitRPGToolsRuntimeSession):
    def __init__(self):
        super().__init__()
        self.session_directory = user_data_dir(self.app_name, self.app_author)
        self.config_path = os.path.join(self.session_directory, self.app_name + ".json")
        self.autosave_path = os.path.join(self.session_directory, "autosave.litrpg")

        self.main_geometry = None
        self.main_state = True
        self.modal_geometry = None
        self.modal_state = True

    def load(self):
        # Check for file's existence
        if self.config_path is None or not os.path.isfile(self.config_path):
            return

        # Load
        tmp_session_data = load_json(self.config_path)
        self.last_activity = tmp_session_data.get(self.last_activity_key, "")

        tmp_main_geometry_data = tmp_session_data.get(self.main_geometry_key, "")
        if tmp_main_geometry_data != "":
            self.main_geometry = QByteArray.fromHex(bytes(tmp_main_geometry_data, "ascii"))

        self.main_state = tmp_session_data.get(self.main_state_key, False)

        tmp_modal_geometry_data = tmp_session_data.get(self.modal_geometry_key, "")
        if tmp_modal_geometry_data != "":
            self.modal_geometry = QByteArray.fromHex(bytes(tmp_modal_geometry_data, "ascii"))

        self.modal_state = tmp_session_data.get(self.modal_state_key, False)

    def save(self):
        tmp_session_data = dict()
        tmp_session_data[self.last_activity_key] = self.last_activity

        if self.main_geometry is not None:
            tmp_main_geometry_data = bytes(self.main_geometry.toHex()).decode("ascii")
            tmp_session_data[self.main_geometry_key] = tmp_main_geometry_data

        if self.main_state is not None:
            tmp_session_data[self.main_state_key] = self.main_state

        if self.modal_geometry is not None:
            tmp_modal_geometry_data = bytes(self.modal_geometry.toHex()).decode("ascii")
            tmp_session_data[self.modal_geometry_key] = tmp_modal_geometry_data

        if self.modal_state is not None:
            tmp_session_data[self.modal_state_key] = self.modal_state

        # Save to disk
        save_json(self.config_path, tmp_session_data)

    def get_gsheets_handler(self) -> [str | GSheetsHandler]:
        if self.gsheets_handler is not None:
            return self.gsheets_handler

        if self.runtime.data_manager.gsheet_credentials_path is None:
            return "No credentials file available."

        self.gsheets_handler = GSheetsHandler(self.runtime.data_manager.gsheet_credentials_path)
        return self.gsheets_handler


class DesktopRuntime(LitRPGToolsRuntime[DesktopSession]):
    """
    High Priority:
    TODO: Edit output target doesnt work
    TODO: Automatic resizing edit entry dialog causes scroll areas to mess up
    TODO: New sheet?
        - Should save current dialog.
    TODO: Text size +/-

    Medium Priority:
    TODO: ID / Character picking - Head vs current? Rework w/ below maybe?

    Medium Priority (Dynamic Data QOL):
    TODO: Target scope as a separate column in dynamic data?
    TODO: Target character as a separate column in dynamic data?
    TODO: Dynamic data builder?
    TODO: Separate type where it needs to be eval'd? Or seperate symbol tokens where it needs to be eval'd? Reuse existing from embedded text?
    TODO: Expression creator?
    TODO: Clipboard needs a lot of work to not feel so clunky

    Low Priority:
    TODO: Search shouldn't be tokenised??? Search improvements, Search scoring
    TODO: Catch likely candidates (e.g. '[string]') and assume we intended it a string literal?
    TODO: Create entry everywhere with context applied?
    TODO: Fill in options (i.e. for create entry) when there is only one choice
    TODO: OS X saving seems to put it in the wrong directory (uses relative to cwd?)
    TODO: Better notifications when things go wrong
    TODO: History log text inject category info etc etc
    TODO: Replace in search?
    TODO: Web
    TODO: Bullet Points and Bold?
    TODO: Switch to Deltas?
    TODO: Versionable Categories?
    TODO: NamedRanges ordering
    """

    def __init__(self):
        super().__init__(DesktopSession())
        self.application = QApplication(sys.argv)
        self.gui = None

        self.data_directory = None

    def start(self):
        self.session.load()  # No hinting
        self.gui = DesktopGUI(self.application, self)
        super().start()

    def run(self):
        if not self.started:
            print("Application has not been started")
            return

        self.gui.show()

        # Check for auto saves
        result = False
        if self.has_autosave():
            # Ask the user if we want to load the autosave
            result = QMessageBox.question(
                self.gui,
                "Autosave Detected",
                "Do you wish to load the autosave? This was likely created prior to a crash...",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No)

            # If they want to load, do so. Otherwise delete it.
            if result == QMessageBox.StandardButton.Yes:
                self.load_autosave()
            else:
                self.delete_autosave()

        # Handle resume
        if (not result or result == QMessageBox.StandardButton.No) and self.session.last_activity is not None:
            result = QMessageBox.question(
                self.gui,
                "Resume?",
                "Do you wish to resume where you left off?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No)

            if result == QMessageBox.StandardButton.Yes:
                self.load(self.session.last_activity)

        # This is a bit unnecessary, but it's clean
        self.gui.fill_content()

        # Main runtime join
        sys.exit(self.application.exec())

    def has_autosave(self) -> bool:
        return os.path.exists(self.session.autosave_path)

    def autosave(self):
        self.session.save()
        self.data_manager.save(self.session.autosave_path)

    def load_autosave(self):
        self.load(self.session.autosave_path)

    def delete_autosave(self):
        if os.path.isfile(self.session.autosave_path):
            os.remove(self.session.autosave_path)

    def save_state(self, force: bool = False):
        # If we are forcing a save to a new location or don't have an existing file pointer
        if force or self.session.last_activity is None:
            results = QFileDialog.getSaveFileName(self.gui, "Save File", "*.litrpg", filter="*.litrpg")
            if results[0] == "":
                return
            self.session.last_activity = results[0]

        # Save both our session info and our data
        self.session.save()
        self.data_manager.save(self.session.last_activity)

    def load_state(self):
        results = QFileDialog.getOpenFileName(self.gui, "Load File", filter="*.litrpg")
        if results[0] == "":
            return
        self.session.last_activity = results[0]
        self.session.save()

        # Load our data
        self.load(self.session.last_activity)

    def load(self, file_path: str):
        self.data_manager.load(file_path)
        self.gui.fill_content()

    def load_gsheets_credentials(self):
        results = QFileDialog.getOpenFileName(self.gui, 'Load GSheets Credentials File', filter="*.json")
        if results[0] == "" or not os.path.exists(results[0]):
            return
        self.data_manager.gsheet_credentials_path = results[0]

    def output_to_gsheets(self):
        if self.session.get_gsheets_handler() is None:
            QMessageBox.warning(self.gui, "Could Not Create GSheets Handler", "Could not create the gsheets handler. Please ensure your gsheets credentials are correct and properly loaded", QMessageBox.StandardButton.Ok, QMessageBox.StandardButton.Ok)
            return

        self.save_state()  # With autosaves, do we really need to save here?
        progress_bar = LitRPGToolsDesktopGUIProgressUpdater(self)
        self.data_manager.output_to_gsheets(progress_bar)
        self.save_state()

    def set_window_properties(self, geometry: QByteArray, fullscreen: bool):
        self.session.main_geometry = geometry
        self.session.main_state = fullscreen
        self.session.save()

    def set_modal_window_properties(self, geometry: QByteArray, fullscreen: bool):
        self.session.modal_geometry = geometry
        self.session.modal_state = fullscreen
        self.session.save()
