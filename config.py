import os
import tempfile
from datetime import timedelta

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "change-me-in-production")
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "sqlite:///past_paper.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # Cookie hardening (the Secure flag should be switched on behind HTTPS).
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    PERMANENT_SESSION_LIFETIME = timedelta(days=14)  # used by "remember me"
    UPLOAD_FOLDER = os.environ.get("UPLOAD_FOLDER", os.path.join(BASE_DIR, "instance", "uploads"))
    MAX_CONTENT_LENGTH = 20 * 1024 * 1024  # reject uploads over 20 MB


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False
    UPLOAD_FOLDER = tempfile.mkdtemp(prefix="ppa_uploads_")


CONFIGS = {"default": Config, "testing": TestingConfig}
