from dbt.adapters.base import AdapterPlugin

from dbt.adapters.redis_adbc.connections import RedisAdbcConnectionManager, RedisAdbcCredentials
from dbt.adapters.redis_adbc.impl import RedisAdbcAdapter
from dbt.include import redis_adbc

Plugin = AdapterPlugin(
    adapter=RedisAdbcAdapter,
    credentials=RedisAdbcCredentials,
    include_path=redis_adbc.PACKAGE_PATH,
)

__all__ = ["Plugin", "RedisAdbcAdapter", "RedisAdbcConnectionManager", "RedisAdbcCredentials"]
