import click
from flask import Flask, render_template

from config import CONFIGS

from .extensions import csrf, db, migrate


def create_app(config_name: str = "default") -> Flask:
    """Application factory: builds and wires the Flask app."""
    app = Flask(__name__)
    app.config.from_object(CONFIGS[config_name])

    db.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)

    from . import models  # noqa: F401  (registers every model)
    from .auth_utils import load_current_user
    from .blueprints.admin import bp as admin_bp
    from .blueprints.analytics import bp as analytics_bp
    from .blueprints.auth import bp as auth_bp
    from .blueprints.main import bp as main_bp
    from .blueprints.papers import bp as papers_bp
    from .blueprints.review import bp as review_bp
    from .blueprints.study import bp as study_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix="/auth")
    for blueprint in (admin_bp, analytics_bp, papers_bp, review_bp, study_bp):
        app.register_blueprint(blueprint)
    app.before_request(load_current_user)

    for code in (403, 404):
        app.register_error_handler(code, lambda e, c=code: (render_template(f"errors/{c}.html"), c))

    @app.cli.command("seed")
    def seed_command():
        """Load reference data and demo accounts (safe to run twice)."""
        from .seed import seed_all

        seed_all()
        click.echo("Seed complete.")

    return app
