"""System tables: 2 tables."""
from ..extensions import db
from .base import utcnow


class AuditLog(db.Model):
    __tablename__ = "audit_logs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"))
    action = db.Column(db.String(40), nullable=False)  # create / update / delete / review / login
    entity_type = db.Column(db.String(60), nullable=False)
    entity_id = db.Column(db.Integer)
    details = db.Column(db.JSON)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    user = db.relationship("User", backref="audit_logs")


class AppSetting(db.Model):
    __tablename__ = "app_settings"

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(80), unique=True, nullable=False)
    value = db.Column(db.String(255))
    description = db.Column(db.String(255))
    updated_by = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"))
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    updated_by_user = db.relationship("User", backref="settings_changed")
