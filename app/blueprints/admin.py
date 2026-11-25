"""Generic CRUD screens for every ORM model (rubric: CRUD across the whole schema)."""
import json

from flask import Blueprint, abort, flash, g, redirect, render_template, request, url_for
from flask_wtf import FlaskForm
from sqlalchemy import JSON, Boolean, Date, DateTime, Float, Integer, String, Text, func, inspect
from sqlalchemy.exc import IntegrityError
from wtforms import (BooleanField, DateField, FloatField, IntegerField, PasswordField, SelectField,
                     StringField, SubmitField, TextAreaField, ValidationError)
from wtforms.validators import InputRequired, Length, Optional

from ..auth_utils import role_required
from ..extensions import db
from ..models import ALL_MODELS, AuditLog, User

bp = Blueprint("admin", __name__, url_prefix="/admin")
MODELS = {m.__tablename__: m for m in ALL_MODELS}
SKIP = {"created_at", "updated_at", "computed_at", "assigned_at", "password_hash"}
LABEL_ATTRS = ("name", "title", "username", "word", "keyword", "short_code", "version_label", "code", "label")


def pk_of(row) -> str:
    return "~".join(str(v) for v in inspect(row).identity)


def row_label(row) -> str:
    for attr in LABEL_ATTRS:
        if getattr(row, attr, None):
            return f"#{pk_of(row)} {getattr(row, attr)}"
    return f"#{pk_of(row)}"


def _model(name):
    return MODELS.get(name) or abort(404)


def _get(model, pk):
    parts, cols = pk.split("~"), inspect(model).primary_key
    if len(parts) != len(cols) or not all(p.isdigit() for p in parts):
        abort(404)
    key = tuple(int(p) for p in parts)
    return db.session.get(model, key if len(key) > 1 else key[0]) or abort(404)


def _int_or_none(value):
    return None if value in (None, "") else int(value)


def _json_check(form, field):
    if field.data:
        try:
            json.loads(field.data)
        except ValueError:
            raise ValidationError("Enter valid JSON.")


def editable_columns(model, creating):
    cols = []
    for col in inspect(model).columns:
        if col.key in SKIP or isinstance(col.type, DateTime):
            continue
        if col.primary_key and not col.foreign_keys:
            continue                      # auto-increment id
        if col.primary_key and not creating:
            continue                      # composite keys can only be set on create
        cols.append(col)
    return cols


def _field(col):
    required = not col.nullable and col.default is None
    checks = [InputRequired() if required else Optional()]
    label = col.key.replace("_", " ").title()
    if col.foreign_keys:
        target = MODELS[next(iter(col.foreign_keys)).column.table.name]
        choices = [(str(r.id) if hasattr(r, "id") else pk_of(r), row_label(r)) for r in db.session.query(target).limit(500)]
        if not required:
            choices.insert(0, ("", "- none -"))
        return SelectField(label, choices=choices, coerce=_int_or_none, validators=[Optional()] if not required else [])
    t = col.type
    if isinstance(t, Boolean):
        return BooleanField(label)
    if isinstance(t, Integer):
        return IntegerField(label, validators=checks)
    if isinstance(t, Float):
        return FloatField(label, validators=checks)
    if isinstance(t, Date):
        return DateField(label, validators=checks)
    if isinstance(t, JSON):
        return TextAreaField(label, validators=checks + [_json_check])
    if isinstance(t, Text):
        return TextAreaField(label, validators=checks)
    if isinstance(t, String):
        return StringField(label, validators=checks + ([Length(max=t.length)] if t.length else []))
    return StringField(label, validators=checks)


def build_form(model, creating):
    fields = {col.key: _field(col) for col in editable_columns(model, creating)}
    if model is User:
        fields["password"] = PasswordField("Password", validators=[InputRequired() if creating else Optional(), Length(min=8)])
    fields["submit"] = SubmitField("Save")
    return type(f"{model.__name__}Form", (FlaskForm,), fields)


def apply(form, model, instance, creating):
    for col in editable_columns(model, creating):
        value = form[col.key].data
        if isinstance(col.type, JSON):
            value = json.loads(value) if value else None
        elif isinstance(value, str):
            value = value.strip() or None
        if value is None and creating and col.default is not None:
            continue                      # let the column default apply
        setattr(instance, col.key, value)
    if model is User and form.password.data:
        instance.set_password(form.password.data)


def _audit(action, model, row):
    ident = inspect(row).identity
    db.session.add(AuditLog(user_id=g.user.id, action=action, entity_type=model.__tablename__,
                            entity_id=ident[0] if ident and len(ident) == 1 else None))


@bp.route("/")
@role_required("admin")
def index():
    counts = {name: db.session.scalar(db.select(func.count()).select_from(m)) for name, m in sorted(MODELS.items())}
    return render_template("admin/index.html", counts=counts)


@bp.route("/<model_name>/")
@role_required("admin")
def list_rows(model_name):
    model = _model(model_name)
    page = request.args.get("page", 1, type=int)
    pagination = db.paginate(db.select(model).order_by(*inspect(model).primary_key), page=page, per_page=20, error_out=False)
    columns = [c.key for c in inspect(model).columns if c.key not in SKIP][:7]
    return render_template("admin/list.html", name=model_name, pagination=pagination, columns=columns, pk_of=pk_of)


@bp.route("/<model_name>/new", methods=["GET", "POST"])
@role_required("admin")
def create_row(model_name):
    model = _model(model_name)
    form = build_form(model, creating=True)()
    if form.validate_on_submit():
        row = model()
        apply(form, model, row, creating=True)
        db.session.add(row)
        try:
            db.session.flush()
            _audit("create", model, row)
            db.session.commit()
        except IntegrityError as exc:
            db.session.rollback()
            flash(f"Could not save: {exc.orig}", "danger")
        else:
            flash("Record created.", "success")
            return redirect(url_for("admin.list_rows", model_name=model_name))
    return render_template("admin/form.html", form=form, name=model_name, title="New")


@bp.route("/<model_name>/<pk>/edit", methods=["GET", "POST"])
@role_required("admin")
def edit_row(model_name, pk):
    model = _model(model_name)
    row = _get(model, pk)
    form = build_form(model, creating=False)(obj=row)
    if request.method == "GET":
        for col in editable_columns(model, False):
            if isinstance(col.type, JSON):
                form[col.key].data = json.dumps(getattr(row, col.key)) if getattr(row, col.key) is not None else ""
    if form.validate_on_submit():
        apply(form, model, row, creating=False)
        try:
            _audit("update", model, row)
            db.session.commit()
        except IntegrityError as exc:
            db.session.rollback()
            flash(f"Could not save: {exc.orig}", "danger")
        else:
            flash("Record updated.", "success")
            return redirect(url_for("admin.list_rows", model_name=model_name))
    return render_template("admin/form.html", form=form, name=model_name, title=f"Edit {row_label(row)}")


@bp.route("/<model_name>/<pk>/delete", methods=["POST"])
@role_required("admin")
def delete_row(model_name, pk):
    model = _model(model_name)
    row = _get(model, pk)
    try:
        _audit("delete", model, row)
        db.session.delete(row)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        flash("Cannot delete: other records depend on it.", "danger")
    else:
        flash("Record deleted.", "info")
    return redirect(url_for("admin.list_rows", model_name=model_name))
