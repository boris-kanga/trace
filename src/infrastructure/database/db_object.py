from typing import Optional
from dataclasses import is_dataclass, asdict
from contextlib import asynccontextmanager
import re

import asyncpg
import sqlparse

from src.core.logger import get_logger

from src.domain.interfaces.db_object_abc import DbObjectABC, AffectedRows, DBError


logger = get_logger(__name__)



class DBObject(DbObjectABC):
    def __init__(self, host, port, user, password, database_name, min_size=2, max_size=10):
        self._host = host
        self._port = port
        self._user = user
        self._password = password
        self._database_name = database_name
        self._min_size = min_size
        self._max_size = max_size

        self._pool: Optional[asyncpg.pool.Pool] = None

    @classmethod
    def get_root_db_exception(cls):
        return asyncpg.exceptions.PostgresError

    @classmethod
    def parse_error(cls, error):
        if isinstance(error, asyncpg.exceptions.UniqueViolationError):
            key, value = re.search(
                r"\((\w+)\)=\((\w+)\)", error.detail
            ).groups()
            return DBError(
                "UniqueViolationError",
                (key, value)

            )
        if isinstance(error, asyncpg.exceptions.DataError):
            pass
        return DBError(
            "DBError"
        )

    @staticmethod
    def _get_sql_type(sql):
        if not sql or not sql.strip():
            return "EMPTY"
        sql = sqlparse.parse(sql)
        if sql:
            sql = sql[0]
            return sql.get_type()
        return "SELECT"

    async def connect(self):
        self._pool = await asyncpg.create_pool(
            dsn=f"postgresql://{self._user}:{self._password}@{self._host}:{self._port}/{self._database_name}",
            min_size=self._min_size,
            max_size=self._max_size
        )

    async def __aenter__(self):
        if not self._pool:
            await self.connect()
        return await self._pool.acquire()

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

    @asynccontextmanager
    async def get_conn(self):
        async with self as conn:
            try:
                yield conn
            finally:
                if self._pool is not None:
                    await self._pool.release(conn)

    async def insert_records(self, table_name, records:list[list]|list[dict], columns=None, conn=None, on_conflict=None):
        if not records:
            return []
        first_row = records[0]
        data_columns = columns
        if is_dataclass(first_row):
            if hasattr(first_row, "to_dict"):
                first_row = first_row.to_dict()
            else:
                first_row = asdict(first_row)
        if isinstance(first_row, dict):
            data_columns = list(first_row.keys())

        if not columns:
            columns = data_columns
        if not columns:
            raise TypeError("Required columns")


        if isinstance(first_row, dict):
            _tmp = []
            for r in records:
                row = []
                if hasattr(r, "to_dict"):
                    r = r.to_dict()
                for c in data_columns:
                    row.append(
                        getattr(r, c, None)
                        if is_dataclass(r) else r.get(c, None)
                    )
                _tmp.append(tuple(row))
            records = _tmp

        if not self._pool:
            await self.connect()

        if not on_conflict:
            async def _run(active_conn):
                return await active_conn.copy_records_to_table(
                    table_name,
                    records=records,
                    columns=columns
                )
        else:
            async def _run(active_conn):
                return await active_conn.executemany(
                    f"INSERT INTO {table_name} ({','.join(columns)}) VALUES "
                    f"({','.join('$'+str(i+1) for i in range(len(columns)))}) "
                    f"ON CONFLICT {on_conflict}", records
                )

        if conn is not None:
            return await _run(conn)

        async with self._pool.acquire() as dynamic_conn:
            return await _run(dynamic_conn)

    async def execute(self, query, params=None, conn=None):
        if not self._pool:
            await self.connect()

        _type = self._get_sql_type(query).upper()
        if _type == "EMPTY":
            return []

        query = query.strip()

        async def _parse_result(active_conn):
            _is_returning = re.search(r"RETURNING\s+\w+\s*;?$", query, re.I) is not None
            logger.info(f"{query}--> {(params or ())}")
            if _type == "SELECT" or _is_returning:
                rows = [dict(x) for x in await active_conn.fetch(query, *(params or ()))]
                if _is_returning and rows:
                    if len(rows[0]) == 1:
                        return list(rows[0].values())[0]
                    return rows[0]
                return rows
            else:
                res = None
                if conn is not None:
                    res = await active_conn.execute(query, *(params or ()))
                else:
                    async with active_conn.transaction():
                        res = await active_conn.execute(query, *(params or ()))

                if _type == "INSERT":
                    return AffectedRows(int(res.split()[2]))
                if _type in ("UPDATE", "DELETE"):
                    return AffectedRows(int(res.split()[1]))
                return res

        if conn is not None:
            return await _parse_result(conn)

        async with self._pool.acquire() as dynamic_conn:
            return await _parse_result(dynamic_conn)

    async def close(self):
        if self._pool:
            await self._pool.close()
            self._pool = None
