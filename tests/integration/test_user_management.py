from src.infrastructure.database.repositories.user_repository import UserRepository
from src.domain.entities.user import User, Role
from src.infrastructure.password_hasher.hasher import PasswordHasher


async def _create_user(user_dict, db):
    repo = UserRepository(db)

    user = User.from_dict(
        user_dict, password_hasher=PasswordHasher()
    )

    assert await repo.create(user)
    return user


async def test_create_user(db, user_dict):
    repo = UserRepository(db)
    user = await _create_user(user_dict, db)

    user2 = await repo.get(user.matricule)
    assert user2 == user


async def test_api_create_user(backoffice_api):
    res = await backoffice_api.post(
        "/api/user",
        json={
            "matricule": "5307",
            "first_name": "boris",
            "last_name": "kanga",
            "email": "boris.kanga@socgen.com",
            "role": Role.INVENTORIST.value
        }
    )
    if res.status_code != 201:
        print(res.json())
    assert res.status_code == 201


async def test_login_user_not_exists(api):
    res = await api.post(
        "/api/login/",
        json={
            "username": "fake-username",
            "password": "fake-password"
        }
    )
    assert res.status_code == 401, "fake-username should be exist"


async def test_login_user_bad_password(api, db, user_dict):
    user = await _create_user(user_dict, db)
    res = await api.post(
        "/api/login/",
        json={
            "username": user.matricule,
            "password": "fake-password"
        }
    )
    assert res.status_code == 401, "fake password should not succeed login"


async def test_user_login(api, user_dict, db):
    user = await _create_user(user_dict, db)
    res = await api.post(
        "/api/login/",
        json={
            "username": user.matricule,
            "password": user_dict["password"]
        }
    )
    assert res.status_code == 200
    cookies = res.cookies
    res = res.json()

    assert (
            res.get("token")
            and res["user"]["matricule"] == user.matricule
            and cookies.get("access_token_cookie")
            )



