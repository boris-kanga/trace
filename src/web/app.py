from dataclasses import is_dataclass

from flask import Flask, render_template, Response, jsonify

from werkzeug.middleware.proxy_fix import ProxyFix

from flask_cors import CORS
from flask_jwt_extended import JWTManager

from init import InitData
from src.core.config import DB_CONFIG, WORK_DIR, CONFIG, S3_CONFIG
from src.core.logger import get_logger

from src.web.api.auth import view as api_view
from src.web.api.localization import view as localization_view
from src.web.api.immobilization import view as immobilization_view
from src.web.api.immobilization_family import view as family_view
from src.web.api.campaign import view as campaign_view
from src.web.api.inventory import view as inventory_view
from src.web.api.supplier import view as supplier_view

from flask.json.provider import DefaultJSONProvider

from src.web._swagger import add_swagger_views


logger = get_logger(__name__)


class CustomJSONProvider(DefaultJSONProvider):
    def default(self, obj):
        if is_dataclass(obj) and hasattr(obj, "to_dict"):
            return obj.to_dict()
        return super().default(obj)


def create_app(config=None) -> Flask:
    app = Flask(
        __name__,
        template_folder=str(WORK_DIR + "src" + "web" + "templates")
    )
    app.wsgi_app = ProxyFix(app.wsgi_app, x_host=1, x_proto=1, x_port=1)

    app.json_provider_class = CustomJSONProvider

    app.json = CustomJSONProvider(app)

    JWTManager(app)

    CORS(app, )
    app.config.update({
        "db_params": DB_CONFIG,
        "storage_params": S3_CONFIG,
        **CONFIG
    })

    swagger_endpoint = CONFIG.get("swagger_endpoint", "/api/swagger/")
    if config is not None:
        app.config.update(config)

    @app.route("/healthcheck", strict_slashes=False)
    def healthcheck():
        return "OK", 200

    @app.errorhandler(InitData.default_db_class().get_root_db_exception())
    def handle_db_error(error):
        logger.exception(error)
        return jsonify({
            "message": str(InitData.default_db_class().parse_error(error))
        }), 409

    @app.get("/api", strict_slashes=False)
    @app.get("/")
    def _():
        return render_template("index.html", swagger_endpoint=swagger_endpoint)

    app.register_blueprint(
        api_view, url_prefix="/api"
    )
    app.register_blueprint(
        localization_view, url_prefix="/api"
    )
    app.register_blueprint(
        immobilization_view, url_prefix="/api"
    )
    app.register_blueprint(
        family_view, url_prefix="/api"
    )

    app.register_blueprint(
        campaign_view, url_prefix="/api"
    )

    app.register_blueprint(
        inventory_view, url_prefix="/api"
    )

    app.register_blueprint(
        supplier_view, url_prefix="/api"
    )

    @app.after_request
    def before_request(response: Response):
        return response

    if not app.config["TESTING"]:
        add_swagger_views(app, swagger_endpoint)


    return app