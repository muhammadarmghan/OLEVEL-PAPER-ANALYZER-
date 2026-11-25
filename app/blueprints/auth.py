from flask import Blueprint, flash, g, redirect, render_template, request, session, url_for
from sqlalchemy import func

from ..auth_utils import is_safe_next
from ..extensions import db
from ..forms.auth import LoginForm, RegisterForm
from ..models import Role, User
from ..models.base import utcnow

bp = Blueprint("auth", __name__)


@bp.route("/register", methods=["GET", "POST"])
def register():
    if g.user:
        return redirect(url_for("main.index"))
    form = RegisterForm()
    if form.validate_on_submit():
        user = User(username=form.username.data.strip(), email=form.email.data.strip().lower())
        user.set_password(form.password.data)
        student = Role.query.filter_by(name="student").first() or Role(name="student")
        user.roles.append(student)
        db.session.add(user)
        db.session.commit()
        flash("Account created. You can log in now.", "success")
        return redirect(url_for("auth.login"))  # Post-Redirect-Get
    return render_template("auth/register.html", form=form)


@bp.route("/login", methods=["GET", "POST"])
def login():
    if g.user:
        return redirect(url_for("main.index"))
    form = LoginForm()
    if form.validate_on_submit():
        ident = form.identifier.data.strip().lower()
        user = User.query.filter(
            (func.lower(User.username) == ident) | (func.lower(User.email) == ident)
        ).first()
        if user and user.is_active and user.check_password(form.password.data):
            session.clear()  # prevents session fixation
            session["user_id"] = user.id
            session.permanent = form.remember.data  # remember-me cookie lifetime
            user.last_login_at = utcnow()
            db.session.commit()
            flash(f"Welcome back, {user.username}!", "success")
            next_url = request.args.get("next")
            return redirect(next_url if is_safe_next(next_url) else url_for("main.index"))
        flash("Invalid username or password.", "danger")
    return render_template("auth/login.html", form=form)


@bp.route("/logout", methods=["POST"])
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("main.index"))
