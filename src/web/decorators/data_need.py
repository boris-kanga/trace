from functools import wraps

from flask import current_app
from init import InitData
from src.tools.utils import get_func_args


def inject_db(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        if "db" in get_func_args(func):
            try:
                kwargs["db"] = await InitData.default_db(
                    **current_app.config["db_params"]
                )
                return await func(*args, **kwargs)
            finally:
                if "db" in kwargs:
                    await kwargs["db"].close()
        return await func(*args, **kwargs)
    return wrapper


def inject_storage(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        if "storage" in get_func_args(func):
            try:
                kwargs["storage"] = await InitData.default_storage(
                    **current_app.config["storage_params"]
                )
                return await func(*args, **kwargs)
            finally:
                pass
        return await func(*args, **kwargs)
    return wrapper
