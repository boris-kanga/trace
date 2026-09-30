from flask import Blueprint, jsonify

from src.domain.entities.localization import Agency, Localization
from src.domain.entities.user import Role
from src.web.decorators import parse_to_schema, status_code, auth_required, inject_db

from init import InitData
from src.web.schema import LocalizationCreation

view = Blueprint("localization", __name__)


@view.get("/agency", strict_slashes=False)
@inject_db
@status_code(200, description="List of active agency", schema={"ok": True, "data": list[Agency]})
@auth_required()
async def agency(db):
    service = await InitData.immobilization_service(db)
    res = await service.get_full("agency")
    return jsonify({
        "ok": True,
        "data": res
    }), 200


@view.post("/agency", strict_slashes=False)
@inject_db
@parse_to_schema(Agency)
@status_code(201, description="Agency created successfully", schema={"message": "success"})
@auth_required(role=(Role.BACKOFFICE,))
async def create_agency(data: Agency, db):
    service = await InitData.immobilization_service(db)
    await service.create_agency(data)
    return jsonify({"message": "success"}), 201


@view.delete("/agency/<string:code_agency>")
@inject_db
@status_code(200, description="Agency successfully deleted", schema={"message": "success"})
@status_code(400, description="Impossible to delete")
@auth_required(role=(Role.BACKOFFICE,))
async def delete_agency(code_agency, db):
    service = await InitData.immobilization_service(db)
    size, res = await service.delete_agency(code_agency)
    if res:
        return jsonify({"message": "success"}), 200
    return jsonify({
        "message": "%s biens sont liés a cette agence veuillez"
                   " les rattacher ailleurs avant suppression" % (size,)
    }
    ), 400



@view.post("/agency/<string:code_agency>/localization")
@inject_db
@parse_to_schema(LocalizationCreation)
@status_code(200, description="Localization creation success", schema={"message": "success"})
@status_code(400, description="Required existing agency")
@auth_required(role=(Role.BACKOFFICE,))
async def create_localization(code_agency, data: LocalizationCreation, db):
    service = await InitData.immobilization_service(db)
    try:
        res = await service.repo.create_localization(
            Localization(
                data.location_code,
                Agency(code_agency, "")
            )
        )
        return jsonify({"message": "success"}), 201
    except:
        pass

    return jsonify({"message": "Agence inexistant"}), 400


@view.delete("/agency/<string:code_agency>/localization/<string:location_code>")
@inject_db
@status_code(200, description="localization successfully deleted", schema={"message": "success"})
@status_code(400, description="Impossible to delete")
@auth_required(role=(Role.BACKOFFICE,))
async def delete_localization(code_agency, location_code, db):
    service = await InitData.immobilization_service(db)
    size, res = await service.delete_localization(
        code_agency, location_code
    )
    if res:
        return jsonify({"message": "success"}), 200
    return jsonify({
        "message": "%s biens sont liés a cette localisation veuillez"
                   " les rattacher ailleurs avant suppression" % (size,)
    }
    ), 400


@view.get("/localization", strict_slashes=False)
@inject_db
@status_code(200, description="List of active localization", schema={"ok": True, "data": list[Localization]})
@auth_required()
async def localization(db):
    service = await InitData.immobilization_service(db)
    res = await service.get_full("localization")
    return jsonify({"ok": True, "data": res}), 200
