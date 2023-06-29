import time
import uuid


class SessionData:
    def __init__(self):
        self.unique_id = str(uuid.uuid4())
        self.last_accessed: float = time.time()
        self.session_data = "test"
