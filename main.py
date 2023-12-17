from abc import abstractmethod, ABC
from typing import TypeVar, Generic, TYPE_CHECKING

from data.data_manager import DataManager
from gsheets import GSheetsHandler

"""
TODO: Move utils.py into relevant
"""


class LitRPGToolsRuntimeSession(ABC):
    app_name = "LitRPGTools"
    app_author = "JonathanCSmith"
    last_activity_key = "last_activity"
    main_geometry_key = "main_geometry_key"
    main_state_key = "main_state_key"
    modal_geometry_key = "modal_geometry_key"
    modal_state_key = "modal_state_key"

    def __init__(self):
        self.runtime: LitRPGToolsRuntime | None = None
        self.session_directory: str | None = None
        self.config_path: str | None = None
        self.autosave_path: str | None = None
        self.gsheets_handler: GSheetsHandler | None = None

        # General configs
        self.last_activity: str | None = None

    @abstractmethod
    def load(self):
        pass

    @abstractmethod
    def save(self):
        pass

    @abstractmethod
    def get_gsheets_handler(self) -> [str | GSheetsHandler]:
        pass


T = TypeVar("T", bound=LitRPGToolsRuntimeSession)


class LitRPGToolsRuntime(ABC, Generic[T]):
    # """
    # TODO: Secrets handling
    # """

    def __init__(self, session: Generic[T]):
        self.session: Generic[T] = session
        self.data_manager: DataManager = DataManager(self)
        self.session.runtime = self
        self.started = False

    @abstractmethod
    def start(self):
        self.started = True

    @abstractmethod
    def run(self):
        pass

    @abstractmethod
    def has_autosave(self) -> bool:
        pass

    @abstractmethod
    def autosave(self):
        pass

    @abstractmethod
    def load_autosave(self):
        pass

    @abstractmethod
    def delete_autosave(self):
        pass

    @abstractmethod
    def save_state(self, force: bool = False):
        pass

    @abstractmethod
    def load_state(self):
        pass

    @abstractmethod
    def load_gsheets_credentials(self):
        pass

    @abstractmethod
    def output_to_gsheets(self):
        pass


if __name__ == '__main__':
    from desktop.runtime import DesktopRuntime

    main = DesktopRuntime()
    main.start()
    main.run()
