import json
import os
from typing import TYPE_CHECKING

from gsheets import GSheetsHandler
from data_manager import LitRPGToolsEngine

if TYPE_CHECKING:
    from main import LitRPGToolsInstance
    from progress_bar import LitRPGToolsProgressUpdater


class LitRPGToolsSession:
    def __init__(self, instance: 'LitRPGToolsInstance'):
        self.instance = instance
        self.data_manager: LitRPGToolsEngine = LitRPGToolsEngine(self)
        self.session_name = None
        self.__gsheets_handler = None

    def has_save_path(self):
        return self.session_name is not None

    def set_save_information(self, file: str):
        self.session_name = file

    def save_state(self) -> [str | None]:
        if self.session_name is None:
            return "No save target."

        # Path handling
        path = os.path.join(self.instance.get_data_directory(), self.session_name)
        self.__save(path)

    def load_state(self):
        if self.session_name is None:
            return "No load target."

        # Path handling
        path = os.path.join(self.instance.get_data_directory(), self.session_name)
        self.__load(path)

    def has_autosave(self) -> bool:
        """
        Note this implementation of autosave is not multi-user safe
        """
        if self.instance.get_autosave_directory() is None:
            return False

        return os.path.isfile(os.path.join(self.instance.get_autosave_directory(), "autosave.litrpg"))

    def autosave(self):
        """
        Note this implementation of autosave is not multi-user safe
        """
        path = os.path.join(self.instance.get_autosave_directory(), "autosave.litrpg")
        self.__save(path)

    def load_autosave(self):
        """
        Note this implementation of autosave is not multi-user safe
        """
        path = os.path.join(self.instance.get_autosave_directory(), "autosave.litrpg")
        self.__load(path)

    def delete_autosave(self):
        """
        Note this implementation of autosave is not multi-user safe
        """
        path = os.path.join(self.instance.get_autosave_directory(), "autosave.litrpg")
        if os.path.isfile(path):
            os.remove(path)

    def get_gsheets_handler(self) -> [str | GSheetsHandler]:
        if self.__gsheets_handler is not None:
            return self.__gsheets_handler

        if self.data_manager.gsheet_credentials_path is None:
            return "No credentials file available."

        self.__gsheets_handler = GSheetsHandler(self.data_manager.gsheet_credentials_path)
        return self.__gsheets_handler

    def output_to_gsheets(self, progress_bar: 'LitRPGToolsProgressUpdater') -> [str | None]:
        self.save_state()  # With autosaves, do we really need to save here?
        self.data_manager.output_to_gsheets(progress_bar, self)
        self.save_state()

    def __save(self, path: str):
        # Get the data
        data_holder = self.data_manager.get_data_object()
        jsons = json.dumps(data_holder, default=lambda o: o.__dict__, indent=4)

        # Serialize
        with open(path, 'w') as output_file:
            output_file.write(jsons)

    def __load(self, path: str):
        with open(path, "r") as source_file:
            json_data = json.load(source_file)
            self.data_manager.set_data_object(json_data)
