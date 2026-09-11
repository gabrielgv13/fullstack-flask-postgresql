"""WSGI entry point — exposes `app` for `flask run`."""
from . import create_app

app = create_app()

