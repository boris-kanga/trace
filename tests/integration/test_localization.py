from src.domain.entities.localization import Agency, Localization
from init import InitData


async def test_not_authorized_agency_creation(inventorist_api):
    a = Agency("code", "Test agence")
    res = await inventorist_api.post(
        "/api/agency",
        json={
            "code_agency": a.code_agency,
            "title": a.title
        }
    )
    assert res.status_code == 401

async def test_create_agency(backoffice_api):
    a = Agency("code", "Test agence")
    res = await backoffice_api.post(
        "/api/agency",
        json={
            "code_agency": a.code_agency,
            "title": a.title
        }
    )
    assert res.status_code == 201


async def test_delete_agency(backoffice_api, db):
    a = Agency("code1", "Test agency")
    service = await InitData.immobilization_service(db)

    await service.create_agency(a)
    res = await backoffice_api.delete(
        "/api/agency/"+a.code_agency
    )
    assert res.status_code == 200
    assert await service.get_full("agency") == []


async def test_delete_agency_with_immobilization(backoffice_api, db):
    a = Agency("code1", "Test agency")
    service = await InitData.immobilization_service(db)

    await service.create_agency(a)

    res = await backoffice_api.delete(
        "/api/agency/" + a.code_agency
    )
    assert res.status_code == 400


async def test_get_agency_list(backoffice_api, db):
    a1 = Agency("code1", "Test agency")
    a2 = Agency("code2", "Test agency")

    service = await InitData.immobilization_service(db)

    await service.create_agency(a1)
    await service.create_agency(a2)

    res = await backoffice_api.get(
        "/api/agency"
    )
    assert res.status_code == 200
    assert set(Agency(**a) for a in res.json()["data"]) == {a1, a2}


async def test_localization_creation(backoffice_api, db):
    a1 = Agency("code1", "Test agency")

    service = await InitData.immobilization_service(db)

    await service.create_agency(a1)

    res = await backoffice_api.post(
        "/api/agency/" + a1.code_agency+ "/localization",
        json={
            "location_code": "REZ12000"
        }
    )
    assert res.status_code == 201


async def test_localization_delete(backoffice_api, db):
    a1 = Agency("code1", "Test agency")

    service = await InitData.immobilization_service(db)

    await service.create_agency(a1)

    loc = Localization(
            "REZ12000",
            a1
        )
    await service.repo.create_localization(loc)

    res = await backoffice_api.delete(
        "/api/agency/" + a1.code_agency+ "/localization/"+loc.location_code
    )
    assert res.status_code == 200


async def test_localization_get(backoffice_api, db):
    a1 = Agency("code1", "Test agency")

    service = await InitData.immobilization_service(db)

    await service.create_agency(a1)

    loc = Localization("REZ12000", a1)
    loc2 = Localization("REZ12001", a1)

    await service.repo.create_localization(loc)
    await service.repo.create_localization(loc2)


    res = await backoffice_api.get(
        "/api/localization/"
    )
    assert res.status_code == 200 and (
        set(Localization.from_dict(a) for a in res.json()["data"]) == {loc, loc2}
    )
