"""Connection management: dbt <-> Redis ADBC driver via adbc_driver_manager's DB-API."""

import os
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Optional, Tuple

import adbc_driver_manager
import adbc_driver_manager.dbapi as dbapi
from dbt_common.exceptions import DbtDatabaseError, DbtRuntimeError

from dbt.adapters.contracts.connection import AdapterResponse, Connection, ConnectionState, Credentials
from dbt.adapters.events.logging import AdapterLogger
from dbt.adapters.sql import SQLConnectionManager

logger = AdapterLogger("RedisAdbc")


@dataclass
class RedisAdbcCredentials(Credentials):
    # Path to libadbc_driver_redis.{so,dylib,dll}; falls back to $REDIS_ADBC_DRIVER.
    driver: Optional[str] = None
    uri: str = "redis://localhost:6379/0"
    username: Optional[str] = None
    password: Optional[str] = None
    # exact | all | none (see the driver README).
    aggregate_pushdown: Optional[str] = None
    # Move a renamed table's rows to its new name's keys (driver option
    # adbc.redis.rename_rekey). dbt renames every table it builds, so this
    # copies every row once more per build, in exchange for key names that
    # match the table's.
    rename_rekey: Optional[bool] = None

    @classmethod
    def __pre_deserialize__(cls, data):
        data = super().__pre_deserialize__(data)
        # The driver exposes a single catalog named "redis".
        data.setdefault("database", "redis")
        return data

    @property
    def type(self) -> str:
        return "redis_adbc"

    @property
    def unique_field(self) -> str:
        return self.uri

    def _connection_keys(self) -> Tuple[str, ...]:
        return ("driver", "uri", "database", "schema", "username", "aggregate_pushdown", "rename_rekey")

    def driver_path(self) -> str:
        path = self.driver or os.environ.get("REDIS_ADBC_DRIVER")
        if not path:
            raise DbtRuntimeError(
                "No Redis ADBC driver configured: set `driver` in profiles.yml or $REDIS_ADBC_DRIVER"
            )
        return os.path.expanduser(path)


class RedisAdbcHandle:
    """Wraps an ADBC DB-API connection so cursors dbt never closes get closed.

    ADBC refuses to close a connection while it still has open statements.
    """

    def __init__(self, conn: dbapi.Connection):
        self.conn = conn
        self._cursors: list = []

    def cursor(self):
        # Close finished cursors eagerly so statements don't pile up.
        self._cursors = [c for c in self._cursors if not c._closed]
        cur = self.conn.cursor()
        self._cursors.append(cur)
        return cur

    def commit(self):
        pass  # autocommit only

    def rollback(self):
        pass  # no transactions

    def close(self):
        for cur in self._cursors:
            try:
                cur.close()
            except Exception:
                pass
        self._cursors = []
        self.conn.close()


class RedisAdbcConnectionManager(SQLConnectionManager):
    TYPE = "redis_adbc"

    @classmethod
    def open(cls, connection: Connection) -> Connection:
        if connection.state == ConnectionState.OPEN:
            return connection
        creds: RedisAdbcCredentials = connection.credentials
        db_kwargs = {"uri": creds.uri, "adbc.redis.default_schema": creds.schema}
        if creds.username:
            db_kwargs["username"] = creds.username
        if creds.password:
            db_kwargs["password"] = creds.password
        if creds.aggregate_pushdown:
            db_kwargs["adbc.redis.aggregate_pushdown"] = creds.aggregate_pushdown
        if creds.rename_rekey is not None:
            db_kwargs["adbc.redis.rename_rekey"] = "true" if creds.rename_rekey else "false"

        def connect():
            conn = dbapi.connect(driver=creds.driver_path(), db_kwargs=db_kwargs, autocommit=True)
            return RedisAdbcHandle(conn)

        return cls.retry_connection(
            connection,
            connect=connect,
            logger=logger,
            retryable_exceptions=[adbc_driver_manager.OperationalError],
        )

    @contextmanager
    def exception_handler(self, sql: str):
        try:
            yield
        except adbc_driver_manager.Error as e:
            logger.debug(f"Redis ADBC error: {e}")
            raise DbtDatabaseError(str(e).strip()) from e
        except Exception as e:
            if isinstance(e, (DbtRuntimeError, DbtDatabaseError)):
                raise
            raise DbtRuntimeError(str(e)) from e

    def cancel(self, connection: Connection):
        pass  # the driver doesn't support cancellation

    @classmethod
    def get_response(cls, cursor: Any) -> AdapterResponse:
        rows = cursor.rowcount if cursor is not None else -1
        return AdapterResponse(_message="OK", rows_affected=rows if rows is not None else -1)

    # The driver is autocommit-only: dbt's BEGIN/COMMIT become no-ops.
    def add_begin_query(self):
        pass

    def add_commit_query(self):
        pass

    @classmethod
    def data_type_code_to_name(cls, type_code) -> str:
        from dbt.adapters.redis_adbc.impl import arrow_type_to_sql

        return arrow_type_to_sql(type_code)
