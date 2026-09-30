from abc import ABC, abstractmethod

from dataclasses import dataclass
from typing import Literal, Any

from contextlib import asynccontextmanager


@dataclass(frozen=True)
class AffectedRows:
    size: int


@dataclass(frozen=True)
class DBError:
    type: Literal["DBError", "UniqueViolationError"]
    args: Any = None

    def __str__(self):
        if self.type == "UniqueViolationError":
            return f"Champ {self.args[0]} dupliqué pour la valeur {self.args[1]}"
        if self.type == "DBError":
            return "Une erreur s'est produite"
        return self.type

    def to_dict(self):
        return str(self)


class DbObjectABC(ABC):
    @classmethod
    @abstractmethod
    def get_root_db_exception(cls):
        pass

    @staticmethod
    def sql_file_j2(j2_file, **kwargs):
        from jinja2 import Template
        from src.core.config import WORK_DIR
        base = WORK_DIR + "sql"

        if (base + j2_file).exists():
            j2_file = base + j2_file
        else:
            m, file = j2_file.split(".", 1)
            if (base + m + file).exists():
                j2_file = base + m + file
            else:
                j2_file = (base + m) + (file + ".j2.sql")
        with open(j2_file) as f:
            template = Template(f.read())
            return template.render(**kwargs)

    @classmethod
    @abstractmethod
    def parse_error(cls, error):
        pass

    @abstractmethod
    async def connect(self):
        pass

    @abstractmethod
    async def __aenter__(self):
        pass

    @abstractmethod
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

    @abstractmethod
    async def insert_records(self, table_name, records:list[list]|list[dict], columns=None, conn=None, on_conflict=None):
        pass

    @abstractmethod
    async def execute(self, query, params=None, conn=None):
        pass

    @abstractmethod
    async def close(self):
        pass

    @abstractmethod
    @asynccontextmanager
    async def get_conn(self):
        pass
