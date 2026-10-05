"""Connection management: dbt <-> Redis ADBC driver via adbc_driver_manager's DB-API."""

import os
import sys
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Iterable, Optional, Tuple
from urllib.parse import urlsplit, urlunsplit

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

    @classmethod
    def validate(cls, data):
        # dbt validates the profile before __pre_deserialize__ sets the default.
        super().validate({"database": "redis", **data})

    @property
    def type(self) -> str:
        return "redis_adbc"

    @property
    def unique_field(self) -> str:
        # Hashed for dbt's anonymous usage stats: the server, not credentials.
        return _redact_uri(self.uri, keep_user=False)

    def _connection_keys(self) -> Tuple[str, ...]:
        return ("driver", "uri", "database", "schema", "username", "aggregate_pushdown", "rename_rekey")

    def connection_info(self, *, with_aliases: bool = False) -> Iterable[Tuple[str, Any]]:
        # dbt debug prints these and logs them: never the URI's password.
        for key, value in super().connection_info(with_aliases=with_aliases):
            yield key, _redact_uri(value) if key == "uri" and value else value

    def driver_path(self) -> str:
        path = self.driver or os.environ.get("REDIS_ADBC_DRIVER")
        if not path:
            raise DbtRuntimeError(
                "No Redis ADBC driver configured: set `driver` in profiles.yml or $REDIS_ADBC_DRIVER"
            )
        path = os.path.expanduser(path)
        # `driver/libadbc_driver_redis` means the platform's shared library.
        if not os.path.splitext(os.path.basename(path))[1]:
            path += {"darwin": ".dylib", "win32": ".dll"}.get(sys.platform, ".so")
        return path


def _redact_uri(uri: str, keep_user: bool = True) -> str:
    """The URI with its password replaced by ****, or (keep_user=False)
    without any credentials."""
    try:
        parts = urlsplit(uri)
        host = parts.hostname or ""
        if parts.port:
            host = f"{host}:{parts.port}"
    except ValueError:
        return "<unparseable uri>"
    if keep_user and (parts.username or parts.password):
        user = parts.username or ""
        host = f"{user}:****@{host}" if parts.password else f"{user}@{host}"
    return urlunsplit((parts.scheme, host, parts.path, parts.query, parts.fragment))


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

    def cancel(self):
        """Cancel the statement running on this connection (from another thread).

        Idle cursors refuse with INVALID_STATE, and so does a cursor reading
        a streamed result, which the driver can't cancel yet.
        """
        for cur in list(self._cursors):
            if cur._closed:
                continue
            try:
                cur.adbc_cancel()
            except adbc_driver_manager.Error as e:
                logger.debug(f"Redis ADBC cancel: {e}")

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

    def execute(self, sql: str, auto_begin: bool = False, fetch: bool = False, limit: Optional[int] = None):
        # The driver streams a long result (over 65,536 rows), so an error
        # past its first batch comes from fetching the rows, which dbt does
        # outside add_query's exception_handler.
        with self.exception_handler(sql):
            return super().execute(sql, auto_begin=auto_begin, fetch=fetch, limit=limit)

    def cancel(self, connection: Connection):
        # dbt calls this from the main thread on Ctrl-C and --fail-fast.
        connection.handle.cancel()

    @classmethod
    def get_response(cls, cursor: Any) -> AdapterResponse:
        rows = cursor.rowcount if cursor is not None else -1
        return AdapterResponse(_message="OK", rows_affected=rows if rows is not None else -1)

    @classmethod
    def data_type_code_to_name(cls, type_code) -> str:
        from dbt.adapters.redis_adbc.impl import arrow_type_to_sql

        return arrow_type_to_sql(type_code)
