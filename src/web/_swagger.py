from dataclasses import is_dataclass, asdict

import re
from types import GenericAlias
from typing import Any

from flasgger import Swagger
from pydantic import BaseModel, TypeAdapter

from src.web.decorators.validator import is_file_field


def _get_default(json_dict: dict, _stck=None) -> dict | list | Any:
    defs = _stck if _stck else {}

    def _parse_value(v):
        if "default" in v:
            return v["default"]
        if "$ref" in v:
            return defs.get(v["$ref"])
        elif "anyOf" in v:
            return _parse_value(v["anyOf"][0])
        else:
            return (
                v.get("format") or v.get("title") or v["type"]
                if v["type"] == "string" else (
                    0 if v["type"] in ("integer", "number")
                    else (
                        True if v["type"] == "boolean" else (
                            "null" if v["type"] == "null" else (
                                _get_default(v) if v["type"] == "array" else v["type"]
                            )
                        )
                    )
                )
            )
    for def_key, d in json_dict.get("$defs", {}).items():
        def_key = "#/$defs/"+def_key
        if "enum" in d:
            defs[def_key] = d["enum"][0]
        else:
            defs[def_key] = {}
            for k, _v in d["properties"].items():
                defs[def_key][k] = _parse_value(_v)

    if "type" in json_dict and json_dict["type"] not in ("object", "array"):
        return _parse_value(json_dict)
    if "items" in json_dict:
        return [_parse_value(json_dict["items"])]
    return {
        k: _parse_value(v)
        for k, v in json_dict.get("properties", {}).items()
    }


def _parse_dict_example(dict_example):
    for k, v in dict_example.items():
        if is_dataclass(v) or isinstance(v, GenericAlias):
            dict_example[k] = _get_default(TypeAdapter(v).json_schema())
        if isinstance(v, dict):
            _parse_dict_example(v)
    return dict_example


def _update_ref(obj):
    if isinstance(obj, dict):
        if "$ref" in obj:
            obj["$ref"] = "#/definitions/"+obj["$ref"].split("/", 2)[2]
        for k, v in obj.items():
            _update_ref(v)
    elif isinstance(obj, (list,)):
        for i, v in enumerate(obj):
            _update_ref(v)


