from datetime import datetime

import pytest
from testcontainers.community.postgres import PostgresContainer

import httpx
from asgiref.wsgi import WsgiToAsgi

import os
import sys


sys.path.insert(
    0,
    os.path.dirname(
        os.path.dirname(os.path.abspath(__file__))
    )
)

from src.infrastructure.database.repositories.user_repository import UserRepository
from src.infrastructure.password_hasher.hasher import PasswordHasher
from src.domain.entities.user import User, Role


print("[++] In pytest config")


async def _restore_db_session(db_session):
    await db_session.execute(
        """
            DO $$ 
            DECLARE 
                r RECORD;
            BEGIN
                FOR r IN (SELECT tablename FROM pg_tables WHERE schemaname = 'public') LOOP
                    EXECUTE 'TRUNCATE TABLE ' || quote_ident(r.tablename) || ' RESTART IDENTITY CASCADE;';
                END LOOP;
            END $$;
        """
    )


def _get_user_dict():
    return {
        "matricule": "matricule",
        "first_name": "first_name",
        "last_name": "last_name",
        "email": "email@socgen.com",
        "password": "password",
        "role": Role.INVENTORIST,
        "is_active": True,
        "last_login_at": datetime.now(),
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
        "deleted_at": None
    }


@pytest.fixture(scope="session")
def postgres_container():
    """Démarre un conteneur PostgreSQL éphémère."""
    # Utilisation d'une version légère d'Alpine Linux
    with PostgresContainer("postgres:18-alpine", driver="asyncpg") as postgres:
        yield postgres


@pytest.fixture(scope="session")
def db_params(postgres_container):
    host = postgres_container.get_container_host_ip()
    port = postgres_container.get_exposed_port(5432)
    user = postgres_container.username
    password = postgres_container.password
    dbname = postgres_container.dbname
    return dict(
        host=host, port=port,
        user=user, password=password, database_name=dbname
    )


@pytest.fixture(scope="session")
async def db_session(db_params):
    from init import InitData

    dbo = await InitData.default_db(
        **db_params,
        init_db=True
    )
    yield dbo
    await dbo.close()


@pytest.fixture(scope="function")
async def db(db_session):
    yield db_session
    await _restore_db_session(db_session)


@pytest.fixture()
def user_dict():
    yield _get_user_dict()


@pytest.fixture(scope="session")
def inventorist_user_dict():
    _dict = _get_user_dict()
    _dict["matricule"] = "invent"
    yield _dict


@pytest.fixture(scope="session")
def backoffice_user_dict():
    _dict = _get_user_dict()
    _dict["matricule"] = "backoffice"
    _dict["role"] = Role.BACKOFFICE
    yield _dict


@pytest.fixture(scope="session")
def get_user():
    _user = _get_user_dict()
    def _(**kwargs):
        _user.update(kwargs)
        return User.from_dict(_user, password_hasher=PasswordHasher())
    yield _


@pytest.fixture(scope="session")
async def api(db_params):
    from src.web.app import create_app
    app = create_app(
        {
            "db_params": db_params,
            "TESTING": True,
        }
    )
    asgi_app = WsgiToAsgi(app)

    async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=asgi_app),
            base_url="http://testserver"
    ) as client:
        yield client


@pytest.fixture()
async def api_with_user_connected(api, db):
    methods = {
        "post": None, "put": None, "patch": None,
        "delete": None, "head": None, "options": None, "get": None
    }
    for method in methods:
        methods[method] = getattr(api, method)

    async def _(user, password):
        repo = UserRepository(db)
        assert await repo.create(user)
        res = await methods["post"](
            "/api/login",
            json={
                "username": user.matricule,
                "password": password
            }
        )
        assert res.status_code == 200
        token = res.json()["token"]
        headers = {"Authorization": f"Bearer {token}"}
        for mth in methods:
            def make_patched_method(_mth=mth):
                async def patched_method(*args, **kwargs):
                    call_headers = kwargs.get("headers", {})
                    kwargs["headers"] = {**headers, **call_headers}
                    return await methods[_mth](*args, **kwargs)

                return patched_method

            setattr(api, mth, make_patched_method())
        return api

    yield _

    for method in methods:
        setattr(api, method, methods[method])


@pytest.fixture(scope="function")
async def backoffice_api(get_user, backoffice_user_dict, api_with_user_connected):
    yield await api_with_user_connected(
        get_user(**backoffice_user_dict),
        backoffice_user_dict["password"]
    )


@pytest.fixture(scope="function")
async def inventorist_api(get_user, inventorist_user_dict, api_with_user_connected):
    yield await api_with_user_connected(
        get_user(**inventorist_user_dict),
        inventorist_user_dict["password"]
    )
