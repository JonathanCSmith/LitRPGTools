import time

from threading import Thread
from typing import List, Dict

from flask import Flask, session, render_template
from flask_classful import FlaskView
from flask_login import LoginManager, current_user

from main import LitRPGToolsInstance
from web.data import SessionData
from web.profile.profile import ProfileBlueprint


class BaseView(FlaskView):
    template_folder = "templates"

    def index(self):
        if current_user.is_authenticated:
            return render_template("index.html", user=current_user)

        return render_template("index.html")


class LitRPGToolsWeb(LitRPGToolsInstance):
    def __init__(self):
        super().__init__()
        self.application = self.__create_flask_application()
        self.application.secret_key = self.secret_key = "test"
        self.patreon_client_id = None
        self.patreon_client_secret = None
        self.login_manager = LoginManager()
        self.sessions: Dict[str, SessionData] = dict()
        self.session_daemon = Thread(target=self.__repeating_cleanup_session_data)

    def start(self):
        self.login_manager.init_app(self.application)

        # Register our views
        BaseView.register(self.application, route_base="/")
        self.application.template_folder = BaseView.template_folder

        ProfileBlueprint(self)

        # Start our background scheduler
        self.session_daemon.start()

    def run(self):
        self.application.run(host="localhost", port=5050, debug=True)

    def get_data_directory(self):
        pass

    def set_data_directory(self, data_directory: str):
        pass

    def get_autosave_directory(self):
        pass

    def before_request(self):
        if current_user.is_authenticated:
            session_id = session["session_id"]
            self.mark_session_as_active(session_id)
        return

    def get_session_data(self):
        if "session_id" not in session:
            self.create_session()

        return self.sessions[session["session_id"]]

    def create_session(self):
        if current_user.is_authenticated:
            session_data = SessionData()
            self.sessions[session_data.unique_id] = session_data
            session["session_id"] = session_data.unique_id

    def mark_session_as_active(self, key: str):
        self.sessions[key].last_accessed = time.time()

    def cleanup_session_data(self, key: str):
        # TODO: Proper session clean up

        del self.sessions[key]

    def __create_flask_application(self):
        application = Flask(__name__)

        @application.before_request
        def before_request():
            return self.before_request()

        return application

    def __repeating_cleanup_session_data(self):
        while True:
            for key, value in self.sessions.items():
                if time.time() - value.last_accessed > 600:
                    self.cleanup_session_data(key)

            time.sleep(5)
