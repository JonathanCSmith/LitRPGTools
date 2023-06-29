import uuid

from flask_login import UserMixin


class UserData(UserMixin):
    def __init__(self, user_name: str, hashed_password: str, user_role: str, patreon_id: str = None):
        self.id = str(uuid.uuid4())
        self.user_name = user_name
        self.hashed_password = hashed_password
        self.user_role = user_role
        self.patreon_id = patreon_id
