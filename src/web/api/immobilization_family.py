from flask import Blueprint, jsonify

from src.domain.entities.immobilization import ImmobilizationFamily, ImmobilizationSubFamily
from src.domain.entities.user import Role
from src.web.decorators import inject_db, parse_to_schema, status_code, auth_required

from init import InitData
from src.web.schema import ImmoSubFamilyCreation

view = Blueprint("family", __name__)


@view.post("/family", strict_slashes=False)
@inject_db
@parse_to_schema(ImmobilizationFamily)
@status_code(201, description="Success")
@auth_required(role=(Role.BACKOFFICE,))
async def create_family(data: ImmobilizationFamily, db):
    service = await InitData.immobilization_service(db)
    await service.repo.insert_family([data])
    return jsonify({"message": "Success"}), 201


@view.get("/sub-family", strict_slashes=False)
@inject_db
@status_code(200, description="Success", schema=list[ImmobilizationSubFamily])
@auth_required()
async def get_sub_family(db):
    service = await InitData.immobilization_service(db)
    res = await service.get_full("sub-family")
    return jsonify(res)


@view.get("/family", strict_slashes=False)
@inject_db
@status_code(200, description="Success", schema=list[ImmobilizationFamily])
@auth_required()
async def get_family(db):
    service = await InitData.immobilization_service(db)
    res = await service.get_full("family")
    return jsonify(res)


@view.post("/family/<string:id_family>/sub-family", strict_slashes=False)
@inject_db
@parse_to_schema(ImmoSubFamilyCreation)
@status_code(201, description="Success")
@auth_required(role=(Role.BACKOFFICE,))
async def create_subfamily(id_family: str, data: ImmoSubFamilyCreation, db):
    service = await InitData.immobilization_service(db)
    subfamily = ImmobilizationSubFamily(
        **data.model_dump(),
        family=id_family
    )
    await service.repo.insert_subfamily([subfamily])
    return jsonify({"message": "Success"}), 201