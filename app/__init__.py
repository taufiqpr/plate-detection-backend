import os
from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv

from .config import Config
from .db import init_db, get_scoped_session
from .models import Base, Kendaraan, ScanLog
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView


def create_app() -> Flask:
    load_dotenv()

    app = Flask(__name__)
    app.config.from_object(Config())

    CORS(app)

    engine, Session = init_db(
        user=app.config.get("DB_USER"),
        password=app.config.get("DB_PASSWORD"),
        host=app.config.get("DB_HOST"),
        port=app.config.get("DB_PORT"),
        name=app.config.get("DB_NAME"),
    )

    Base.metadata.create_all(bind=engine)

    app.extensions = getattr(app, "extensions", {})
    app.extensions["engine"] = engine
    app.extensions["Session"] = Session

    admin = Admin(app, name="Admin", template_mode="bootstrap4")
    admin.add_view(ModelView(Kendaraan, Session()))
    admin.add_view(ModelView(ScanLog, Session()))

    from .routes.detect import bp as detect_bp
    from .routes.scans import bp as scans_bp

    app.register_blueprint(detect_bp)
    app.register_blueprint(scans_bp)

    return app


