from flask import Blueprint, jsonify

from src.domain.entities.suppliers import Supplier
from src.domain.entities.user import Role
from src.web.decorators import parse_to_schema, status_code, auth_required, inject_db

from init import InitData


view = Blueprint("supplier", __name__)


@view.get("/supplier", strict_slashes=False)
@inject_db
@status_code(200, description="Success", schema=list[Supplier])
@auth_required()
async def get_supplier(db):
    service = await InitData.immobilization_service(db)
    res = await service.get_full("supplier")
    return jsonify(res)


@view.post("/supplier", strict_slashes=False)
@inject_db
@parse_to_schema(Supplier)
@status_code(201, description="Success")
@auth_required(role=(Role.BACKOFFICE,))
async def create_family(data: Supplier, db):
    service = await InitData.immobilization_service(db)
    await service.repo.create_supplier(data)
    return jsonify({"message": "Success"}), 201
