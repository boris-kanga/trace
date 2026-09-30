import traceback
from functools import wraps
import time
from datetime import datetime, timedelta

from flask import current_app, jsonify, Response, request
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request
from flask_jwt_extended import create_access_token, create_refresh_token, set_access_cookies, set_refresh_cookies
from jwt.exceptions import PyJWTError
from flask_jwt_extended.exceptions import JWTExtendedException

from src.domain.entities.user import User, Role, UserException
from init import InitData
from src.core.config import CONFIG
from src.tools.utils import get_func_args


__cache = {}


def auth_required(role=(), **kw):
    if not role:
        role = tuple(Role.__members__.values())
    def decorator(func):
        setattr(func, "__need_auth", True)
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                verify_jwt_in_request(**kw)
            except (JWTExtendedException, PyJWTError) as e:
                return jsonify({"msg": "Unauthorized"}), 401

            matricule = get_jwt_identity()
            user: User = None
            if matricule in __cache:
                exp, user = __cache[matricule]
                if exp < time.time():
                    user = None

            if user is None:
                db = await InitData.default_db(
                    **current_app.config["db_params"]
                )
                try:
                    service = await InitData.user_service(db)
                    user = await service.from_matricule(matricule)
                    __cache[matricule] = time.time() + int(CONFIG.get("EXPIRE_SECONDS_USER", 5*60)), user
                except UserException:
                    return jsonify({"msg": "Unauthorized"}), 401
            if user.role not in role:
                return jsonify({"msg": "Unauthorized"}), 401

            _kw = kwargs.copy()

            if "user" in get_func_args(func):
                _kw["user"] = user
            return await func(*args, **_kw)
        return wrapper
    return decorator


def remove_cache(matricule):
    if matricule in __cache:
        __cache.pop(matricule)


def attach_token(identity, response: Response, claims=None):
    token = create_access_token(
        identity=identity,
        expires_delta=timedelta(CONFIG.get("EXPIRE_SECONDS_ACCESS_TOKEN", 60*60)),
        additional_claims=claims
    )
    refresh_token = create_refresh_token(
        identity=identity,
        expires_delta=timedelta(CONFIG.get("EXPIRE_SECONDS_REFRESH_TOKEN", 3 *60 * 60)),
        additional_claims=claims
    )
    set_access_cookies(response, token)
    set_refresh_cookies(response, refresh_token)

    return response, token

