from typing import TYPE_CHECKING

from flask import Blueprint, redirect, url_for, request, render_template, session
from flask_login import current_user, login_user, login_required, logout_user
from requests_oauthlib import OAuth2Session
from werkzeug.security import generate_password_hash, check_password_hash

from web.profile.data import UserData
from web.profile.forms import RegistrationForm, LoginForm

if TYPE_CHECKING:
    from web.web_ui import LitRPGToolsWeb

# Fake user
users = {
    "test": UserData("test", generate_password_hash("test"), "admin")
}


class ProfileBlueprint:
    profile_blueprint = Blueprint("profile", __name__, template_folder="templates")

    def __init__(self, app: 'LitRPGToolsWeb'):
        self.app = app
        self.app.application.register_blueprint(self.profile_blueprint)
        self.app.login_manager.login_view = "profile.login"
        self.app.login_manager.user_loader(self.__load_user)

    @profile_blueprint.route("/")
    def profile(self):
        if current_user is None or not current_user.is_authenticated:
            return redirect(url_for("profile.login"))

        return render_template("profile.html", user=current_user, session_data=self.app.get_session_data())

    @profile_blueprint.route("/register")
    def register(self):
        form = RegistrationForm()

        if form.validate_on_submit():
            username = form.username.data
            password = form.password.data

            # Check for username collision
            if username in users:
                return render_template("register.html", form=form, error="Username is already taken.")

            # TODO: Validate password quality

            # Create and store users
            user = UserData(username, generate_password_hash(password), "user")
            users[user.id] = user  # TODO: Switch to DB

            return self.__log_in_user(user)

        return render_template("register.html", form=form)

    @profile_blueprint.route("/login")
    def login(self):
        error = None
        form = LoginForm()

        # Check the form submission data
        if form.validate_on_submit():
            username = form.username.data
            password = form.password.data

            # Find our user
            for user in users.values():
                if user.user_name == username:

                    # Check their password and if a fail, bail because usernames should be unique
                    if check_password_hash(user.hashed_password, password):
                        self.__log_in_user(user)
                    else:
                        error = "Invalid Password"
                        break

        return render_template("login.html", form=form, error=error)

    @profile_blueprint.route("/logout")
    def logout(self):
        logout_user()
        return redirect(url_for("profile.login"))

    @profile_blueprint.route("/link_patreon")
    @login_required
    def link_patreon(self):
        oauth = OAuth2Session(self.app.patreon_client_id, redirect_uri=url_for("profile.patreon_callback"))
        auth_url, state = oauth.authorization_url("https://www.patreon.com/oauth2/authorize")
        session["oauth_state"] = state
        return redirect(auth_url)

    @profile_blueprint.route("/unlink_patreon")
    @login_required
    def unlink_patreon(self):
        current_user.patreon_id = None
        return redirect(url_for("profile"))

    @profile_blueprint.route("/patreon_callback")
    @login_required
    def patreon_callback(self):
        patreon = OAuth2Session(self.app.patreon_client_id, redirect_uri=url_for("profile.patreon_callback"), state=session['oauth_state'])
        token_url = 'https://www.patreon.com/api/oauth2/token'
        token = patreon.fetch_token(token_url, client_secret=self.app.patreon_client_secret, authorization_response=request.url)
        current_user.patreon_id = token

        # Set up the current patreon pledge tier
        self.check_patreon_tier()

        return redirect(url_for("profile"))

    def check_patreon_tier(self):
        patreon = OAuth2Session(self.app.patreon_client_id, token=current_user.patreon_id)
        response = patreon.get("https://www.patreon.com/api/oauth2/v2/identity")
        if response.status_code != 200:
            return redirect("error.patreon_issue")

        data = response.json()
        pledge_status = data["data"]["attributes"]["pledge_status"]
        pledge_amount = data["data"]["attributes"]["currently_entitled_amount_cents"]
        # TODO: Fill out their current permission level

    def __load_user(self, unique_id: str):
        return users[unique_id]  # TODO: Switch to id

    def __log_in_user(self, user: UserData):
        login_user(user)

        # Assign role based on patreon tier
        if current_user.patreon_id is not None:
            return self.check_patreon_tier()

        # Create our basic session data
        self.app.create_session()

        return redirect(url_for("index"))

