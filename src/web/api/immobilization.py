from uuid import UUID

from flask import Blueprint, jsonify, request, Response

from src.core.logger import get_logger
from src.domain.entities.campaign import Inventory
from src.domain.entities.immobilization import Immobilization, ImmobilizationSubFamily, ImmobilizationStatus
from src.domain.entities.localization import Localization, Agency
from src.domain.entities.suppliers import Supplier
from src.domain.entities.user import Role, User
from src.services.immobilization_service import ImmobilizationService

from src.web.decorators import inject_db, parse_to_schema, status_code, auth_required
from src.web.decorators.data_need import inject_storage

from init import InitData
from src.web.schema import ImmoFilters, ImmoCreation, ImmoInventoryArgs, ImmoGenerateQrCode, ChangeQrCode

view = Blueprint("immobilization", __name__)
logger = get_logger(__name__)


async def _get_loc(service, id_localization=None, location_code=None, code_agency=None):
    if isinstance(id_localization, int):
        loc = Localization(
            str(location_code or ""),
            Agency(str(code_agency or ""), "")
        )
        loc.id_localization = id_localization
    else:
        loc = None
        locations = await service.repo.get_localization()
        for l in locations:
            if l.location_code == location_code and l.agency == code_agency:
                loc = l
    return loc


async def _get_immo_from_creation(data: ImmoCreation, service: ImmobilizationService, user: User):
    loc = await _get_loc(
        service, data.id_localization, data.location_code, data.code_agency
    )
    if loc is None:
        return "Please fill code_agency and location_code or id_localization", 400
    im = Immobilization(
        data.id_immobilization_amplitude,
        data.title,
        loc,
        ImmobilizationSubFamily(
            data.id_subfamily,
        ),
        Supplier(data.supplier),
        data.order_number,
        data.order_date,
        data.delivery_note_number,
        data.delivery_note_date,
        data.invoice_number,
        data.invoice_date,
        data.acquittement_date,
        data.acquittement_value,
        user,
        user,
        serial_number=data.serial_number,
        comment=data.comment,
        status=ImmobilizationStatus(data.status),
        ubigreen_number=data.ubigreen_number
    )

    return im


async def _save(im: Immobilization, service: ImmobilizationService, data: ImmoCreation):
    res = await service.repo.save(im)
    if res and data.main_image is not None:
        await service.put_file(
            im, data.main_image.read(),
            file_type="main",
            content_type=data.main_image.content_type,
            ext=data.main_image.filename.split(".")[-1]
        )
    if res and data.invoice_file is not None:
        await service.put_file(
            im, data.invoice_file.read(),
            file_type="invoice",
            content_type=data.invoice_file.content_type,
            ext=data.invoice_file.filename.split(".")[-1]
        )

    return res


@view.get("/immobilization", strict_slashes=False)
@inject_db
@parse_to_schema(ImmoFilters, method="args")
@status_code(200, description="List of immobilization", schema={"ok": True, "data": list[Immobilization]})
@auth_required(role=(Role.BACKOFFICE,))
async def immobilization(data: ImmoFilters, db):
    filters = data.model_dump()
    service = await InitData.immobilization_service(db)
    res = await service.repo.get(**filters)
    cursor = None
    if res:
        cursor = max([imm.id_immobilization for imm in res])
    return jsonify({"ok": True, "data": res, "cursor": cursor})


@view.get("/immobilization/<string:item>", strict_slashes=False)
@inject_db
@inject_storage
@status_code(404, description="Immobilization introuvable", schema={"ok": False, "message": "Immobilization introuvable"})
@status_code(200, description="Les données", schema={"ok": True, "images": {"main": "url"}, "data": Immobilization})
@auth_required()
async def immobilization_item(item, db, storage):
    try:
        if "?" in item:
            item = item.split("?")[1]
        item = UUID(item)
    except ValueError:
        return jsonify({"message": "Immobilization introuvable"}), 404
    service = await InitData.immobilization_service(db, storage)
    res = await service.repo.get(id_immobilization=item)
    if not res:
        return jsonify({"ok": False, "message": "Immobilization introuvable"}), 404
    im = res[0]
    imgs = await service.get_images_url(im, url=request.host)

    cpg_service = await InitData.campaign_service(db)
    most_recent_status = await cpg_service.repo.most_recent_immobilization_status(item)

    return jsonify({"ok": True, "images": imgs, "data": im, "most_recent_status": most_recent_status}), 200


@view.post("/immobilization", strict_slashes=False)
@inject_db
@inject_storage
@parse_to_schema(ImmoCreation)
@status_code(201, description="Success", schema={"ok": True, "id": "id"})
@auth_required(role=(Role.BACKOFFICE,))
async def create_immo(
        data: ImmoCreation,
        db, storage, user: User
    ):
    service = await InitData.immobilization_service(db, storage)
    im = await _get_immo_from_creation(data, service, user)
    if isinstance(im, tuple):
        msg, s = im
        return jsonify({"ok": False, "message": msg}), s

    res = await _save(im, service, data)

    return jsonify({"ok": True, "id": str(res)}), 201


