"""Identity and access: 5 tables."""
from werkzeug.security import check_password_hash, generate_password_hash

from ..extensions import db
from .base import TimestampMixin, utcnow


class School(TimestampMixin, db.Model):
    __tablename__ = "schools"
    __table_args__ = (db.UniqueConstraint("name", "city", name="uq_school_name_city"),)

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    city = db.Column(db.String(80))
    country = db.Column(db.String(80), default="Pakistan")

    users = db.relationship("User", backref="school")


class Role(TimestampMixin, db.Model):
    __tablename__ = "roles"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(30), unique=True, nullable=False)  # student, contributor, admin
    description = db.Column(db.String(255))


class UserRole(db.Model):
    """Association table between users and roles (many-to-many)."""

    __tablename__ = "user_roles"

    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    role_id = db.Column(db.Integer, db.ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True)
    assigned_at = db.Column(db.DateTime, default=utcnow, nullable=False)


class User(TimestampMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(40), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    last_login_at = db.Column(db.DateTime)
    school_id = db.Column(db.Integer, db.ForeignKey("schools.id", ondelete="SET NULL"))

    roles = db.relationship("Role", secondary="user_roles", backref="users")
    profile = db.relationship(
        "UserProfile", uselist=False, backref="user", cascade="all, delete-orphan"
    )

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def has_role(self, name: str) -> bool:
        return any(role.name == name for role in self.roles)


class UserProfile(TimestampMixin, db.Model):
    __tablename__ = "user_profiles"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    full_name = db.Column(db.String(120))
    grade_level = db.Column(db.String(30))
    target_exam_year = db.Column(db.Integer)
    bio = db.Column(db.Text)
