from flask import Flask, send_from_directory
import os

from flask_scss import Scss
from .extensions import db, swagger
from .routes.ui import ui_bp
from .routes.api import api_bp
from .routes.csv_routes import csv_bp

def create_app():
    app = Flask(
        __name__,
        template_folder="../templates",
        static_folder="../static"
    )

    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database.db"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SWAGGER"] = {"title": "Task API", "uiversion": 3}

    # init extensions
    db.init_app(app)
    swagger.init_app(app)
    Scss(app, static_dir='static', asset_dir='static')

    # register blueprints
    app.register_blueprint(ui_bp)
    app.register_blueprint(csv_bp)
    app.register_blueprint(api_bp)

    with app.app_context():
        db.create_all()

    @app.route("/favicon.ico")
    def favicon():
        return send_from_directory(app.static_folder, "favicon.ico")

    return app
