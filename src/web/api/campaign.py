from flask import Blueprint, jsonify

from src.domain.entities.campaign import Campaign, CampaignStatus
from src.domain.entities.immobilization import Immobilization
from src.domain.entities.user import Role, User
from src.web.decorators import inject_db, auth_required, status_code, parse_to_schema

from init import InitData
from src.web.schema import CampaignCreation, CampaignInventorist, CampaignFilter, CampaignImmobilizationFilter

view = Blueprint('campaign', __name__)


@view.get('/campaign', strict_slashes=False)
@inject_db
@parse_to_schema(CampaignFilter, method="args")
@status_code(200, description="Success", schema={
    "ok": True, "data": list[Campaign], "stats": {"0": {"user_count": 0, "immobilization_count": 0, "zone_count": 0}}
})
@auth_required(role=(Role.BACKOFFICE,))
async def campaign(data: CampaignFilter, db):
    service = await InitData.campaign_service(db)
    res, stats = await service.get_campaign_and_stats(**data.model_dump())
    return jsonify({
        "ok": True,
        "data": res,
        "stats": stats
    })


@view.get('/campaign/<int:_id>', strict_slashes=False)
@inject_db
@status_code(200, description="Success", schema={
    "ok": True, "data": Campaign, "stats": {"user_count": 0, "immobilization_count": 0, "zone_count": 0}
})
@status_code(404, description="Not found")
@auth_required(role=(Role.BACKOFFICE,))
async def campaign_item(_id, db):
    service = await InitData.campaign_service(db)
    res, stats = await service.get_campaign_and_stats(_id=_id)
    zones = await service.repo.campaign_zone(_id)
    if not res:
        return jsonify({"ok": False, "message": "Campagne inconnue"}), 404
    return jsonify({"ok": True, "data": res[0], "stats": stats.get(int(_id)) or {}, "zones": zones}), 200


@view.patch("/campaign/<int:_id>", strict_slashes=False)
@inject_db
@parse_to_schema(CampaignCreation)
@status_code(200, description="Return inventorists")
@status_code(400, description="Error", schema={"ok": False, "message": "Choisir les localisations"})
@auth_required(role=(Role.BACKOFFICE,))
async def modify_campaign(
        _id,
        data: CampaignCreation,
        db, user: User
    ):
    if not data.localization_ids:
        return jsonify({"ok": False, "message": "Choisir les localisations"}), 400
    service = await InitData.campaign_service(db)
    cpg = await service.create_campaign(
        **data.model_dump(), user=user, _id=_id
    )
    if isinstance(cpg, Campaign):
        res = await service.repo.get_inventorist(_id)
        return jsonify({"ok": True, "data": cpg, "inventorist": res}), 200

    return jsonify({"ok": False, "message": cpg}), 400


@view.delete('/campaign/<int:_id>', strict_slashes=False)
@inject_db
@status_code(200, description="Success", schema={"ok": True})
@status_code(404, description="Not found")
@auth_required(role=(Role.BACKOFFICE,))
async def delete_campaign_item(_id, db):
    service = await InitData.campaign_service(db)
    ok = await service.repo.delete_campaign(_id)
    return jsonify({"ok": ok}), 200 if ok else 404


@view.post("/campaign", strict_slashes=False)
@inject_db
@parse_to_schema(CampaignCreation)
@status_code(201, description="Success", schema={"ok": True, "id": "id"})
@status_code(400, description="Error", schema={"ok": False, "message": "Choisir les localisations"})
@auth_required(role=(Role.BACKOFFICE,))
async def create_campaign(
        data: CampaignCreation,
        db, user: User
    ):
    if not data.localization_ids:
        return jsonify({"ok": False, "message": "Choisir les localisations"}), 400
    service = await InitData.campaign_service(db)
    cpg = await service.create_campaign(
        **data.model_dump(), user=user
    )
    if isinstance(cpg, Campaign):
        return jsonify({"ok": True, "id": cpg.campaign_id}), 201

    return jsonify({"ok": False, "message": cpg}), 400


@view.get("/campaign/<int:_id>/inventorist", strict_slashes=False)
@inject_db
@status_code(200, description="Success")
@auth_required(role=(Role.BACKOFFICE,))
async def get_inventorist(
        _id,
        db
    ):
    service = await InitData.campaign_service(db)
    res = await service.repo.get_inventorist(_id)
    return jsonify(res)


@view.patch("/campaign/<int:_id>/inventorist", strict_slashes=False)
@inject_db
@parse_to_schema(CampaignInventorist)
@status_code(200, description="Success")
@auth_required(role=(Role.BACKOFFICE,))
async def add_or_update_campaign_inventorist(
        _id, data: CampaignInventorist, db
    ):
    service = await InitData.campaign_service(db)
    ok, msg = await service.add_inventorist(_id, **data.model_dump())
    return jsonify({"ok": ok, "message": msg}), 200 if ok else 400


@view.delete("/campaign/<int:_id>/inventorist/<string:matricule>", strict_slashes=False)
@inject_db
@status_code(200, description="Success")
@auth_required(role=(Role.BACKOFFICE,))
async def delete_inventorist(
        db, _id, matricule
    ):
    service = await InitData.campaign_service(db)
    ok = await service.repo.delete_inventorist(_id, matricule)
    msg = "Success" if ok else "Ignored"
    return jsonify({"ok": ok, "message": msg}), 200 if ok else 400


@view.delete("/campaign/<int:_id>/mark-as-ended", strict_slashes=False)
@inject_db
@status_code(200, description="Success")
@auth_required(role=(Role.BACKOFFICE,))
async def mark_as_ended(
        db, _id, user
    ):
    service = await InitData.campaign_service(db)
    cpg = await service.repo.get(_id=_id)
    if not cpg:
        return jsonify({"ok": False, "message": "Not found"}), 404
    cpg = cpg[0]
    cpg.updated_by = user

    _bool = await service.mark_ended(cpg)

    return jsonify({"ok": _bool}), 200 if _bool else 400


@view.get('/campaign/<int:_id>/immobilization', strict_slashes=False)
@inject_db
@status_code(200, description="Success", schema={"ok": True, "data": list[Immobilization]})
@parse_to_schema(CampaignImmobilizationFilter, method="args")
@auth_required(role=(Role.BACKOFFICE,))
async def campaign_immobilization_list(_id, db, data: CampaignImmobilizationFilter):
    data = data.model_dump()
    data["localization_ids"] = list(
        filter(
            lambda x: str(x).isnumeric(),
            data["localization_ids"]
        )
    )
    data["localization_ids"] = [int(x) for x in data["localization_ids"]]
    service = await InitData.campaign_service(db)
    res = await service.repo.campaign_immobilization(_id, None, **data)
    return jsonify({"ok": True, "data": res})

