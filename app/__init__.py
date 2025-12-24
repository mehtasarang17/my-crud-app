from flask import Flask, send_from_directory
import os
import yaml
from flasgger import Swagger
from flask_scss import Scss

from .extensions import db
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

    # init extensions
    db.init_app(app)
    Scss(app, static_dir="static", asset_dir="static")

    # ---- Load YAML Swagger spec (root/api-spec.yml) ----
    yaml_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "api-spec.yml"))
    with open(yaml_path, "r") as f:
        swagger_template = yaml.safe_load(f)

    swagger_config = {
    "headers": [],
    "specs": [
        {
            "endpoint": "apispec_1",
            "route": "/apispec_1.json",
            "rule_filter": lambda rule: True,
            "model_filter": lambda tag: True,
        }
    ],
    "static_url_path": "/flasgger_static",
    "swagger_ui": True,
    "specs_route": "/apidocs/",
    }
    Swagger(app, config=swagger_config, template=swagger_template)

    # register blueprints
    app.register_blueprint(ui_bp)
    app.register_blueprint(csv_bp)
    app.register_blueprint(api_bp)

    # create tables
    with app.app_context():
        db.create_all()

    @app.route("/favicon.ico")
    def favicon():
        return send_from_directory(app.static_folder, "favicon.ico")

    return app
