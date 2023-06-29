from abc import abstractmethod


class LitRPGToolsProgressUpdater:
    @abstractmethod
    def set_minimum(self, value: int):
        pass

    @abstractmethod
    def set_maximum(self, value: int):
        pass

    @abstractmethod
    def set_current_work_done(self, value: int):
        pass

    @abstractmethod
    def finish(self):
        pass
