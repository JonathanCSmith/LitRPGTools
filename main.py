import sys
from abc import abstractmethod

"""
High Priority:
TODO: If no gsheets present, gsheets progress bar is made and not reported to the user
TODO: Edit output target doesnt work
TODO: Automatic resizing edit entry dialog causes scroll areas to mess up

Medium Priority:
TODO: Output View, order entries not in output by actual entry index (and display corresponding entry index in the synopsis)
TODO: Enter = run search
TODO: Autosave to remember default save path?
TODO: If an entry is not updatable then dont display the update buttons (note, force update should still be allowed!)

Low Priority:
TODO: Search shouldn't be tokenised??? 
TODO: Catch likely candidates (e.g. '[string]') and assume we intended it a string literal?
TODO: Create entry everywhere with context applied?
TODO: Fill in options (i.e. for create entry) when there is only one choice
TODO: OS X saving seems to put it in the wrong directory (uses relative to cwd?)
TODO: Expression creator!
TODO: Update function logic check + streamline?
TODO: Better notifications when things go wrong
TODO: History log text inject category info etc etc
TODO: Replace in search?
TODO: Mobile?
TODO: Web
TODO: Bullet Points and Bold?
TODO: Switch to Deltas?
TODO: Versionable Categories?
TODO: NamedRanges ordering
"""


class LitRPGToolsInstance:
    """
    TODO: Instance specific handling of the below:
    TODO: Save directory handling
    TODO: Autosave directory handling
    TODO: Config handling
    TODO: Secrets handling
    """

    def __init__(self):
        self.started = False

    @abstractmethod
    def start(self):
        self.started = True

    @abstractmethod
    def run(self):
        pass

    @abstractmethod
    def get_data_directory(self):
        pass

    @abstractmethod
    def set_data_directory(self, data_directory: str):
        pass

    @abstractmethod
    def get_autosave_directory(self):
        pass


if __name__ == '__main__':
    state = 0
    if len(sys.argv) > 1:
        if sys.argv[1].lower() == "web":
            state = 1

    # Desktop
    main = None
    if not state:
        from desktop.desktop_ui import LitRPGToolsDesktop
        main = LitRPGToolsDesktop()

    # Web
    else:
        from web.web_ui import LitRPGToolsWeb
        main = LitRPGToolsWeb()

    # Trigger variable initialization
    main.start()

    # Run the console interaction
    main.run()