@view.patch("/immobilization/<string:_id>", strict_slashes=False)
@inject_db
@inject_storage
@parse_to_schema(ImmoCreation)
@status_code(200, description="Success", schema={"ok": True})
@auth_required()
async def modify_immo(
        _id,
        data: ImmoCreation,
        db, storage, user: User
    ):
    try:
        _id = UUID(_id)
    except ValueError:
        return jsonify({"message": "Immobilization introuvable"}), 404
    service = await InitData.immobilization_service(db, storage)
    im = await _get_immo_from_creation(data, service, user)
    if isinstance(im, tuple):
        msg, s = im
        return jsonify({"ok": False, "message": msg}), s
    im.id_immobilization = _id

    res = await _save(im, service, data)

    return jsonify({"ok": res}), 200 if res else 404


@view.delete("/immobilization/<string:_id>", strict_slashes=False)
@inject_db
@inject_storage
@status_code(200, description="Success", schema={"ok": True})
@auth_required(role=(Role.BACKOFFICE,))
async def delete_immo(
        _id,
        db, storage, user: User
    ):
    service = await InitData.immobilization_service(db, storage)
    im = await service.repo.get(id_immobilization=_id)
    if not im:
        return jsonify({"ok": False, "message": "Immobilization introuvable"}), 404
    im = im[0]
    im.updated_by = user
    res = await service.repo.delete(im)
    return jsonify({"ok": res.size == 1}), 200 if res.size == 1 else 404


@view.get("/immobilization/<string:_id>/qr_code.png", strict_slashes=False)
@inject_db
@inject_storage
@status_code(200, description="Retrieve image")
@auth_required(role=(Role.BACKOFFICE,))
async def get_qr_code(_id, db, storage):
    service = await InitData.immobilization_service(db, storage)
    immo = await service.repo.get(id_immobilization=_id)
    if not immo:
        return jsonify({"ok": False, "message": "Immobilization not available"}), 404

    dst = await service.generate_qr_code(_id, request.host_url)

    dst.seek(0)

    return Response(dst.getvalue(), mimetype="image/png")


@view.get("/immobilization/<string:_id>/inventory", strict_slashes=False)
@inject_db
@inject_storage
@parse_to_schema(ImmoInventoryArgs, method="args")
@status_code(200, description="Success", schema={"ok": True, "data": list[Inventory]})
@auth_required()
async def inventory_history(_id, db, data: ImmoInventoryArgs):
    campaign_s = await InitData.campaign_service(db)
    return jsonify({
        "ok": True, "data": await campaign_s.repo.get_inventory_history_on_immobilization(
            _id,
            data.limit
        )
    })


@view.post("/immobilization/generate-qrcode", strict_slashes=False)
@inject_db
@inject_storage
@parse_to_schema(ImmoGenerateQrCode)
@status_code(200, description="Success", schema={"ok": True, "data": list[str]})
@auth_required(role=(Role.BACKOFFICE,))
async def generate_immo_qrcode(db, data: ImmoGenerateQrCode, user: User, storage):
    service = await InitData.immobilization_service(db, storage)

    kw = data.model_dump()
    loc = await _get_loc(
        service,
        id_localization=kw.pop("id_localization", None),
        location_code=kw.pop("location_code", None),
        code_agency=kw.pop("code_agency", None)
    )

    id_subfamily = kw.pop("id_subfamily", None)
    sub_family = None if id_subfamily is None else ImmobilizationSubFamily(id_subfamily)

    supplier = Supplier(kw.pop("supplier", None))

    kw["localization"] = loc
    kw["sub_family"] = sub_family
    kw["supplier"] = supplier

    res = await service.create_batch_immobilization(**kw, user=user)
    return jsonify({"ok": True, "data": res}), 200


@view.post("/immobilization/<string:_id>/change-qrcode", strict_slashes=False)
@inject_db
@inject_storage
@parse_to_schema(ChangeQrCode)
@status_code(200, description="Success", schema={"ok": True})
@auth_required()
async def change_qrcode(_id, db, data: ChangeQrCode, user: User, storage):
    service = await InitData.immobilization_service(db, storage)
    new_id = data.id_immobilization
    try:
        new_id = UUID(new_id)
    except ValueError:
        return jsonify({"ok": False, "message": "Invalid qrcode"}), 400

    try:
        _id = UUID(_id)
        immo = await service.repo.get(id_immobilization=_id)

        assert immo
        immo = immo[0]
    except (ValueError, AssertionError):
        return jsonify({"ok": False, "message": "Immobilization Not found"}), 404

    immo.updated_by = user

    res = await service.change_immo_id(immo, new_id)

    return jsonify({"ok": res}), 200 if res else 400


