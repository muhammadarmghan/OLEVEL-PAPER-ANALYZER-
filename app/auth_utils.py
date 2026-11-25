"""Session helpers: current user loading and access-control decorators."""
from functools import wraps

from flask import abort, flash, g, redirect, request, session, url_for

from .extensions import db
from .models import User


def load_current_user():
    """Runs before every request: puts the logged-in user (or None) on `g`."""
    user_id = session.get("user_id")
    g.user = db.session.get(User, user_id) if user_id else None
    if g.user is not None and not g.user.is_active:
        session.clear()
        g.user = None


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if g.user is None:
            flash("Please log in to continue.", "warning")
            return redirect(url_for("auth.login", next=request.full_path.rstrip("?")))
        return view(*args, **kwargs)

    return wrapped


def role_required(*roles):
    """Allow only users holding at least one of the given roles (else 403)."""

    def decorator(view):
        @wraps(view)
        @login_required
        def wrapped(*args, **kwargs):
            if not any(g.user.has_role(r) for r in roles):
                abort(403)
            return view(*args, **kwargs)

        return wrapped

    return decorator


def is_safe_next(url: str | None) -> bool:
    """Only follow relative redirects, never to another site."""
    return bool(url) and url.startswith("/") and not url.startswith("//")
