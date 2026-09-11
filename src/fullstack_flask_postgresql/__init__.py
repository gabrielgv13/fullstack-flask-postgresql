"""Application factory + entry point for fullstack_flask_postgresql."""
import os
from flask import Flask, g, session

from . import db


def create_app(test_config=None):
    app = Flask(
        __name__,
        # templates live at the project root, not inside the package
        template_folder=os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", "templates")
        ),
    )
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-change-me")
    app.config["DATABASE_URL"] = os.environ.get(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/supermercado",
    )

    if test_config is not None:
        app.config.update(test_config)

    db.init_app(app)

    from . import auth, views
    app.register_blueprint(auth.bp)
    app.register_blueprint(views.bp)

    @app.before_request
    def _load_logged_in_user():
        user_id = session.get("user_id")
        if user_id is None:
            g.user = None
        else:
            g.user = (
                db.get_db()
                .execute("SELECT * FROM users WHERE id = %s", (user_id,))
                .fetchone()
            )

    return app


def main():
    create_app().run(debug=True)
