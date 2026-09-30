import traceback

from flask import Blueprint, jsonify

from flask_jwt_extended import unset_jwt_cookies

from src.core.logger import get_logger
from src.web.schema import LoginSchema, Login200, RegisterUser, PatchUser
from src.domain.entities.user import User, UserException, Role

from src.web.decorators import parse_to_schema, status_code, auth_required, inject_db

from init import InitData
from src.web.decorators.auth import attach_token, remove_cache

logger = get_logger(__name__)


view = Blueprint('auth', __name__)


@view.post("/login", strict_slashes=False)
@inject_db
@parse_to_schema(LoginSchema)
@status_code(200, description="Login successful", schema=Login200)
@status_code(401, description="Login failed")
async def login(data: LoginSchema, db):
    try:
        user_service = await InitData.user_service(db)
        try:
            user = await user_service.from_matricule(data.username)
            if user == data.password:
                response = jsonify({"message": "Login successful", "user": user.to_dict(False)})
                response, token = attach_token(user.matricule, response)
                resp_json = response.json
                resp_json["token"] = token

                response.set_data(jsonify(resp_json).get_data())
                await user_service.notify_login(user)
                return response
        except UserException:
            pass
        return jsonify({"message": "Login failed", "user": data.username}), 401
    except Exception as err:
        logger.error(err)
        return jsonify({"message": "une erreur s'est produite"}), 500


@view.get("/logout", strict_slashes=False)
@status_code(200, description="Logout successful", schema={"message": "Logout successful"})
@auth_required()
async def logout(user: User):
    remove_cache(user.matricule)
    response = jsonify({"message": "Logout successful"})
    unset_jwt_cookies(response)
    return response


@view.post("/user", strict_slashes=False)
@inject_db
@parse_to_schema(RegisterUser)
@auth_required(role=(Role.BACKOFFICE,))
async def register(data: RegisterUser, db):
    service = await InitData.user_service(db)

    user_dict = data.model_dump()
    try:
        assert await service.create_user(user_dict)
    except (Exception, AssertionError):
        traceback.print_exc()
        return jsonify({"message": "Utilisateur existant"}), 400
    return jsonify({"message": "Login successful"}), 201


@view.delete("/user/<string:matricule>", strict_slashes=False)
@inject_db
@auth_required(role=(Role.BACKOFFICE,))
async def delete(matricule, db):
    service = await InitData.user_service(db)

    try:
        assert await service.user_repo.delete(matricule)
    except (Exception, AssertionError):
        traceback.print_exc()
        return jsonify({"message": "Utilisateur existant"}), 400
    return jsonify({"message": "Suppression OK"}), 200


@view.get("/user", strict_slashes=False)
@inject_db
@auth_required(role=(Role.BACKOFFICE,))
@status_code(200, description="Ok", schema={"ok": True, "users": list[User]})
async def all_user(db):
    service = await InitData.user_service(db)
    res = await service.user_repo.get_all()
    return jsonify({
        "ok": True,
        "users": [user.to_dict() for user in res]
    }), 200


@view.get("/user/roles", strict_slashes=False)
@status_code(200, description="List of roles")
def roles():
    return [r for r in Role.__members__]


@view.patch("/user/<matricule>", strict_slashes=False)
@inject_db
@parse_to_schema(PatchUser)
@auth_required(role=(Role.BACKOFFICE,))
async def update_user(matricule, data: PatchUser, db):
    service = await InitData.user_service(db)
    user_dict = data.model_dump()
    try:
        user = await service.from_matricule(matricule)
        for k, v in user_dict.items():
            setattr(user, k, v)
        assert await service.user_repo.update(user)
    except (Exception, UserException):
        traceback.print_exc()
        return jsonify({"message": "Utilisateur inexistant"}), 400
    return jsonify({"message": "Success"}), 200

