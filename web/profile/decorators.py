from functools import wraps
from typing import List

from flask import redirect, url_for
from flask_login import current_user


def role_required(role: [str | List]):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(*args, **kwargs):
            if current_user.is_authenticated:
                if current_user.role == role:  # Equality
                    return view_func(*args, **kwargs)
                elif current_user.role in role:  # List
                    return view_func(*args, **kwargs)

            # Fail
            return redirect(url_for("error.unauthorised"))
        return wrapper
    return decorator
