import traceback
from functools import wraps
import inspect
from typing import Type, get_args, get_origin, Union
from types import UnionType
from dataclasses import is_dataclass

from flask import jsonify, request
from werkzeug.exceptions import BadRequest
from werkzeug.utils import secure_filename

from src.tools.utils import get_func_args

from pydantic import ValidationError, BaseModel

from src.web.schema import FileTypeSchema


def is_file_field(schema: Type):
    if schema == bytes or schema == FileTypeSchema:
        return True
    _o = get_origin(schema)
    if _o == Union or _o == UnionType:
        if any(is_file_field(s) for s in get_args(schema)):
            return True
    return False


def parse_to_schema(schema: Type[BaseModel] | Type, method="json"):
    assert method in ["json", "get_json", "args", "form", "files"] or callable(method), \
        "method must be json or get_json"
    try:
        assert issubclass(schema, BaseModel)
        for _k, _info in schema.model_fields.items():
            if is_file_field(_info.annotation):
                def _hack_method():
                    _values = request.form.to_dict()
                    for f in request.files:
                        _file = request.files[f]
                        _file.filename = secure_filename(_file.filename or "")
                        _values[f] = _file
                    return _values

                method = _hack_method
    except (TypeError, AssertionError):
        pass

    def _get_value():
        if isinstance(method, str):
            if method in ("json", "get_json"):
                try:
                    values = request.get_json(force=True)
                except (ValueError, BadRequest):
                    values = request.form.to_dict()
            else:
                values = getattr(request, method).to_dict()
        else:
            values = method()
        if is_dataclass(schema):
            if hasattr(schema, "from_dict"):
                return schema.from_dict(values)
        return schema(**values)

    def inner(func):
        setattr(func, "_schema", schema)
        setattr(func, "_schema_method", method)
        def _get_k_args(args, kwargs):
            values = _get_value()
            keys = get_func_args(func)
            if "data" in keys:
                kwargs["data"] = values
            else:
                args = tuple([values] + list(args))
            return args, kwargs

        if inspect.iscoroutinefunction(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                try:
                    args, kwargs = _get_k_args(args, kwargs)
                except (ValueError, ValidationError, TypeError):
                    traceback.print_exc()
                    return jsonify({"ok": False, "msg": "bad input got"}), 400
                return await func(*args, **kwargs)
        else:
            @wraps(func)
            def wrapper(*args, **kwargs):
                try:
                    args, kwargs = _get_k_args(args, kwargs)
                except (ValueError, ValidationError, TypeError):
                    return jsonify({"ok": False, "msg": "bad input got"}), 400
                return func(*args, **kwargs)
        return wrapper

    return inner


def status_code(status_code, schema=None, description=None):
    def inner(func):
        _desc = getattr(func, "_status_code", {})
        _desc.setdefault(status_code, {"description": description, "schema": schema})
        setattr(
            func,
            "_status_code",
            _desc
        )
        return func
    return inner

