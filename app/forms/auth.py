import re

from flask_wtf import FlaskForm
from sqlalchemy import func
from wtforms import BooleanField, PasswordField, StringField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, Length, Regexp, ValidationError

from ..models import User


class RegisterForm(FlaskForm):
    username = StringField(
        "Username",
        validators=[DataRequired(), Length(3, 40), Regexp(r"^\w+$", message="Letters, numbers and underscores only.")],
    )
    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=120)])
    password = PasswordField("Password", validators=[DataRequired(), Length(8, 128)])
    confirm = PasswordField(
        "Confirm password", validators=[DataRequired(), EqualTo("password", message="Passwords must match.")]
    )
    submit = SubmitField("Create account")

    # Server-side rules beyond HTML5 attributes (rubric: Forms & Validation).
    def validate_username(self, field):
        if User.query.filter(func.lower(User.username) == field.data.lower()).first():
            raise ValidationError("That username is already taken.")

    def validate_email(self, field):
        if User.query.filter(func.lower(User.email) == field.data.lower()).first():
            raise ValidationError("An account with that email already exists.")

    def validate_password(self, field):
        if not (re.search(r"[A-Za-z]", field.data) and re.search(r"\d", field.data)):
            raise ValidationError("Use at least one letter and one number.")


class LoginForm(FlaskForm):
    identifier = StringField("Username or email", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])
    remember = BooleanField("Keep me logged in")
    submit = SubmitField("Log in")
