from uuid import UUID

from flask import Blueprint, jsonify

from src.domain.entities.campaign import Campaign, Inventory
from src.domain.entities.immobilization import Immobilization
from src.domain.entities.user import Role, User
from src.web.decorators import inject_db, auth_required, status_code, parse_to_schema

from init import InitData
from src.web.decorators.data_need import inject_storage
from src.web.schema import InventoryMark, CampaignImmobilizationFilter


view = Blueprint('inventory', __name__)


@view.get('/inventory/campaign/active', strict_slashes=False)
@inject_db
@status_code(200, description="Success", schema={"ok": True, "data": list[Campaign]})
@auth_required()
async def active_campaign(db, user: User):
    service = await InitData.campaign_service(db)
    kw = {
        "status": "active",
    }
    if user.role == Role.INVENTORIST:
        kw["user"] = user

    res = await service.repo.get(**kw)

    return jsonify({"ok": True, "data": res})


@view.get('/inventory/campaign/<int:_id>/zone', strict_slashes=False)
@inject_db
@status_code(200, description="Success", schema={
    "ok": True, "data": [{
        "code_agency": "code_agency",
        "id_localization": "id_localization",
        "immobilization_count": 0,
        "already_treat_count": 0}]
})
@auth_required()
async def inventory_campaign_zone(_id, db, user: User):
    service = await InitData.campaign_service(db)

    res = await service.repo.campaign_zone(_id, user.matricule, user.role == Role.BACKOFFICE)
    return jsonify({"ok": True, "data": res})


@view.get('/inventory/campaign/<int:_id>', strict_slashes=False)
@inject_db
@status_code(200, description="Success", schema={
    "ok": True, "data": [{
        "code_agency": "code_agency",
        "id_localization": "id_localization",
        "title": "title",
        "inventorist": "inventorist", "id_immobilization": "uuid",
        "status": "GOOD"}]
})
@auth_required()
async def inventory_history(_id, db, user: User):
    service = await InitData.campaign_service(db)
    res = await service.repo.get_inventory_history(_id, user.matricule)
    return jsonify({"ok": True, "data": res})


@view.get('/inventory/campaign/<int:_id>/immobilization', strict_slashes=False)
@inject_db
@status_code(200, description="Success", schema={"ok": True, "data": list[Immobilization]})
@parse_to_schema(CampaignImmobilizationFilter, method="args")
@auth_required()
async def campaign_immobilization(_id, db, user: User, data: CampaignImmobilizationFilter):
    data = data.model_dump()
    data["localization_ids"] = list(
        filter(
            lambda x: str(x).isnumeric(),
            data["localization_ids"]
        )
    )
    data["localization_ids"] = [int(x) for x in data["localization_ids"]]
    service = await InitData.campaign_service(db)
    res = await service.repo.campaign_immobilization(_id, user.matricule, **data)
    return jsonify({"ok": True, "data": res})


@view.post('/inventory/campaign/<int:_id>/immobilization/<string:imm_id>', strict_slashes=False)
@inject_db
@inject_storage
@parse_to_schema(InventoryMark)
@status_code(200, description="Success", schema={"ok": True})
@auth_required()
async def mark_inventory(_id, imm_id: str, data: InventoryMark, db, user: User, storage):
    im_service = await InitData.immobilization_service(db, storage)

    try:
        imm_id = UUID(imm_id)
        imm = await im_service.repo.get(id_immobilization=imm_id)
        assert imm
        imm = imm[0]
    except (ValueError, AssertionError):
        return jsonify({"ok": False, "message": "Immobilization inconnue"}), 400

    service = await InitData.campaign_service(db)
    # TODO: check if user can do this inventory

    ok, msg = await service.mark_inventory(
        Inventory(
            _id, imm, data.status,
            user, data.comment,
            data.latitude, data.longitude, data.device_id
        )
    )

    if ok:
        if imm.serial_number is None:
            imm.serial_number = data.serial_number
            imm.updated_by = user
            await im_service.repo.save(imm)

        if data.main_image is not None:
            imgs = await im_service.get_images_url(imm)
            if "main" not in imgs:
                await im_service.put_file(
                    imm_id,
                    data.main_image.read(),
                    file_type="main",
                    content_type=data.main_image.content_type,
                    ext=data.main_image.filename.split(".")[-1]
                )
        if data.current_img:
            await im_service.put_file(
                imm_id,
                data.current_img.read(),
                file_type="image",
                content_type=data.current_img.content_type,
                ext=data.current_img.filename.split(".")[-1]
            )

    return jsonify({"ok": ok, "message": msg}), 200 if ok else 400