def add_swagger_views(app, swagger_endpoint="/api/swagger"):

    swagger_template = {
        "swagger": "2.0",
        "info": {
            "title": "TraceSafe Swagger API",
            "version": "1.0.0"
        },
        "securityDefinitions": {
            "BearerAuth": {
                "type": "apiKey",
                "name": "Authorization",
                "in": "header",
                "description": "Entrez votre token JWT sous la forme : Bearer <votre_token>"
            }
        },
        "definitions": {},
        "paths": {}
    }

    swagger_config = {
        "headers": [],
        "specs": [
            {
                "endpoint": 'apispec_1',
                "route": '/api/apispec_1.json',
                "rule_filter": lambda rule: True,
                "model_filter": lambda tag: True,
            }
        ],
        "static_url_path": "/api/flasgger_static",
        "swagger_ui": True,
        "specs_route": swagger_endpoint
    }

    with app.app_context():
        for rule in app.url_map.iter_rules():
            if rule.endpoint in ['static', 'flasgger.apispec_1', 'flasgger.static']:
                continue
            if str(rule) in ("/", "/api"):
                continue
            func = app.view_functions[rule.endpoint]

            _schema: BaseModel = getattr(func, "_schema", None)
            _status_codes = getattr(func, "_status_code", None)
            _schema_method = getattr(func, "_schema_method", None)
            _any_file_in_schema = []

            if is_dataclass(_schema):
                _schema = (_schema.__name__, TypeAdapter(_schema).json_schema())
            elif _schema:
                for _k, _info in _schema.model_fields.items():
                    if is_file_field(_info.annotation):
                        _any_file_in_schema.append(_k)

                _schema = (_schema.__name__, _schema.model_json_schema())

            if _schema and _schema_method != "args" and not _any_file_in_schema:
                swagger_template["definitions"][_schema[0]] = _schema[1]
                _update_ref(swagger_template["definitions"][_schema[0]])
                _schema = _schema[0]

            parameters = []
            for param in re.findall(r"<(?:(\w+):)?(.*?)>", str(rule)):
                parameters.append(
                    {
                        "name": param[1],
                        "in": "path",
                        "required": True,
                        "type": {"int": "integer", "str": "string"}.get(param[0] or "string", param[0]) or "string"
                    }
                )
            uri = re.sub(r"<(?:(\w+):)?(\w+)>", r"{\2}", str(rule))
            if uri not in swagger_template["paths"]:
                swagger_template["paths"][uri] = {}

            responses = {
                500: {"description": "Internal Server Error"},
                **({} if not getattr(func, "__need_auth", False) else {
                    401: {"description": "Unauthorized"}
                })

            }
            if _status_codes:
                for code, obj in _status_codes.items():
                    responses[code] = {}
                    if obj["description"]:
                        responses[code]["description"] = obj["description"]

                    if obj["schema"]:
                        if isinstance(obj["schema"], dict):
                            responses[code]["examples"] = {
                                "application/json": _parse_dict_example(obj["schema"])
                            }
                        else:
                            _sch = obj["schema"]
                            if is_dataclass(_sch) or isinstance(_sch, GenericAlias):
                                responses[code]["schema"] = TypeAdapter(_sch).json_schema()
                            else:
                                try:
                                    assert issubclass(_sch, BaseModel)
                                    responses[code]["schema"] = obj["schema"].model_json_schema()
                                except (AssertionError, TypeError):
                                    pass
                            if "$defs" in (responses[code].get("schema") or ()):
                                defs = responses[code]["schema"].pop("$defs")
                                _update_ref(defs)
                                swagger_template["definitions"].update(defs)
                                _update_ref(responses[code]["schema"], )
                            if "$definitions" in (responses[code].get("schema") or ()):
                                defs = responses[code]["schema"].pop("$definitions")
                                _update_ref(defs)
                                swagger_template["definitions"].update(defs)
                                _update_ref(responses[code]["schema"])

            for method in rule.methods:
                if method in ['OPTIONS', 'HEAD']:
                    continue
                path_mth = {
                    "tags": [rule.endpoint.split(".")[0]],
                    'responses': responses,
                    "parameters": parameters
                }
                if getattr(func, "__need_auth", False):
                    path_mth["security"] = [{"BearerAuth": []}]
                if _any_file_in_schema:
                    path_mth["parameters"].extend(
                        [
                            {
                                'name': q,
                                'in': 'formData',
                                'required': q in (_schema[1].get("required") or []),
                                **v,
                                **({"type": "file"} if q in _any_file_in_schema else {}),
                                **({"type": ([x for x in v["anyOf"] if x["type"] != "null"] + ["string"])[0]}
                                   if q not in _any_file_in_schema and "anyOf" in v else {})
                            }
                            for q, v in _schema[1]["properties"].items()
                        ]
                    )
                    path_mth["consumes"] = ["multipart/form-data"]
                elif _schema_method == "args":
                    path_mth["parameters"].extend(
                        [
                            {
                                'name': q,
                                'in': 'query',
                                'required': q in (_schema[1].get("required") or []),
                                'type': v.get("type") or "string"
                            }
                            for q, v in _schema[1]["properties"].items()
                        ]
                    )
                else:

                    if method in ['POST', 'PUT', 'PATCH']:
                        path_mth["parameters"].append(
                            {
                                'name': 'body',
                                'in': 'body',
                                'required': True,
                                "schema": {
                                    "$ref": f"#/definitions/{_schema}"
                                }
                            }
                        )

                    elif method in ['GET', 'DELETE']:
                        pass

                swagger_template["paths"][uri][method.lower()] = path_mth

    return Swagger(app, template=swagger_template, config=swagger_config)

